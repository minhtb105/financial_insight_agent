import logging
import os
import time
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel

from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var
from infrastructure.resilience.circuit_breaker import LLMUnavailableError, CircuitBreaker

logger = get_logger("llm_provider")


class MultiQuery(BaseModel):
    queries: List[str]


class LLMProvider:
    def __init__(self):
        load_dotenv()

        openai_api_key = os.getenv("OPENAI_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")

        if openai_api_key:
            self._primary = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=openai_api_key,
                max_retries=3,
            )
        else:
            logger.warning("OPENAI_API_KEY not set — skipping primary LLM")
            self._primary = None

        if groq_api_key:
            self._fallback = ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=0,
                api_key=groq_api_key,
                max_retries=3,
            )
        else:
            logger.warning("GROQ_API_KEY not set — fallback LLM (Groq) disabled")
            self._fallback = None

        self._circuit_breaker = CircuitBreaker(
            name="llm_provider",
            failure_threshold=3,
            recovery_timeout=60,
            half_open_max_requests=1,
        )

    def invoke_with_fallback(self, messages, model_kwargs: Optional[dict] = None):
        model_kwargs = model_kwargs or {}
        rid = request_id_var.get() or "unknown"

        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: both OPENAI_API_KEY and GROQ_API_KEY are missing"
            )

        if not self._circuit_breaker.can_execute():
            provider_status = {"circuit_breaker": "open", "state": self._circuit_breaker.state.value}
            raise LLMUnavailableError(
                "Circuit breaker is open — LLM calls temporarily suspended",
                provider_status=provider_status,
            )

        last_error = None

        if self._primary:
            try:
                start = time.time()
                result = self._primary.invoke(messages, **model_kwargs)
                self._circuit_breaker.record_success()
                logger.info("Primary LLM call succeeded", extra={
                    "request_id": rid,
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "duration_ms": round((time.time() - start) * 1000, 2),
                })
                return result
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()
                logger.warning("Primary LLM failed, falling back to Groq", extra={
                    "request_id": rid,
                    "provider": "openai",
                    "error_type": type(e).__name__,
                    "error": str(e),
                })

        if self._fallback and self._circuit_breaker.can_execute():
            try:
                start = time.time()
                result = self._fallback.invoke(messages, **model_kwargs)
                self._circuit_breaker.record_success()
                logger.info("Fallback LLM call completed", extra={
                    "request_id": rid,
                    "provider": "groq",
                    "model": "llama-3.1-8b-instant",
                    "duration_ms": round((time.time() - start) * 1000, 2),
                })
                return result
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()
                logger.error("Fallback LLM also failed", extra={
                    "request_id": rid,
                    "provider": "groq",
                    "error_type": type(e).__name__,
                    "error": str(e),
                })

        if last_error:
            raise last_error

        raise LLMUnavailableError(
            "No LLM providers available: both OpenAI and Groq are unreachable"
        )

    def with_structured_output(
        self,
        pydantic_object,
        method: str = "json_mode",
        fallback: bool = False,
    ):
        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: both OPENAI_API_KEY and GROQ_API_KEY are missing"
            )

        primary = None
        if self._primary:
            primary = self._primary.with_structured_output(pydantic_object, method=method)

        fallback_llm = None
        if self._fallback:
            fallback_llm = self._fallback.with_structured_output(pydantic_object, method=method)

        if not fallback or primary is None:
            if fallback_llm:
                return fallback_llm
            if primary:
                return primary
            raise LLMUnavailableError(
                "No LLM providers available: both OPENAI_API_KEY and GROQ_API_KEY are missing"
            )

        circuit_breaker = self._circuit_breaker

        class FallbackChain:
            def __init__(self, primary, fallback, rid: str, cb):
                self._primary = primary
                self._fallback = fallback
                self._rid = rid
                self._cb = cb

            def invoke(self, messages, **kwargs):
                rid = self._rid or request_id_var.get() or "unknown"
                last_error = None

                if not self._cb.can_execute():
                    raise LLMUnavailableError(
                        "Circuit breaker is open — structured LLM calls temporarily suspended",
                    )

                if self._primary:
                    try:
                        start = time.time()
                        result = self._primary.invoke(messages, **kwargs)
                        self._cb.record_success()
                        logger.info("Primary structured LLM call succeeded", extra={
                            "request_id": rid,
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "duration_ms": round((time.time() - start) * 1000, 2),
                        })
                        return result
                    except Exception as e:
                        last_error = e
                        self._cb.record_failure()
                        logger.warning("Primary structured LLM failed, falling back to Groq", extra={
                            "request_id": rid,
                            "provider": "openai",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        })

                if self._fallback and self._cb.can_execute():
                    try:
                        start = time.time()
                        result = self._fallback.invoke(messages, **kwargs)
                        self._cb.record_success()
                        logger.info("Fallback structured LLM call completed", extra={
                            "request_id": rid,
                            "provider": "groq",
                            "model": "llama-3.1-8b-instant",
                            "duration_ms": round((time.time() - start) * 1000, 2),
                        })
                        return result
                    except Exception as e:
                        last_error = e
                        self._cb.record_failure()
                        logger.error("Fallback structured LLM also failed", extra={
                            "request_id": rid,
                            "provider": "groq",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        })

                if last_error:
                    raise last_error
                raise LLMUnavailableError(
                    "No LLM providers available: both OpenAI and Groq are unreachable"
                )

        return FallbackChain(primary, fallback_llm, rid=request_id_var.get() or "unknown", cb=circuit_breaker)

    def get_tool_calling_llm(self, tools):
        """
        Return an LLM-like callable with tools bound for tool-calling.

        Tries primary (OpenAI) first with fallback to Groq.
        Handles circuit breaker and error logging.
        """
        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: both OPENAI_API_KEY and GROQ_API_KEY are missing"
            )

        primary = self._primary.bind_tools(tools) if self._primary else None
        fallback_llm = self._fallback.bind_tools(tools) if self._fallback else None

        if not fallback_llm and primary is None:
            raise LLMUnavailableError(
                "No LLM providers available: both OpenAI and Groq are unreachable"
            )

        circuit_breaker = self._circuit_breaker
        rid = request_id_var.get() or "unknown"

        class ToolCallingChain:
            def __init__(self, primary, fallback, cb, rid):
                self._primary = primary
                self._fallback = fallback
                self._cb = cb
                self._rid = rid

            def invoke(self, messages, **kwargs):
                rid = self._rid or request_id_var.get() or "unknown"
                last_error = None

                if not self._cb.can_execute():
                    raise LLMUnavailableError(
                        "Circuit breaker is open — tool-calling LLM calls temporarily suspended",
                    )

                if self._primary:
                    try:
                        start = time.time()
                        result = self._primary.invoke(messages, **kwargs)
                        self._cb.record_success()
                        logger.info("Primary tool-calling LLM call succeeded", extra={
                            "request_id": rid,
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "duration_ms": round((time.time() - start) * 1000, 2),
                        })
                        return result
                    except Exception as e:
                        last_error = e
                        self._cb.record_failure()
                        logger.warning("Primary tool-calling LLM failed, falling back to Groq", extra={
                            "request_id": rid,
                            "provider": "openai",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        })

                if self._fallback and self._cb.can_execute():
                    try:
                        start = time.time()
                        result = self._fallback.invoke(messages, **kwargs)
                        self._cb.record_success()
                        logger.info("Fallback tool-calling LLM call completed", extra={
                            "request_id": rid,
                            "provider": "groq",
                            "model": "llama-3.1-8b-instant",
                            "duration_ms": round((time.time() - start) * 1000, 2),
                        })
                        return result
                    except Exception as e:
                        last_error = e
                        self._cb.record_failure()
                        logger.error("Fallback tool-calling LLM also failed", extra={
                            "request_id": rid,
                            "provider": "groq",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        })

                if last_error:
                    raise last_error
                raise LLMUnavailableError(
                    "No LLM providers available: both OpenAI and Groq are unreachable"
                )

        return ToolCallingChain(primary, fallback_llm, rid=rid, cb=circuit_breaker)
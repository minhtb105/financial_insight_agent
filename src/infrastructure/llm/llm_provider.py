import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var
from infrastructure.observability.tracing import SpanKind, get_tracer
from infrastructure.resilience.circuit_breaker import LLMUnavailableError, create_circuit_breaker

_RETRYABLE_ERRORS = frozenset({
    "RateLimitError",
    "InternalServerError",
    "ServiceUnavailableError",
    "APITimeoutError",
    "APIConnectionError",
})

_AUTH_ERRORS = frozenset({
    "AuthenticationError",
    "PermissionDeniedError",
    "ForbiddenError",
})

logger = get_logger("llm_provider")

_OPENAI_KNOWN_KWARGS = {
    "temperature",
    "max_tokens",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "stop",
    "n",
    "stream",
    "model",
    "response_format",
    "seed",
    "tools",
    "tool_choice",
}

_GROQ_KNOWN_KWARGS = {
    "temperature",
    "max_tokens",
    "top_p",
    "stop",
    "stream",
    "model",
}


class MultiQuery(BaseModel):
    queries: list[str]


class ReformulatedQuery(BaseModel):
    """Self-contained rewrite of a context-dependent follow-up question."""

    rewritten: str
    entities: list[str] = []
    topics: list[str] = []


class LLMChain:
    def __init__(self, primary, fallback, openai_cb, groq_cb, label: str):
        self._primary = primary
        self._fallback = fallback
        self._openai_cb = openai_cb
        self._groq_cb = groq_cb
        self._label = label
        self._openai_kwarg_keys = _OPENAI_KNOWN_KWARGS
        self._groq_kwarg_keys = _GROQ_KNOWN_KWARGS

    @staticmethod
    def _filter_kwargs(kwargs, allowed_keys):
        return {k: v for k, v in kwargs.items() if k in allowed_keys}

    @staticmethod
    def _classify_error(error: Exception) -> str:
        error_type = type(error).__name__
        if error_type in _RETRYABLE_ERRORS:
            return "retryable"
        if error_type in _AUTH_ERRORS:
            return "auth"
        return "unknown"

    def _try_provider(self, provider_name: str, llm, cb, messages, kwargs, rid: str):  # noqa: PLR0917
        """Try a single provider. Returns (result, error) tuple."""
        try:
            start = time.time()
            result = llm.invoke(messages, **kwargs)
            cb.record_success()
            logger.info(
                "%s %s LLM call succeeded", provider_name.title(), self._label,
                extra={
                    "request_id": rid,
                    "provider": provider_name,
                    "duration_ms": round((time.time() - start) * 1000, 2),
                },
            )
            return result, None
        except Exception as e:
            error_type = type(e).__name__
            category = self._classify_error(e)

            log_extra = {
                "request_id": rid,
                "provider": provider_name,
                "error_type": error_type,
                "error_category": category,
                "error": str(e),
            }

            if category == "retryable":
                logger.warning("%s retryable error", provider_name.title(), extra=log_extra)
            elif category == "auth":
                logger.error("%s auth error", provider_name.title(), extra=log_extra)
                cb.record_failure()
            else:
                logger.warning("%s LLM failed", provider_name.title(), extra=log_extra)
                cb.record_failure()

            return None, e

    def invoke(self, messages, **kwargs):
        rid = request_id_var.get() or "unknown"
        last_error = None

        tracer = get_tracer()
        with tracer.start_span(
            "llm_provider.chain", SpanKind.LLM,
            attributes={"request_id": rid, "label": self._label},
            inputs={"message_count": len(messages)},
        ) as span:
            openai_kwargs = self._filter_kwargs(kwargs, self._openai_kwarg_keys)
            groq_kwargs = self._filter_kwargs(kwargs, self._groq_kwarg_keys)

            if self._primary and self._openai_cb.acquire_permit():
                result, err = self._try_provider("openai", self._primary, self._openai_cb, messages, openai_kwargs, rid)
                if err is None:
                    if span is not None:
                        span.provider = "openai"
                        span.model = getattr(self._primary, "model_name", None) or getattr(self._primary, "model", None)
                        span.attributes["fallback_used"] = False
                    return result
                last_error = err
                if span is not None:
                    span.attributes["openai_error"] = f"{type(err).__name__}: {err}"

            if self._fallback and self._groq_cb.acquire_permit():
                result, err = self._try_provider("groq", self._fallback, self._groq_cb, messages, groq_kwargs, rid)
                if err is None:
                    if span is not None:
                        span.provider = "groq"
                        span.model = getattr(self._fallback, "model_name", None)
                        span.attributes["fallback_used"] = True
                    return result
                last_error = err

            if span is not None and last_error is not None:
                span.attributes["all_providers_failed"] = True

        if last_error:
            raise last_error
        raise LLMUnavailableError(
            "No LLM providers available: both OpenAI and Groq are unreachable"
        )


class LLMProvider:
    def __init__(self):
        load_dotenv()
        self._chain_cache: dict[str, LLMChain] = {}

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

        self._openai_cb = create_circuit_breaker(name="llm_openai")
        self._groq_cb = create_circuit_breaker(name="llm_groq")

    def invoke_with_fallback(self, messages, model_kwargs: dict | None = None):
        """Invoke LLM with automatic primary → fallback chain.

        Delegates to LLMChain to avoid duplicating the retry logic.
        """
        model_kwargs = model_kwargs or {}

        if self._primary is None and self._fallback is None:
            raise LLMUnavailableError(
                "No LLM providers available: both OPENAI_API_KEY and GROQ_API_KEY are missing"
            )

        chain = self._make_chain(self._primary, self._fallback, "invoke")
        return chain.invoke(messages, **model_kwargs)

    def _make_chain(self, primary, fallback, label) -> "LLMChain":
        cache_key = f"{label}:{id(primary)}:{id(fallback)}"
        cached = self._chain_cache.get(cache_key)
        if cached:
            return cached
        chain = LLMChain(
            primary=primary,
            fallback=fallback,
            openai_cb=self._openai_cb,
            groq_cb=self._groq_cb,
            label=label,
        )
        self._chain_cache[cache_key] = chain
        return chain

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

        primary = (
            self._primary.with_structured_output(pydantic_object, method=method)
            if self._primary
            else None
        )
        fallback_llm = (
            self._fallback.with_structured_output(pydantic_object, method=method)
            if self._fallback
            else None
        )

        if not fallback or primary is None:
            if fallback_llm:
                return fallback_llm
            if primary:
                return primary
            raise LLMUnavailableError(
                "No LLM providers available: both OPENAI_API_KEY and GROQ_API_KEY are missing"
            )

        return self._make_chain(primary, fallback_llm, "structured")

    def get_tool_calling_llm(self, tools, **kwargs):  # noqa: ARG002 — API-compat passthrough
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

        return self._make_chain(primary, fallback_llm, "tool-calling")

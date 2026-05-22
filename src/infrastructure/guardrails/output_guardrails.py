"""
Output guardrails for the financial insight agent.

Validates and sanitizes LLM responses before returning to the user.
Runs AFTER the agent's ReAct loop — protects against PII leaks,
API key exposure, anomalous responses, and all-tool-failure scenarios.

This is the OUTPUT side of the guardrail system. The INPUT side
lives in pipeline.py and its companion guardrail modules.
"""

import re
import logging
from typing import Any
from collections.abc import Sequence
from langchain_core.messages import ToolMessage, BaseMessage
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GuardrailLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    level: GuardrailLevel
    code: str
    message: str
    field: str | None = None
    value: Any | None = None


@dataclass
class ValidationResultData:
    status: ValidationResult
    issues: list[ValidationIssue]
    confidence: float | None = None
    processed_query: dict[str, Any] | None = None


class OutputGuardrails:
    """Output validation and sanitization guardrails."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        return {
            "financial_bounds": {
                "pe_ratio": {"min": 0, "max": 1000},
                "price": {"min": 0, "max": 1000000},
                "volume": {"min": 0, "max": 1000000000},
            },
            "response_length": {"max": 2000},
            "pii_detection": True,
            "api_key_detection": True,
            "anomaly_detection": True,
        }

    def validate_tool_results(self, messages: Sequence[BaseMessage]) -> str | None:
        """Check that at least one tool returned useful data.

        Returns an error message string if all tools failed, or None when OK.
        """
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        if not tool_msgs:
            return None

        all_errors = all("TOOL_ERR#" in str(m.content) for m in tool_msgs)
        if all_errors:
            return (
                "Không thể lấy dữ liệu cho yêu cầu này. "
                "Vui lòng kiểm tra lại mã cổ phiếu hoặc thử lại sau."
            )
        return None

    def validate_response(self, response: str, original_query: str) -> ValidationResultData:
        issues = []
        sanitized_response = response

        if response is None:
            return ValidationResultData(
                status=ValidationResult.PASS,
                issues=[],
                processed_query={"original_response": None, "sanitized_response": ""},
            )

        length_result = self._validate_response_length(sanitized_response)
        if length_result.status == ValidationResult.FAIL:
            issues.extend(length_result.issues)
            sanitized_response = sanitized_response[: self.config["response_length"]["max"]]

        pii_result = self._detect_pii(sanitized_response)
        if pii_result.status == ValidationResult.FAIL:
            issues.extend(pii_result.issues)
            sanitized_response = self._redact_pii(sanitized_response)

        api_result = self._detect_api_keys(sanitized_response)
        if api_result.status == ValidationResult.FAIL:
            issues.extend(api_result.issues)
            sanitized_response = self._redact_api_keys(sanitized_response)

        anomaly_result = self._detect_anomalies(sanitized_response, original_query)
        if anomaly_result.status == ValidationResult.WARNING:
            issues.extend(anomaly_result.issues)

        has_fail = any(i.level in (GuardrailLevel.CRITICAL, GuardrailLevel.HIGH) for i in issues)
        has_warning = any(i.level == GuardrailLevel.MEDIUM for i in issues)
        if has_fail:
            status = ValidationResult.FAIL
        elif has_warning:
            status = ValidationResult.WARNING
        else:
            status = ValidationResult.PASS
        return ValidationResultData(
            status=status,
            issues=issues,
            processed_query={
                "original_response": response,
                "sanitized_response": sanitized_response,
            },
        )

    def _validate_response_length(self, response: str) -> ValidationResultData:
        max_length = self.config["response_length"]["max"]
        issues = []

        if len(response) > max_length:
            issues.append(
                ValidationIssue(
                    level=GuardrailLevel.MEDIUM,
                    code="RESPONSE_TOO_LONG",
                    message=f"Response too long: {len(response)} characters (max: {max_length})",
                )
            )

        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS, issues=issues
        )

    def _detect_pii(self, text: str) -> ValidationResultData:
        issues = []

        # Email detection with TLD validation (skip numeric-only TLDs)
        email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.([a-zA-Z]{2,})"
        )
        for match in email_pattern.finditer(text):
            tld = match.group(1)
            if tld.isalpha() and len(tld) >= 2:
                issues.append(
                    ValidationIssue(
                        level=GuardrailLevel.HIGH,
                        code="PII_EMAIL_DETECTED",
                        message="Email address detected in response",
                    )
                )
                break

        # Phone numbers: Vietnamese (+84 / 0)
        phone_pattern = re.compile(r"(\+84|0)([0-9]{9,10})")
        if phone_pattern.search(text):
            issues.append(
                ValidationIssue(
                    level=GuardrailLevel.HIGH,
                    code="PII_PHONE_DETECTED",
                    message="Phone number detected in response",
                )
            )

        # Vietnamese ID: CCCD (12 digits), CMND (9 digits)
        id_pattern = re.compile(r"\b\d{12}\b|\b\d{9}\b")
        if id_pattern.search(text):
            issues.append(
                ValidationIssue(
                    level=GuardrailLevel.HIGH,
                    code="PII_VIETNAM_ID_DETECTED",
                    message="Vietnamese ID number detected in response",
                )
            )

        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS, issues=issues
        )

    def _detect_api_keys(self, text: str) -> ValidationResultData:
        issues = []

        api_patterns = [
            r"(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*[a-zA-Z0-9]{10,}",
            r"sk-[a-zA-Z0-9]{20,}",
            r"pk_[a-zA-Z0-9]{20,}",
        ]

        for pattern in api_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        level=GuardrailLevel.CRITICAL,
                        code="API_KEY_DETECTED",
                        message="API key detected in response",
                    )
                )
                break

        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS, issues=issues
        )

    def _detect_anomalies(self, response: str, _original_query: str) -> ValidationResultData:
        issues = []

        suspicious_patterns = [
            r"\b(?:traceback|debug)\b",
            r"\b(?:password|credential)\b",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        level=GuardrailLevel.MEDIUM,
                        code="ANOMALY_DETECTED",
                        message="Potential anomaly detected in response",
                    )
                )
                break

        return ValidationResultData(
            status=ValidationResult.WARNING if issues else ValidationResult.PASS, issues=issues
        )

    def _redact_pii(self, text: str) -> str:
        text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", text)
        text = re.sub(r"(\+84|0)([0-9]{9,10})", "[REDACTED_PHONE]", text)
        text = re.sub(r"\b\d{12}\b", "[REDACTED_ID]", text)
        text = re.sub(r"\b\d{9}\b", "[REDACTED_ID]", text)
        return text

    def _redact_api_keys(self, text: str) -> str:
        api_patterns = [
            r"(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*[a-zA-Z0-9]{10,}",
            r"sk-[a-zA-Z0-9]{20,}",
            r"pk_[a-zA-Z0-9]{20,}",
        ]

        for pattern in api_patterns:
            text = re.sub(pattern, "[REDACTED_API_KEY]", text, flags=re.IGNORECASE)

        return text


def get_output_guardrails() -> OutputGuardrails | None:
    """Get output guardrails instance from Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    return deps.output_guardrails if deps is not None else None

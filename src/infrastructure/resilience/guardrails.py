"""
Guardrails system for the financial insight agent.

Provides comprehensive input validation, step-wise validation, and output protection.
Ensures system security, reliability, and financial domain safety.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from infrastructure.guardrails.type_validators import validate_parsed_query
from infrastructure.guardrails.tickers import VIETNAMESE_TICKERS

logger = logging.getLogger(__name__)


class GuardrailLevel(Enum):
    """Guardrail severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationResult(Enum):
    """Validation result status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    level: GuardrailLevel
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None


@dataclass
class ValidationResultData:
    """Result of validation process."""
    status: ValidationResult
    issues: List[ValidationIssue]
    confidence: Optional[float] = None
    processed_query: Optional[Dict[str, Any]] = None


class StepWiseGuardrails:
    """Step-wise validation guardrails for LangGraph pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize step-wise guardrails.
        
        Args:
            config: Configuration for guardrails
        """
        self.config = config or self._get_default_config()
        self._ticker_whitelist = self._load_ticker_whitelist()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default step-wise guardrails configuration."""
        return {
            "confidence_threshold": 0.5,
            "date_validation": {
                "max_years_back": 5,
                "max_years_forward": 1
            },
            "ticker_validation": {
                "whitelist_enabled": True,
                "max_tickers": 10
            },
            "financial_bounds": {
                "pe_ratio": {"min": 0, "max": 1000},
                "price": {"min": 0, "max": 1000000},
                "volume": {"min": 0, "max": 1000000000}
            }
        }
    
    def _load_ticker_whitelist(self) -> set:
        """Load ticker whitelist from canonical source."""
        return set(VIETNAMESE_TICKERS)
    
    def validate_parser_output(self, parsed_query: Dict[str, Any]) -> ValidationResultData:
        issues = []
        confidence = parsed_query.get("confidence", 0.0)
        
        threshold = self.config["confidence_threshold"]
        if confidence < threshold:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="LOW_CONFIDENCE",
                message=f"Parser confidence too low: {confidence:.2f} (threshold: {threshold})",
                value=confidence
            ))
        
        type_error = validate_parsed_query(parsed_query)
        if type_error:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="SCHEMA_VALIDATION_FAILED",
                message=f"Type schema validation failed: {type_error}",
            ))
        
        status = ValidationResult.FAIL if issues else ValidationResult.PASS
        return ValidationResultData(
            status=status,
            issues=issues,
            confidence=confidence
        )
    
    def validate_tool_input(self, tool_params: Dict[str, Any]) -> ValidationResultData:
        """Validate tool input parameters."""
        issues = []
        query = tool_params.get("query", {})
        
        # Validate tickers
        tickers = query.get("tickers", [])
        ticker_result = self._validate_tickers(tickers)
        if ticker_result.status == ValidationResult.FAIL:
            issues.extend(ticker_result.issues)
        
        # Validate dates
        start_date = query.get("start")
        end_date = query.get("end")
        date_result = self._validate_dates(start_date, end_date)
        if date_result.status == ValidationResult.FAIL:
            issues.extend(date_result.issues)
        
        # Validate interval
        interval = query.get("interval", "1d")
        if interval not in ["1d", "1w", "1m", "1y"]:
            issues.append(ValidationIssue(
                level=GuardrailLevel.MEDIUM,
                code="INVALID_INTERVAL",
                message=f"Invalid interval: {interval}",
                value=interval
            ))
        
        status = ValidationResult.FAIL if issues else ValidationResult.PASS
        return ValidationResultData(status=status, issues=issues)
    
    def validate_tool_output(self, tool_output: Dict[str, Any]) -> ValidationResultData:
        """Validate tool output data."""
        issues = []
        data = tool_output.get("data", [])
        
        # Validate financial bounds
        for record in data:
            # Check P/E ratio bounds
            pe_ratio = record.get("pe_ratio")
            if pe_ratio is not None:
                bounds = self.config["financial_bounds"]["pe_ratio"]
                if not (bounds["min"] <= pe_ratio <= bounds["max"]):
                    issues.append(ValidationIssue(
                        level=GuardrailLevel.HIGH,
                        code="INVALID_PE_RATIO",
                        message=f"P/E ratio out of bounds: {pe_ratio}",
                        value=pe_ratio
                    ))
            
            # Check price bounds
            price = record.get("close") or record.get("price")
            if price is not None:
                bounds = self.config["financial_bounds"]["price"]
                if not (bounds["min"] <= price <= bounds["max"]):
                    issues.append(ValidationIssue(
                        level=GuardrailLevel.HIGH,
                        code="INVALID_PRICE",
                        message=f"Price out of bounds: {price}",
                        value=price
                    ))
        
        status = ValidationResult.FAIL if issues else ValidationResult.PASS
        return ValidationResultData(status=status, issues=issues)
    
    def _validate_tickers(self, tickers: List[str]) -> ValidationResultData:
        """Validate stock tickers."""
        issues = []
        
        if not tickers:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="NO_TICKERS",
                message="No tickers provided"
            ))
            return ValidationResultData(status=ValidationResult.FAIL, issues=issues)
        
        # Check maximum tickers
        max_tickers = self.config["ticker_validation"]["max_tickers"]
        if len(tickers) > max_tickers:
            issues.append(ValidationIssue(
                level=GuardrailLevel.MEDIUM,
                code="TOO_MANY_TICKERS",
                message=f"Too many tickers: {len(tickers)} (max: {max_tickers})",
                value=len(tickers)
            ))
        
        # Check whitelist if enabled
        if self.config["ticker_validation"]["whitelist_enabled"]:
            invalid_tickers = [t for t in tickers if t.upper() not in self._ticker_whitelist]
            if invalid_tickers:
                issues.append(ValidationIssue(
                    level=GuardrailLevel.MEDIUM,
                    code="INVALID_TICKERS",
                    message=f"Invalid tickers: {', '.join(invalid_tickers)}",
                    value=invalid_tickers
                ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _validate_dates(self, start_date: Optional[str], end_date: Optional[str]) -> ValidationResultData:
        """Validate date range."""
        issues = []

        if not start_date or not end_date:
            return ValidationResultData(status=ValidationResult.PASS, issues=issues)

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="INVALID_DATE_FORMAT",
                message=f"Invalid date format: {e}"
            ))
            return ValidationResultData(status=ValidationResult.FAIL, issues=issues)
        
        # Check date range bounds
        now = datetime.now()
        max_back = self.config["date_validation"]["max_years_back"]
        max_forward = self.config["date_validation"]["max_years_forward"]
        
        if start < now - timedelta(days=max_back * 365):
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="DATE_TOO_OLD",
                message=f"Start date too old: {start_date}"
            ))
        
        if end > now + timedelta(days=max_forward * 365):
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="DATE_TOO_NEW",
                message=f"End date too new: {end_date}"
            ))
        
        if start > end:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="INVALID_DATE_RANGE",
                message=f"Start date after end date: {start_date} > {end_date}"
            ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )


class OutputGuardrails:
    """Output validation and sanitization guardrails."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize output guardrails.
        
        Args:
            config: Configuration for guardrails
        """
        self.config = config or self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default output guardrails configuration."""
        return {
            "financial_bounds": {
                "pe_ratio": {"min": 0, "max": 1000},
                "price": {"min": 0, "max": 1000000},
                "volume": {"min": 0, "max": 1000000000}
            },
            "response_length": {"max": 2000},
            "pii_detection": True,
            "api_key_detection": True,
            "anomaly_detection": True
        }
    
    def validate_response(self, response: str, original_query: str) -> ValidationResultData:
        """
        Validate and sanitize final response.
        
        Args:
            response: Agent response
            original_query: Original user query for context
            
        Returns:
            Validation result with sanitized response
        """
        issues = []
        sanitized_response = response
        
        # 1. Response length validation
        length_result = self._validate_response_length(sanitized_response)
        if length_result.status == ValidationResult.FAIL:
            issues.extend(length_result.issues)
            # Truncate response if too long
            sanitized_response = sanitized_response[:self.config["response_length"]["max"]]
        
        # 2. PII detection and redaction
        pii_result = self._detect_pii(sanitized_response)
        if pii_result.status == ValidationResult.FAIL:
            issues.extend(pii_result.issues)
            sanitized_response = self._redact_pii(sanitized_response)
        
        # 3. API key detection
        api_result = self._detect_api_keys(sanitized_response)
        if api_result.status == ValidationResult.FAIL:
            issues.extend(api_result.issues)
            sanitized_response = self._redact_api_keys(sanitized_response)
        
        # 4. Anomaly detection
        anomaly_result = self._detect_anomalies(sanitized_response, original_query)
        if anomaly_result.status == ValidationResult.WARNING:
            issues.extend(anomaly_result.issues)
        
        status = ValidationResult.FAIL if issues else ValidationResult.PASS
        return ValidationResultData(
            status=status,
            issues=issues,
            processed_query={"original_response": response, "sanitized_response": sanitized_response}
        )
    
    def _validate_response_length(self, response: str) -> ValidationResultData:
        """Validate response length."""
        max_length = self.config["response_length"]["max"]
        issues = []
        
        if len(response) > max_length:
            issues.append(ValidationIssue(
                level=GuardrailLevel.MEDIUM,
                code="RESPONSE_TOO_LONG",
                message=f"Response too long: {len(response)} characters (max: {max_length})"
            ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _detect_pii(self, text: str) -> ValidationResultData:
        """Detect PII in text."""
        issues = []
        
        # Email detection
        email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        if email_pattern.search(text):
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="PII_EMAIL_DETECTED",
                message="Email address detected in response"
            ))
        
        # Phone number detection (Vietnamese format)
        phone_pattern = re.compile(r"(\+84|0)([0-9]{9,10})")
        if phone_pattern.search(text):
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="PII_PHONE_DETECTED",
                message="Phone number detected in response"
            ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _detect_api_keys(self, text: str) -> ValidationResultData:
        """Detect API keys in text."""
        issues = []
        
        # Common API key patterns
        api_patterns = [
            r"(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*[a-zA-Z0-9]{10,}",
            r"sk-[a-zA-Z0-9]{20,}",
            r"pk_[a-zA-Z0-9]{20,}"
        ]
        
        for pattern in api_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(ValidationIssue(
                    level=GuardrailLevel.CRITICAL,
                    code="API_KEY_DETECTED",
                    message="API key detected in response"
                ))
                break
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _detect_anomalies(self, response: str, original_query: str) -> ValidationResultData:
        """Detect anomalies in response."""
        issues = []
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"(error|exception|traceback|debug)",
            r"(system|admin|root|sudo)",
            r"(password|credential|login|auth)"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(ValidationIssue(
                    level=GuardrailLevel.MEDIUM,
                    code="ANOMALY_DETECTED",
                    message="Potential anomaly detected in response"
                ))
                break
        
        return ValidationResultData(
            status=ValidationResult.WARNING if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text."""
        # Redact emails
        text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", text)
        
        # Redact phone numbers
        text = re.sub(r"(\+84|0)([0-9]{9,10})", "[REDACTED_PHONE]", text)
        
        return text
    
    def _redact_api_keys(self, text: str) -> str:
        """Redact API keys from text."""
        api_patterns = [
            r"(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*[a-zA-Z0-9]{10,}",
            r"sk-[a-zA-Z0-9]{20,}",
            r"pk_[a-zA-Z0-9]{20,}"
        ]
        
        for pattern in api_patterns:
            text = re.sub(pattern, "[REDACTED_API_KEY]", text, flags=re.IGNORECASE)
        
        return text


# Global guardrails instances
_step_guardrails: Optional[StepWiseGuardrails] = None
_output_guardrails: Optional[OutputGuardrails] = None


def get_step_guardrails() -> StepWiseGuardrails:
    """Get global step-wise guardrails instance."""
    global _step_guardrails
    if _step_guardrails is None:
        _step_guardrails = StepWiseGuardrails()
    return _step_guardrails


def get_output_guardrails() -> OutputGuardrails:
    """Get global output guardrails instance."""
    global _output_guardrails
    if _output_guardrails is None:
        _output_guardrails = OutputGuardrails()
    return _output_guardrails



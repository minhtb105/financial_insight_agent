"""
Guardrails system for the financial insight agent.

Provides comprehensive input validation, step-wise validation, and output protection.
Ensures system security, reliability, and financial domain safety.
"""

import re
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

from infrastructure.guardrails.type_validators import validate_parsed_query

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


class InputGuardrails:
    """Input validation guardrails."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize input guardrails.
        
        Args:
            config: Configuration for guardrails
        """
        self.config = config or self._get_default_config()
        self._rate_limiter = RateLimiter(self.config.get("rate_limit", {}))
        self._ticker_whitelist = self._load_ticker_whitelist()
        self._injection_patterns = self._compile_injection_patterns()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default guardrails configuration."""
        return {
            "query_length": {"min": 5, "max": 500},
            "rate_limit": {"requests_per_hour": 100, "requests_per_minute": 10},
            "injection_detection": {
                "sql_injection": True,
                "xss_injection": True,
                "command_injection": True
            },
            "content_filtering": {
                "toxic_content": True,
                "pii_detection": True,
                "api_keys": True
            },
            "ticker_validation": {
                "whitelist_enabled": True,
                "max_tickers": 10
            }
        }
    
    def _load_ticker_whitelist(self) -> set:
        """Load ticker whitelist for validation."""
        # Common Vietnamese stock tickers
        return {
            "VNM", "VIC", "VCB", "MSN", "FPT", "GAS", "HPG", "PLX", "MWG", "CTG",
            "BID", "ACB", "SHB", "STB", "TPB", "EIB", "HDB", "TCB", "VIB", "LPB",
            "SSB", "BAB", "BCM", "BSR", "CTD", "DIG", "DXG", "GMD", "HSG", "KDH",
            "LCG", "LGC", "LIX", "NVL", "PDR", "REE", "SBT", "SCR", "SHP", "TCH",
            "TDC", "TDG", "TID", "TNA", "TNC", "TPC", "VCG", "VCS", "VHC", "VHM",
            "VIB", "VIC", "VIF", "VNG", "VRC", "VRE", "VSC", "WAC", "WBS", "WEC"
        }
    
    def _compile_injection_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for injection detection."""
        patterns = {}
        
        if self.config["injection_detection"]["sql_injection"]:
            sql_patterns = [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
                r"('.*'|\".*\")",
                r"(--|\/\*|\*\/|;|\||&|\$)",
                r"(OR\s+1\s*=\s*1|AND\s+1\s*=\s*1)"
            ]
            patterns["sql_injection"] = re.compile("|".join(sql_patterns), re.IGNORECASE)
        
        if self.config["injection_detection"]["xss_injection"]:
            xss_patterns = [
                r"(<script[^>]*>.*?</script>)",
                r"(javascript:|data:|vbscript:|onload|onerror|onclick)",
                r"(<iframe[^>]*>.*?</iframe>)",
                r"(<object[^>]*>.*?</object>)"
            ]
            patterns["xss_injection"] = re.compile("|".join(xss_patterns), re.IGNORECASE)
        
        if self.config["injection_detection"]["command_injection"]:
            cmd_patterns = [
                r"(\|\||&&|\||;|\$\(.*?\)|\`.*?\`)",
                r"(rm\s+|del\s+|format\s+|shutdown\s+|reboot\s+)",
                r"(cat\s+|type\s+|ls\s+|dir\s+|find\s+)"
            ]
            patterns["command_injection"] = re.compile("|".join(cmd_patterns), re.IGNORECASE)
        
        return patterns
    
    def validate_query(self, query: str, session_id: Optional[str] = None) -> ValidationResultData:
        """
        Validate input query with comprehensive checks.
        
        Args:
            query: User query string
            session_id: Session identifier for rate limiting
            
        Returns:
            Validation result with issues if any
        """
        issues = []
        processed_query = query.strip()
        
        # 1. Query length validation
        length_result = self._validate_query_length(processed_query)
        if length_result.status == ValidationResult.FAIL:
            issues.extend(length_result.issues)
        
        # 2. Rate limiting
        if session_id:
            rate_result = self._rate_limiter.check_rate_limit(session_id)
            if rate_result.status == ValidationResult.FAIL:
                issues.extend(rate_result.issues)
        
        # 3. Injection detection
        injection_result = self._detect_injection(processed_query)
        if injection_result.status == ValidationResult.FAIL:
            issues.extend(injection_result.issues)
        
        # 4. Content filtering
        content_result = self._filter_content(processed_query)
        if content_result.status == ValidationResult.FAIL:
            issues.extend(content_result.issues)
        
        # 5. Query sanitization
        if not issues:
            processed_query = self._sanitize_query(processed_query)
        
        status = ValidationResult.FAIL if issues else ValidationResult.PASS
        return ValidationResultData(
            status=status,
            issues=issues,
            processed_query={"original": query, "sanitized": processed_query}
        )
    
    def _validate_query_length(self, query: str) -> ValidationResultData:
        """Validate query length."""
        min_len = self.config["query_length"]["min"]
        max_len = self.config["query_length"]["max"]
        issues = []
        
        if len(query) < min_len:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="QUERY_TOO_SHORT",
                message=f"Query too short: {len(query)} characters (minimum {min_len})"
            ))
        elif len(query) > max_len:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="QUERY_TOO_LONG",
                message=f"Query too long: {len(query)} characters (maximum {max_len})"
            ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _detect_injection(self, query: str) -> ValidationResultData:
        """Detect injection patterns in query."""
        issues = []
        
        for pattern_name, pattern in self._injection_patterns.items():
            if pattern.search(query):
                issues.append(ValidationIssue(
                    level=GuardrailLevel.CRITICAL,
                    code=f"{pattern_name.upper()}_DETECTED",
                    message=f"Potential {pattern_name} detected in query"
                ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _filter_content(self, query: str) -> ValidationResultData:
        """Filter toxic content and PII."""
        issues = []
        
        # Check for API keys (simplified pattern)
        api_key_pattern = re.compile(r"(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*[a-zA-Z0-9]{10,}", re.IGNORECASE)
        if api_key_pattern.search(query):
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="API_KEY_DETECTED",
                message="API key detected in query"
            ))
        
        # Check for email addresses (potential PII)
        email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        if email_pattern.search(query):
            issues.append(ValidationIssue(
                level=GuardrailLevel.MEDIUM,
                code="EMAIL_DETECTED",
                message="Email address detected (potential PII)"
            ))
        
        return ValidationResultData(
            status=ValidationResult.FAIL if issues else ValidationResult.PASS,
            issues=issues
        )
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize query by removing potentially dangerous characters."""
        # Remove excessive whitespace and normalize
        sanitized = re.sub(r'\s+', ' ', query).strip()
        
        # Remove potential injection characters (basic sanitization)
        dangerous_chars = ['<', '>', '"', "'", ';', '|', '&', '$', '`']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized


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
        """Load ticker whitelist."""
        return {
            "VNM", "VIC", "VCB", "MSN", "FPT", "GAS", "HPG", "PLX", "MWG", "CTG",
            "BID", "ACB", "SHB", "STB", "TPB", "EIB", "HDB", "TCB", "VIB", "LPB",
            "SSB", "BAB", "BCM", "BSR", "CTD", "DIG", "DXG", "GMD", "HSG", "KDH",
            "LCG", "LGC", "LIX", "NVL", "PDR", "REE", "SBT", "SCR", "SHP", "TCH",
            "TDC", "TDG", "TID", "TNA", "TNC", "TPC", "VCG", "VCS", "VHC", "VHM",
            "VIB", "VIC", "VIF", "VNG", "VRC", "VRE", "VSC", "WAC", "WBS", "WEC"
        }
    
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
    
    def _validate_dates(self, start_date: str, end_date: str) -> ValidationResultData:
        """Validate date range."""
        issues = []
        
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
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


class RateLimiter:
    """Rate limiting for sessions."""
    
    def __init__(self, config: Dict[str, int]):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.requests_per_hour = config.get("requests_per_hour", 100)
        self.requests_per_minute = config.get("requests_per_minute", 10)
        self._session_requests = defaultdict(list)
    
    def check_rate_limit(self, session_id: str) -> ValidationResultData:
        """Check if session has exceeded rate limits."""
        issues = []
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(session_id, current_time)
        
        # Check minute limit
        minute_requests = [req_time for req_time in self._session_requests[session_id] 
                          if current_time - req_time < 60]
        if len(minute_requests) >= self.requests_per_minute:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="RATE_LIMIT_EXCEEDED_MINUTE",
                message=f"Rate limit exceeded: {len(minute_requests)}/{self.requests_per_minute} requests per minute"
            ))
        
        # Check hour limit
        hour_requests = [req_time for req_time in self._session_requests[session_id] 
                        if current_time - req_time < 3600]
        if len(hour_requests) >= self.requests_per_hour:
            issues.append(ValidationIssue(
                level=GuardrailLevel.HIGH,
                code="RATE_LIMIT_EXCEEDED_HOUR",
                message=f"Rate limit exceeded: {len(hour_requests)}/{self.requests_per_hour} requests per hour"
            ))
        
        # Record this request
        self._session_requests[session_id].append(current_time)
        
        status = ValidationResult.FAIL if issues else ValidationResult.PASS
        return ValidationResultData(status=status, issues=issues)
    
    def _clean_old_requests(self, session_id: str, current_time: float):
        """Clean old requests from session."""
        self._session_requests[session_id] = [
            req_time for req_time in self._session_requests[session_id]
            if current_time - req_time < 3600  # Keep last hour
        ]


# Global guardrails instances
_input_guardrails: Optional[InputGuardrails] = None
_step_guardrails: Optional[StepWiseGuardrails] = None
_output_guardrails: Optional[OutputGuardrails] = None


def get_input_guardrails() -> InputGuardrails:
    """Get global input guardrails instance."""
    global _input_guardrails
    if _input_guardrails is None:
        _input_guardrails = InputGuardrails()
    return _input_guardrails


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


def set_guardrails_instances(
    input_guardrails: InputGuardrails,
    step_guardrails: StepWiseGuardrails,
    output_guardrails: OutputGuardrails
) -> None:
    """Set global guardrails instances (for testing)."""
    global _input_guardrails, _step_guardrails, _output_guardrails
    _input_guardrails = input_guardrails
    _step_guardrails = step_guardrails
    _output_guardrails = output_guardrails
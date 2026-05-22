"""Unit tests for output guardrails — all methods."""

from langchain_core.messages import ToolMessage, AIMessage

from infrastructure.guardrails.output_guardrails import (
    get_output_guardrails,
    OutputGuardrails,
    ValidationResult,
)


def _guardrails():
    return get_output_guardrails()


def test_output_guardrails_initializes():
    g = _guardrails()
    assert g is not None


# -- __init__ & config -----------------------------------------------------


def test_init_with_custom_config():
    g = OutputGuardrails({"response_length": {"max": 500}})
    assert g.config["response_length"]["max"] == 500


def test_init_default_config():
    g = OutputGuardrails()
    assert "response_length" in g.config
    assert g.config["response_length"]["max"] == 2000
    assert g.config["pii_detection"] is True


def test_default_config_has_expected_structure():
    g = OutputGuardrails()
    assert "financial_bounds" in g.config
    assert "pe_ratio" in g.config["financial_bounds"]
    assert "response_length" in g.config


# -- validate_tool_results -------------------------------------------------


def test_validate_tool_results_all_errors():
    g = _guardrails()
    msgs = [
        AIMessage(content="let me check"),
        ToolMessage(content="TOOL_ERR# API failed", tool_call_id="1"),
        ToolMessage(content="TOOL_ERR# no data", tool_call_id="2"),
    ]
    result = g.validate_tool_results(msgs)
    assert result is not None
    assert "Không thể lấy dữ liệu" in result


def test_validate_tool_results_some_success():
    g = _guardrails()
    msgs = [
        ToolMessage(content="some data", tool_call_id="1"),
        ToolMessage(content="TOOL_ERR# partial fail", tool_call_id="2"),
    ]
    result = g.validate_tool_results(msgs)
    assert result is None


def test_validate_tool_results_no_tool_msgs():
    g = _guardrails()
    msgs = [AIMessage(content="hello")]
    result = g.validate_tool_results(msgs)
    assert result is None


def test_validate_tool_results_empty():
    g = _guardrails()
    result = g.validate_tool_results([])
    assert result is None


# -- _validate_response_length ---------------------------------------------


def test_response_length_within_limit():
    g = _guardrails()
    result = g._validate_response_length("short")
    assert result.status == ValidationResult.PASS


def test_response_length_exceeds_limit():
    g = _guardrails()
    long_text = "x" * 3000
    result = g._validate_response_length(long_text)
    assert result.status == ValidationResult.FAIL
    assert any(i.code == "RESPONSE_TOO_LONG" for i in result.issues)


# -- _detect_pii -----------------------------------------------------------


def test_detect_pii_email():
    g = _guardrails()
    result = g._detect_pii("contact me at test@example.com")
    assert result.status == ValidationResult.FAIL
    assert any(i.code == "PII_EMAIL_DETECTED" for i in result.issues)


def test_detect_pii_phone_vn():
    g = _guardrails()
    result = g._detect_pii("số điện thoại 0912345678")
    assert result.status == ValidationResult.FAIL
    assert any(i.code == "PII_PHONE_DETECTED" for i in result.issues)


def test_detect_pii_phone_with_country_code():
    g = _guardrails()
    result = g._detect_pii("call +84123456789")
    assert result.status == ValidationResult.FAIL
    assert any(i.code == "PII_PHONE_DETECTED" for i in result.issues)


def test_detect_pii_no_pii():
    g = _guardrails()
    result = g._detect_pii("VCB stock price is 100,000 VND")
    assert result.status == ValidationResult.PASS


def test_detect_pii_empty_string():
    g = _guardrails()
    result = g._detect_pii("")
    assert result.status == ValidationResult.PASS


# -- _detect_api_keys ------------------------------------------------------


def test_detect_api_key_sk_pattern():
    g = _guardrails()
    result = g._detect_api_keys("my key is sk-ABCdef123456GHIjkl789012mno345PQR")
    assert result.status == ValidationResult.FAIL
    assert any(i.code == "API_KEY_DETECTED" for i in result.issues)


def test_detect_api_key_header():
    g = _guardrails()
    result = g._detect_api_keys("api_key=abcdef1234567890")
    assert result.status == ValidationResult.FAIL


def test_detect_api_key_no_key():
    g = _guardrails()
    result = g._detect_api_keys("normal financial text")
    assert result.status == ValidationResult.PASS


def test_detect_api_key_pk_pattern():
    g = _guardrails()
    result = g._detect_api_keys("pk_ABCdef123456GHIjkl789012mno345PQR")
    assert result.status == ValidationResult.FAIL


# -- _detect_anomalies -----------------------------------------------------


def test_detect_anomaly_traceback():
    g = _guardrails()
    result = g._detect_anomalies("error with traceback", "test")
    assert result.status == ValidationResult.WARNING


def test_detect_anomaly_system_keyword():
    g = _guardrails()
    result = g._detect_anomalies("system password is secret", "test")
    assert result.status == ValidationResult.WARNING


def test_detect_anomaly_normal_text():
    g = _guardrails()
    result = g._detect_anomalies("VCB có lợi nhuận tăng 20%", "test")
    assert result.status == ValidationResult.PASS


# -- _redact_pii -----------------------------------------------------------


def test_redact_pii_email():
    g = _guardrails()
    result = g._redact_pii("email: user@domain.com")
    assert "[REDACTED_EMAIL]" in result
    assert "user@domain.com" not in result


def test_redact_pii_phone():
    g = _guardrails()
    result = g._redact_pii("phone: 0912345678")
    assert "[REDACTED_PHONE]" in result
    assert "0912345678" not in result


# -- _redact_api_keys ------------------------------------------------------


def test_redact_api_keys():
    g = _guardrails()
    result = g._redact_api_keys("key=sk-ABCdef123456GHIjkl789012mno345PQR")
    assert "[REDACTED_API_KEY]" in result


def test_redact_api_keys_no_match():
    g = _guardrails()
    result = g._redact_api_keys("normal text")
    assert result == "normal text"


# -- validate_response integration -----------------------------------------


def test_validate_response_pii_triggers_redaction():
    g = _guardrails()
    result = g.validate_response("email: user@test.com", "test")
    assert result.status in (ValidationResult.FAIL, ValidationResult.WARNING)
    sanitized = result.processed_query["sanitized_response"]
    assert "[REDACTED_EMAIL]" in sanitized


def test_validate_response_none():
    g = _guardrails()
    result = g.validate_response(None, "test")
    assert result.status == ValidationResult.PASS
    assert result.processed_query["sanitized_response"] == ""


def test_validate_response_long_truncated():
    g = _guardrails()
    long_text = "x" * 2500
    result = g.validate_response(long_text, "test")
    sanitized = result.processed_query["sanitized_response"]
    assert len(sanitized) <= 2000


# -- singleton -------------------------------------------------------------


def test_get_output_guardrails_singleton():
    g1 = get_output_guardrails()
    g2 = get_output_guardrails()
    assert g1 is g2

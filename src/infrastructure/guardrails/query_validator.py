import re

from .base import Guardrail, GuardrailResult
from .config import GuardrailConfig


class QuerySizeLimit(Guardrail):
    def __init__(self, config: GuardrailConfig | None = None):
        cfg = config or GuardrailConfig()
        self.max_length = cfg.max_query_length
        self.max_ticker_count = cfg.max_ticker_count

    @property
    def name(self) -> str:
        return "query_size_limit"

    async def validate(self, query: str, client_ip: str) -> GuardrailResult:
        if len(query) > self.max_length:
            return GuardrailResult(
                passed=False,
                reason=f"Query exceeds maximum length ({self.max_length} characters).",
                status_code=400,
                metadata={
                    "type": "max_length_exceeded",
                    "length": len(query),
                    "max_length": self.max_length,
                },
            )

        return GuardrailResult(passed=True)


class TickerValidator(Guardrail):
    def __init__(self, config: GuardrailConfig | None = None):
        cfg = config or GuardrailConfig()
        self.ticker_pattern = cfg.ticker_pattern
        self.whitelist = cfg.vietnamese_tickers

    @property
    def name(self) -> str:
        return "ticker_validator"

    async def validate(self, query: str, client_ip: str) -> GuardrailResult:
        matches = re.findall(self.ticker_pattern, query.upper())
        if not matches:
            return GuardrailResult(passed=True)

        unknown = [t for t in matches if t not in self.whitelist]
        if unknown:
            return GuardrailResult(
                passed=False,
                reason=f"Unrecognized ticker(s): {', '.join(sorted(set(unknown)))}",
                status_code=400,
                metadata={
                    "type": "unknown_ticker",
                    "unknown_tickers": list(set(unknown)),
                },
            )

        return GuardrailResult(passed=True)


class PatternGuard(Guardrail):
    SQL_PATTERNS: list[re.Pattern] = [
        re.compile(r"(\bDROP\b.*\bTABLE\b|\bDROP\s+DATABASE\b)", re.I),
        re.compile(r"(\bDELETE\b.*\bFROM\b|\bTRUNCATE\b)", re.I),
        re.compile(r"(\bUNION\b.*\bSELECT\b)", re.I),
        re.compile(r"('|\")\s*(OR|AND)\s+('|\")\s*=\s*('|\")", re.I),
        re.compile(r"(\bALTER\b.*\bTABLE\b|\bCREATE\b.*\bTABLE\b)", re.I),
        re.compile(r"(\bEXEC\b|\bEXECUTE\b|\bxp_cmdshell\b)", re.I),
        re.compile(r"(\bINTO\s+OUTFILE\b|\bINTO\s+DUMPFILE\b)", re.I),
        re.compile(r"(\bLOAD_FILE\b|\bINFORMATION_SCHEMA\b)", re.I),
        re.compile(r"(\bSLEEP\b\s*\()", re.I),
        re.compile(r"\b(OR|AND)\s+\d+\s*=\s*\d+", re.I),
    ]

    SHELL_PATTERNS: list[re.Pattern] = [
        re.compile(r"[`$][({]", re.I),
        re.compile(r"\b(rm|del|rd|shred)\s+[-/][a-zA-Z]", re.I),
        re.compile(r"(\|\||&&)\s*(wget|curl|bash|sh|powershell|cmd)", re.I),
        re.compile(r"(?:subprocess|os\.system|exec|eval|execfile|compile)\s*\(", re.I),
        re.compile(r"__import__|__builtins__|__subclasses__", re.I),
        re.compile(r"import\s+os\s*;|import\s+subprocess\s*;", re.I),
    ]

    PATH_TRAVERSAL_PATTERNS: list[re.Pattern] = [
        re.compile(r"\.\.(?:[/\\\\]|%2f|%5c)", re.I),
        re.compile(r"[/\\\\]etc[/\\\\]passwd", re.I),
        re.compile(r"[/\\\\]windows[/\\\\]system32", re.I),
        re.compile(r"file://", re.I),
    ]

    @property
    def name(self) -> str:
        return "pattern_guard"

    async def validate(self, query: str, client_ip: str) -> GuardrailResult:
        for pattern in self.SQL_PATTERNS:
            if pattern.search(query):
                return GuardrailResult(
                    passed=False,
                    reason="SQL injection pattern detected.",
                    status_code=400,
                    metadata={"type": "sql_injection"},
                )

        for pattern in self.SHELL_PATTERNS:
            if pattern.search(query):
                return GuardrailResult(
                    passed=False,
                    reason="Shell injection pattern detected.",
                    status_code=400,
                    metadata={"type": "shell_injection"},
                )

        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(query):
                return GuardrailResult(
                    passed=False,
                    reason="Path traversal pattern detected.",
                    status_code=400,
                    metadata={"type": "path_traversal"},
                )

        return GuardrailResult(passed=True)

import re
from typing import ClassVar

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

    def validate(self, query: str, _client_ip: str) -> GuardrailResult:
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


_COMMON_ENGLISH_WORDS = frozenset(
    {
        "TO",
        "IS",
        "BE",
        "OR",
        "BY",
        "IN",
        "AT",
        "WE",
        "IT",
        "AS",
        "AN",
        "GO",
        "NO",
        "SO",
        "UP",
        "ON",
        "OF",
        "DO",
        "IF",
        "MY",
        "ME",
        "US",
        "HE",
        "HI",
        "THE",
        "AND",
        "FOR",
        "ARE",
        "NOT",
        "BUT",
        "YOU",
        "ALL",
        "CAN",
        "HAS",
        "WAS",
        "OUT",
        "WAY",
        "USE",
        "HOW",
        "ITS",
        "NEW",
        "NOW",
        "GET",
        "MAY",
        "SEE",
        "MAN",
        "ANY",
        "DAY",
        "SHE",
        "HER",
        "HIS",
        "OLD",
        "BIG",
        "LOT",
        "PER",
        "SET",
        "TOP",
        "END",
        "LOW",
        "PUT",
        "LET",
        "OWN",
        "FEW",
        "HIT",
        "SIX",
        "TEN",
        "TWO",
        "ONE",
        "DID",
        "YET",
        "FAR",
        "SIR",
        "TRY",
        "ASK",
        "YES",
        "RED",
        "BLUE",
        "GOLD",
        "KEY",
        "RUN",
        "CUT",
        "BUY",
        "PAY",
        "FLY",
        "FUN",
        "ICE",
        "LIE",
        "MAP",
        "RAW",
        "SEA",
        "SUN",
        "VAN",
        "WIN",
        "AGE",
        "BED",
        "BAG",
        "BOX",
        "BUS",
        "CAR",
        "CUP",
        "DOG",
        "EGG",
        "ERA",
        "EVE",
        "EYE",
        "FAT",
        "FIG",
        "GAP",
        "GAS",
        "GUN",
        "HAT",
        "JOB",
        "JOY",
        "LEG",
        "LIP",
        "NET",
        "OIL",
        "OWE",
        "PEN",
        "PIE",
        "PIG",
        "POT",
        "RIB",
        "ROD",
        "ROW",
        "RUG",
        "SAT",
        "SAW",
        "SIT",
        "SKY",
        "SON",
        "TAG",
        "TAP",
        "TIE",
        "TIN",
        "TIP",
        "TOE",
        "TON",
        "TOY",
        "TUB",
        "WAR",
        "WET",
        "WIG",
        "WIT",
        "WOE",
        "WRY",
        "YAM",
        "YEN",
        "ZIP",
        "THAN",
        "THAT",
        "THIS",
        "WITH",
        "HAVE",
        "FROM",
        "THEY",
        "BEEN",
        "CALL",
        "COME",
        "DOES",
        "EACH",
        "EVEN",
        "FIRST",
        "GOOD",
        "HERE",
        "JUST",
        "KNOW",
        "LIKE",
        "LONG",
        "LOOK",
        "MADE",
        "MORE",
        "MOVE",
        "MOST",
        "MUCH",
        "MUST",
        "NEED",
        "ONLY",
        "OPEN",
        "OVER",
        "PART",
        "SAID",
        "SAME",
        "SHOW",
        "SOME",
        "SUCH",
        "TAKE",
        "TELL",
        "THEN",
        "TIME",
        "UNDER",
        "VERY",
        "WANT",
        "WELL",
        "WHAT",
        "WHEN",
        "WILL",
        "WOULD",
        "YOUR",
    }
)


class TickerValidator(Guardrail):
    def __init__(self, config: GuardrailConfig | None = None):
        cfg = config or GuardrailConfig()
        self.ticker_pattern = cfg.ticker_pattern
        self.whitelist = cfg.vietnamese_tickers

    @property
    def name(self) -> str:
        return "ticker_validator"

    def validate(self, query: str, _client_ip: str) -> GuardrailResult:
        matches = re.findall(self.ticker_pattern, query.upper())
        if not matches:
            return GuardrailResult(passed=True)

        unknown = [t for t in matches if t not in self.whitelist and t not in _COMMON_ENGLISH_WORDS]
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
    SQL_PATTERNS: ClassVar[list[re.Pattern]] = [
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

    SHELL_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"[`$][({]", re.I),
        re.compile(r"\b(rm|del|rd|shred)\s+[-/][a-zA-Z]", re.I),
        re.compile(r"(\|\||&&)\s*(wget|curl|bash|sh|powershell|cmd)", re.I),
        re.compile(r"(?:subprocess|os\.system|exec|eval|execfile|compile)\s*\(", re.I),
        re.compile(r"__import__|__builtins__|__subclasses__", re.I),
        re.compile(r"import\s+os\s*;|import\s+subprocess\s*;", re.I),
    ]

    PATH_TRAVERSAL_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"(?:\.\.|%2e%2e)(?:[/\\\\]|%2f|%5c)", re.I),
        re.compile(r"[/\\\\]etc[/\\\\]passwd", re.I),
        re.compile(r"[/\\\\]windows[/\\\\]system32", re.I),
        re.compile(r"file://", re.I),
    ]

    MARKDOWN_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"\[.*?\]\s*\(\s*(?:javascript|vbscript|data)\s*:", re.I),
        re.compile(r"<.*?(?:onerror|onload|onclick|onmouseover)\s*=", re.I),
        re.compile(r"data\s*:\s*(?:text/html|application/x-javascript|application/xml)", re.I),
    ]

    @property
    def name(self) -> str:
        return "pattern_guard"

    def validate(self, query: str, _client_ip: str) -> GuardrailResult:
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

        for pattern in self.MARKDOWN_PATTERNS:
            if pattern.search(query):
                return GuardrailResult(
                    passed=False,
                    reason="Markdown or data URI injection pattern detected.",
                    status_code=400,
                    metadata={"type": "markdown_injection"},
                )

        return GuardrailResult(passed=True)

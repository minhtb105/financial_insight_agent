import re
import unicodedata

from .base import Guardrail, GuardrailResult
from .config import GuardrailConfig

INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|messages|context|prompts?)", re.I),
    re.compile(r"(you\s+are\s+(not|now)|you.ve?\s+been\s+(replaced|hacked)|you\s+must\s+obey)", re.I),
    re.compile(r"(forget|ignore|disregard|bypass)\s+(everything|previous|all)", re.I),
    re.compile(r"(system\s+prompt|initial\s+prompt|original\s+instructions)", re.I),
    re.compile(r"<<SYS>>|\[INST\]|<\|im_start\|>|<\|sys\|>", re.I),
    re.compile(r"(repeat|print|output|show|reveal|display|dump)\s+(the\s+)?(above|entire|full|whole)\s+(prompt|instruction|message|text|system)", re.I),
    re.compile(r"DAN|jail.?break|unfiltered|no\s+(filter|restrictions|limits|rules|boundaries)", re.I),
    re.compile(r"role\s*:\s*system|role\s*:\s*assistant", re.I),
    re.compile(r"pretend\s+(to\s+be|you.are)\s+(an?|the)\s+(AI|AGI|unrestricted|free|unfiltered)", re.I),
    re.compile(r"(new\s+)?instructions?\s*[:：]", re.I),
    re.compile(r"(answer|respond|reply)\s+(in\s+)?(base64|hex|binary|json|yaml|xml|markdown)", re.I),
    re.compile(r"(from\s+)?now\s+on(wards?)?,\s*(you\s+)?(are|will|must)", re.I),
    re.compile(r"(overwrite|override|replace)\s+(the\s+)?(system|default|original)", re.I),
]

HOMOGLYPHS: dict[str, str] = {
    "\u0430": "a",
    "\u0435": "e",
    "\u043E": "o",
    "\u0440": "p",
    "\u0441": "c",
    "\u0445": "x",
    "\u0456": "i",
    "\u0455": "s",
    "\u0432": "b",
    "\u043A": "k",
    "\u041C": "M",
    "\u041D": "H",
    "\u0420": "P",
    "\u0421": "C",
    "\u0425": "X",
    "\u0410": "A",
    "\u0415": "E",
    "\u041E": "O",
    "\u0422": "T",
    "\u0401": "E",
}

ZERO_WIDTH_CHARS: set[str] = {
    "\u200B",
    "\u200C",
    "\u200D",
    "\uFEFF",
    "\u200E",
    "\u200F",
    "\u2060",
    "\u2061",
    "\u2062",
    "\u2063",
    "\u2064",
}

SUSPICIOUS_KEYWORDS: list[re.Pattern] = [
    re.compile(r"<script[^>]*>", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"onerror\s*=|onload\s*=|onclick\s*=", re.I),
]


class ContentFilter(Guardrail):
    def __init__(self, config: GuardrailConfig | None = None):
        cfg = config or GuardrailConfig()
        self.max_special_char_ratio = cfg.max_special_char_ratio
        self.max_uppercase_ratio = cfg.max_uppercase_ratio

    @property
    def name(self) -> str:
        return "content_filter"

    def _has_zero_width(self, text: str) -> bool:
        for ch in text:
            if ch in ZERO_WIDTH_CHARS:
                return True
        return False

    def _has_homoglyph(self, text: str) -> bool:
        for ch in text:
            if ch in HOMOGLYPHS:
                return True
        return False

    def _normalize_homoglyphs(self, text: str) -> str:
        result = []
        for ch in text:
            if ch in HOMOGLYPHS:
                result.append(HOMOGLYPHS[ch])
            else:
                result.append(ch)
        return "".join(result)

    def _strip_zero_width(self, text: str) -> str:
        return "".join(ch for ch in text if ch not in ZERO_WIDTH_CHARS)

    def _has_high_uppercase_ratio(self, text: str) -> bool:
        letters = [ch for ch in text if ch.isalpha()]
        if not letters:
            return False
        upper_count = sum(1 for ch in letters if ch.isupper())
        return (upper_count / len(letters)) > self.max_uppercase_ratio

    def _has_high_special_char_ratio(self, text: str) -> bool:
        if not text:
            return False
        special_count = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
        return (special_count / len(text)) > self.max_special_char_ratio

    def _detect_base64(self, text: str) -> bool:
        b64_pattern = re.compile(
            r"(?:[A-Za-z0-9+/]{40,}(?:[A-Za-z0-9+/]*={0,2})?)"
        )
        matches = b64_pattern.findall(text)
        for match in matches:
            if len(match) >= 40:
                alnum = sum(1 for ch in match if ch.isalnum())
                if alnum / len(match) > 0.8:
                    return True
        return False

    def _detect_token_separator_abuse(self, text: str) -> bool:
        sep_patterns = [
            r"-{10,}",
            r"_{10,}",
            r"={10,}",
            r"#{5,}",
            r"\*{5,}",
            r"\n\s*\n\s*\n",
        ]
        for pattern in sep_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _detect_unicode_normalization_attack(self, text: str) -> bool:
        nfkd = unicodedata.normalize("NFKD", text)
        if nfkd != text:
            suspicious = re.findall(r'[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF\u20D0-\u20FF\uFE00-\uFE0F]', text)
            return len(suspicious) > 5
        return False

    def normalize_query(self, query: str) -> str:
        normalized = self._strip_zero_width(query)
        normalized = self._normalize_homoglyphs(normalized)
        return normalized

    def validate(self, query: str, client_ip: str) -> GuardrailResult:
        nfkd_checks = unicodedata.normalize("NFKD", query)

        raw = query
        normalized = self.normalize_query(raw).lower()

        injection_found = None
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(normalized)
            if match:
                injection_found = match.group(0)
                break

        if not injection_found:
            for pattern in INJECTION_PATTERNS:
                match = pattern.search(nfkd_checks.lower())
                if match:
                    injection_found = match.group(0)
                    break

        if injection_found:
            return GuardrailResult(
                passed=False,
                reason=f"Prompt injection detected: pattern '{injection_found}'",
                status_code=400,
                metadata={"pattern": injection_found, "type": "prompt_injection"},
            )

        for pattern in SUSPICIOUS_KEYWORDS:
            if pattern.search(normalized):
                return GuardrailResult(
                    passed=False,
                    reason="Suspicious script or event handler detected.",
                    status_code=400,
                    metadata={"type": "xss_or_script"},
                )

        if self._has_zero_width(raw):
            return GuardrailResult(
                passed=False,
                reason="Query contains zero-width characters (possible obfuscation).",
                status_code=400,
                metadata={"type": "zero_width_chars"},
            )

        if self._has_homoglyph(raw):
            return GuardrailResult(
                passed=False,
                reason="Query contains homoglyph characters (possible obfuscation).",
                status_code=400,
                metadata={"type": "homoglyph_detected"},
            )

        if self._has_high_uppercase_ratio(raw):
            return GuardrailResult(
                passed=False,
                reason="Suspiciously high uppercase ratio.",
                status_code=400,
                metadata={"type": "high_uppercase_ratio"},
            )

        if self._has_high_special_char_ratio(raw):
            return GuardrailResult(
                passed=False,
                reason="Suspiciously high special character ratio.",
                status_code=400,
                metadata={"type": "high_special_char_ratio"},
            )

        if self._detect_base64(raw):
            return GuardrailResult(
                passed=False,
                reason="Base64 encoded payload detected.",
                status_code=400,
                metadata={"type": "base64_payload"},
            )

        if self._detect_token_separator_abuse(raw):
            return GuardrailResult(
                passed=False,
                reason="Excessive token separators detected (possible context overflow attempt).",
                status_code=400,
                metadata={"type": "separator_abuse"},
            )

        if self._detect_unicode_normalization_attack(raw):
            return GuardrailResult(
                passed=False,
                reason="Unicode normalization attack detected.",
                status_code=400,
                metadata={"type": "unicode_attack"},
            )

        return GuardrailResult(passed=True)

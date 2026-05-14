import warnings
from typing import Dict, Any, Tuple, Optional

from infrastructure.llm.query_preprocessor import QueryPreprocessor
from .llm_provider import LLMProvider
from .two_phase_parser import TwoPhaseParser

warnings.warn(
    "nlp_parser.py is deprecated. Use TwoPhaseParser instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)


class QueryParser:
    def __init__(self, model: Optional[str] = None, llm_provider: Optional[LLMProvider] = None):
        self._two_phase = TwoPhaseParser(llm_provider=llm_provider)
        self.preprocessor = QueryPreprocessor()

    def parse(self, query: str) -> Dict[str, Any]:
        return self._two_phase.parse(query)

    def parse_with_confidence(self, query: str) -> Tuple[Dict[str, Any], float]:
        result = self._two_phase.parse(query)
        return result, 0.85
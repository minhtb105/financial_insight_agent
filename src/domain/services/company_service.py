from data.indicators import get_company_info
from typing import Dict, Any


class CompanyService:
    """
    Handle company_query:
    - shareholders
    - subsidiaries
    - executives
    """

    def handle(self, parsed: Dict[str, Any]):
        tickers = parsed.get("tickers") or []
        if not tickers:
            return {"error": "Missing ticker"}

        try:
            return get_company_info(parsed)
        except Exception as e:
            return {"error": str(e)}

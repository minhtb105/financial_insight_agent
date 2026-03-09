# application/handlers/query_router.py

from typing import Any, Dict

from domain.entities.query_type import QueryType
from .result_formatter import ok, fail

# Import các service thuộc domain
from domain.services.market.price_service import handle_price_query
from domain.services.market.indicator_service import handle_indicator_query
from domain.services.company.company_service import handle_company_query
from domain.services.market.compare_service import handle_compare_query
from domain.services.financial.ranking_service import handle_ranking_query
from domain.services.financial.aggregate_service import handle_aggregate_query


class QueryRouter:

    def __init__(self):
        # Có thể dùng nếu sau này bạn DI (Dependency Injection)
        pass

    def dispatch(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Nhận JSON từ parser và route đến service tương ứng.
        """
        if not parsed or "query_type" not in parsed:
            return fail("Không có query_type trong parsed request", {"parsed": parsed})

        try:
            qtype = QueryType(parsed["query_type"])
        except Exception:
            return fail(f"query_type không hợp lệ: {parsed.get('query_type')}",
                        {"parsed": parsed})

        # --------- Route ----------

        if qtype == QueryType.price_query:
            return handle_price_query(parsed)

        elif qtype == QueryType.indicator_query:
            return handle_indicator_query(parsed)

        elif qtype == QueryType.company_query:
            return handle_company_query(parsed)

        elif qtype == QueryType.comparison_query:
            return handle_compare_query(parsed)

        elif qtype == QueryType.ranking_query:
            return handle_ranking_query(parsed)

        elif qtype == QueryType.aggregate_query:
            return handle_aggregate_query(parsed)

        return fail(f"Chưa hỗ trợ query_type: {qtype}", {"parsed": parsed})

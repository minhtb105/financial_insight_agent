from typing import Any, Dict
import logging

from domain.entities.query_type import QueryType
from application.handler.result_formatter import ok, fail

from domain.services.market.price_service import handle_price_query
from domain.services.market.indicator_service import handle_indicator_query
from domain.services.company.company_service import handle_company_query
from domain.services.market.compare_service import handle_compare_query
from domain.services.financial.ranking_service import handle_ranking_query
from domain.services.financial.aggregate_service import handle_aggregate_query
from domain.services.financial.financial_ratio_service import handle_financial_ratio_query
from domain.services.portfolio.news_sentiment_service import handle_news_sentiment_query
from domain.services.portfolio.portfolio_service import handle_portfolio_query
from infrastructure.llm.nlp_parser import QueryParser


class QueryRouter:
    """
    Router for handling and dispatching queries to appropriate services.
    
    This class provides two main methods:
    - dispatch(): Routes already parsed queries to service handlers
    - route_query(): Parses raw query strings and routes them to services
    
    The route_query method bridges the gap between raw user queries and service routing
    by using QueryParser to extract query_type and then mapping it to the appropriate service.
    """

    def __init__(self):
        """Initialize QueryRouter with required dependencies."""
        self.parser = QueryParser()
        self.logger = logging.getLogger(__name__)
        
        # Query type to service mapping
        self.query_type_to_service = {
            QueryType.price_query: "price_service",
            QueryType.indicator_query: "indicator_service", 
            QueryType.company_query: "company_service",
            QueryType.comparison_query: "comparison_service",
            QueryType.ranking_query: "ranking_service",
            QueryType.aggregate_query: "aggregate_service",
            QueryType.financial_ratio_query: "financial_ratio_service",
            QueryType.news_sentiment_query: "news_sentiment_service",
            QueryType.portfolio_query: "portfolio_service"
        }

    def route_query(self, query: str) -> Dict[str, str]:
        """
        Route a raw query string to the appropriate service.
        
        This method:
        1. Uses QueryParser to parse the raw Vietnamese query string
        2. Extracts query_type from the parse result
        3. Maps query_type enum to service name string
        4. Returns {"service": service_name}
        
        Args:
            query: Raw query string in Vietnamese
            
        Returns:
            Dictionary with service name, e.g., {"service": "price_service"}
            
        Raises:
            ValueError: If query is empty or cannot be parsed
        """
        if not query or not query.strip():
            self.logger.error("Empty query provided to route_query")
            raise ValueError("Query cannot be empty")
        
        try:
            # Parse the raw query using QueryParser
            self.logger.debug(f"Parsing query: {query}")
            parsed_result = self.parser.parse(query)
            
            # Extract query_type from parse result
            query_type_str = parsed_result.get("query_type")
            if not query_type_str:
                self.logger.error(f"Could not extract query_type from parsed result: {parsed_result}")
                raise ValueError("Could not determine query type")
            
            # Convert to QueryType enum and map to service name
            try:
                query_type = QueryType(query_type_str)
                service_name = self.query_type_to_service.get(query_type)
                
                if not service_name:
                    self.logger.error(f"Unsupported query type: {query_type}")
                    raise ValueError(f"Unsupported query type: {query_type}")
                
                self.logger.info(f"Routed query '{query}' to {service_name}")
                return {"service": service_name}
                
            except ValueError as e:
                self.logger.error(f"Invalid query type '{query_type_str}': {e}")
                raise ValueError(f"Invalid query type: {query_type_str}")
                
        except Exception as e:
            self.logger.error(f"Error parsing query '{query}': {e}")
            raise ValueError(f"Failed to parse query: {str(e)}")

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

        elif qtype == QueryType.financial_ratio_query:
            return handle_financial_ratio_query(parsed)

        elif qtype == QueryType.news_sentiment_query:
            return handle_news_sentiment_query(parsed)

        elif qtype == QueryType.portfolio_query:
            # Handle portfolio data if provided
            portfolio_data = parsed.get("portfolio")
            if portfolio_data:
                # Create a temporary portfolio manager with the provided data
                from domain.services.portfolio.portfolio_service import PortfolioManager
                portfolio_manager = PortfolioManager()
                current_holdings = portfolio_manager.get_holdings()
                
                # Merge with existing holdings
                for ticker, quantity in portfolio_data.items():
                    if ticker not in current_holdings:
                        current_holdings[ticker] = 0
                    current_holdings[ticker] += quantity
                
                # Update portfolio temporarily for this query
                portfolio_manager.portfolio["holdings"] = current_holdings
            
            return handle_portfolio_query(parsed)

        return fail(f"Chưa hỗ trợ query_type: {qtype}", {"parsed": parsed})

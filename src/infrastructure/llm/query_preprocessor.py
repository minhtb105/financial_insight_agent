import datetime
import re
from typing import Dict, List, Any, Optional


class QueryPreprocessor:
    """
    Rule-based preprocessor for Vietnamese stock queries.
    Extracts tickers, time params, and indicator params using regex patterns.
    """
    
    def __init__(self):
        # Ticker patterns
        self.ticker_pattern = r'\b[A-Z]{2,4}\b'
        self.vietnamese_tickers = {
            'VCB', 'HPG', 'VIC', 'VHM', 'SSI', 'TCB', 'CTG', 'BID', 'MBB', 'ACB',
            'VPB', 'HDB', 'SHB', 'STB', 'EIB', 'VRE', 'PNJ', 'MWG', 'FPT', 'GAS',
            'PLX', 'BVH', 'VNM', 'MSN', 'REE', 'HSG', 'NKG', 'DXG', 'KDH', 'NLG',
            'VCI', 'HCM', 'PVI', 'BMI', 'POW', 'NT2', 'PC1', 'QNS', 'MCH', 'HAG',
            'HNG', 'TTF', 'VCG', 'MSB', 'SAB', 'VJC', 'ACV', 'SBT', 'VGC', 'VIB'
        }
        
        # Time patterns - Keep minimal patterns for fallback only
        # Main time extraction will be done by LLM
        self.time_patterns = {
            'days': [
                (r'(\d+)\s*(ngày|day)', lambda m: int(m.group(1))),
            ],
            'weeks': [
                (r'(\d+)\s*(tuần|week)', lambda m: int(m.group(1))),
            ],
            'months': [
                (r'(\d+)\s*(tháng|month)', lambda m: int(m.group(1))),
            ],
            'years': [
                (r'(\d+)\s*(năm|year)', lambda m: int(m.group(1))),
            ]
        }
        
        # Indicator patterns
        self.indicator_patterns = {
            'sma': r'SMA(\d+)',
            'ema': r'EMA(\d+)',
            'rsi': r'RSI(\d+)',
            'macd': r'MACD(?:\((\d+),(\d+)\))?',
            'bb': r'(?<!\w)BB(?!\w)|Bollinger',
            'stochastic': r'Stochastic|STOCH',
            'adx': r'ADX',
            'atr': r'ATR',
            'obv': r'OBV',
            'cci': r'CCI'
        }
        
        # Query type keywords
        self.comparison_keywords = {
            'so sánh', 'compare', 'compare with', 'so sánh với', 'so sánh và'
        }
        
        self.ranking_keywords = {
            'mã nào cao nhất', 'mã nào thấp nhất', 'which of', 'which has the highest',
            'which has the lowest', 'trong các mã', 'mã nào lớn nhất', 'mã nào nhỏ nhất',
            'mã nào tốt nhất', 'mã nào xấu nhất', 'mã nào mạnh nhất', 'mã nào yếu nhất',
            'mã nào tăng nhiều nhất', 'mã nào giảm nhiều nhất', 'mã nào dẫn đầu', 'mã nào đi sau',
            'top', 'bottom', 'highest', 'lowest', 'best', 'worst', 'leading', 'lagging',
            'cao nhất', 'thấp nhất', 'lớn nhất', 'nhỏ nhất',
            'tăng mạnh nhất', 'giảm mạnh nhất', 'mạnh nhất', 'yếu nhất'
        }
        
        self.aggregate_keywords = {
            'tổng', 'sum', 'cộng dồn', 'trung bình', 'average', 'avg', 'bình quân',
            'nhỏ nhất', 'thấp nhất', 'cao nhất', 'lớn nhất', 'min', 'max', 'median',
            'đầu tiên', 'cuối cùng', 'first', 'last'
        }
        
        self.price_keywords = {
            'giá', 'open', 'close', 'volume', 'ohlcv', 'mở cửa', 'đóng cửa', 'khối lượng'
        }
        
        self.indicator_keywords = {
            'SMA', 'EMA', 'RSI', 'MACD', 'MA', 'chỉ báo', 'indicator'
        }
        
        self.company_keywords = {
            'cổ đông', 'shareholders', 'lãnh đạo', 'executives', 'CEO', 'BOD', 'board',
            'công ty con', 'subsidiary', 'công ty mẹ', 'company', 'doanh nghiệp'
        }
        
        self.financial_ratio_keywords = {
            'P/E', 'PE', 'P/B', 'PB', 'ROE', 'EPS', 'tỷ lệ', 'ratio', 'financial ratio',
            'giá trên lợi nhuận', 'giá trên sổ sách', 'tỷ suất sinh lời', 'lợi nhuận trên vốn'
        }
        
        self.news_sentiment_keywords = {
            'tin tức', 'news', 'cảm xúc', 'sentiment', 'tích cực', 'tiêu cực', 'thị trường',
            'social', 'volume', 'đánh giá', 'phân tích', 'bình luận'
        }
        
        self.portfolio_keywords = {
            'danh mục', 'portfolio', 'hiệu suất', 'performance', 'phân bổ', 'allocation',
            'ngành', 'sector', 'đa dạng', 'diversification', 'giá trị', 'value'
        }

    def extract_tickers(self, query: str) -> List[str]:
        """Extract tickers using regex and validate against known list."""
        matches = re.findall(self.ticker_pattern, query.upper())
        valid_tickers = []
        
        for ticker in matches:
            if ticker in self.vietnamese_tickers:
                valid_tickers.append(ticker)
            else:
                # Try to correct common typos
                corrected = self.correct_ticker(ticker)
                if corrected and corrected in self.vietnamese_tickers:
                    valid_tickers.append(corrected)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for ticker in valid_tickers:
            if ticker not in seen:
                seen.add(ticker)
                result.append(ticker)
        
        return result

    def correct_ticker(self, ticker: str) -> Optional[str]:
        """Correct common ticker typos."""
        corrections = {
            'VBC': 'VCB', 'HGP': 'HPG', 'VHC': 'VHC', 'VHM': 'VHM',
            'SS': 'SSI', 'TC': 'TCB', 'CT': 'CTG', 'BD': 'BID',
            'MB': 'MBB', 'AC': 'ACB', 'VP': 'VPB', 'HD': 'HDB',
            'SH': 'SHB', 'ST': 'STB', 'EI': 'EIB', 'VR': 'VRE',
            'PN': 'PNJ', 'MW': 'MWG', 'FP': 'FPT', 'GA': 'GAS',
            'PL': 'PLX', 'BV': 'BVH', 'VN': 'VNM', 'MS': 'MSN',
            'RE': 'REE', 'HS': 'HSG', 'NK': 'NKG', 'DX': 'DXG',
            'KD': 'KDH', 'NL': 'NLG', 'VC': 'VCI', 'HC': 'HCM',
            'PV': 'PVI', 'BM': 'BMI', 'PO': 'POW', 'NT': 'NT2',
            'PC': 'PC1', 'QN': 'QNS', 'MC': 'MCH', 'HA': 'HAG',
            'HN': 'HNG', 'TT': 'TTF', 'VG': 'VCG', 'SB': 'SBT',
            'VJ': 'VJC', 'AC': 'ACV', 'VG': 'VGC', 'VI': 'VIB'
        }
        return corrections.get(ticker)

    def extract_time_params(self, query: str) -> Dict[str, Any]:
        """Extract time parameters from query."""
        query_lower = query.lower()
        result = {}
        
        # Check for specific date patterns
        date_pattern = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4}|\d{2})'
        date_matches = re.findall(date_pattern, query)
        if date_matches:
            # Convert to YYYY-MM-DD format
            for day, month, year in date_matches:
                if len(year) == 2:
                    year = f"20{year}"
                date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                if 'start' not in result:
                    result['start'] = date_str
                else:
                    result['end'] = date_str
        
        # Extract time ranges
        for time_type, patterns in self.time_patterns.items():
            for pattern, func in patterns:
                if re.search(pattern, query_lower):
                    match = re.search(pattern, query_lower)
                    if match:
                        value = func(match)
                        if time_type == 'days':
                            result['days'] = value
                        elif time_type == 'weeks':
                            result['weeks'] = value
                        elif time_type == 'months':
                            result['months'] = value
                        elif time_type == 'years':
                            result['years'] = value
                        break
        
        # Handle special cases
        if 'hôm qua' in query_lower:
            result['days'] = 1
            result['end'] = 'yesterday'
        elif 'hôm nay' in query_lower:
            result['days'] = 1
            result['end'] = 'today'
        elif 'tuần trước' in query_lower:
            result['weeks'] = 1
            result['end'] = 'last_week'
        elif 'tháng trước' in query_lower:
            result['months'] = 1
            result['end'] = 'last_month'
        
        return result

    def extract_indicator_params(self, query: str) -> Dict[str, List[int]]:
        """Extract indicator parameters."""
        query_upper = query.upper()
        result = {}
        
        for indicator, pattern in self.indicator_patterns.items():
            matches = re.findall(pattern, query_upper)
            if matches:
                values = []
                for match in matches:
                    if isinstance(match, tuple):  # MACD case
                        values.extend([int(x) for x in match if x])
                    elif match:
                        values.append(int(match))
                
                if values:
                    result[indicator] = values
        
        return result

    def has_financial_metrics(self, query: str) -> bool:
        """Check if query contains financial metrics keywords (ROE, P/E, EPS, etc.)."""
        query_lower = query.lower()
        query_upper = query.upper()
        
        for keyword in self.financial_ratio_keywords:
            if keyword in query_lower or keyword in query_upper:
                return True
        return False
    
    def has_ranking_keywords(self, query: str) -> bool:
        """Check if query contains ranking keywords (min, max, highest, lowest)."""
        query_lower = query.lower()
        
        for keyword in self.ranking_keywords:
            if keyword in query_lower:
                return True
        return False
    
    def has_comparison_keywords(self, query: str) -> bool:
        """Check if query contains comparison keywords."""
        query_lower = query.lower()
        
        for keyword in self.comparison_keywords:
            if keyword in query_lower:
                return True
        return False

    def detect_query_type(self, query: str, tickers: List[str]) -> str:
        """Detect query type based on keywords and patterns."""
        query_lower = query.lower()
        query_upper = query.upper()
        
        # Check for financial ratios FIRST (highest priority)
        if self.has_financial_metrics(query):
            return "financial_ratio_query"
        
        # Check for ranking keywords
        if self.has_ranking_keywords(query) and len(tickers) >= 2:
            return "ranking_query"
        
        # Check for comparison (after financial ratios)
        for keyword in self.comparison_keywords:
            if keyword in query_lower:
                return "comparison_query"
        
        # Check for aggregate
        for keyword in self.aggregate_keywords:
            if keyword in query_lower:
                return "aggregate_query"
        
        # Check for indicators
        for keyword in self.indicator_keywords:
            if keyword in query_upper:
                return "indicator_query"
        
        # Check for company info
        for keyword in self.company_keywords:
            if keyword in query_lower:
                return "company_query"
        
        # Check for news/sentiment
        for keyword in self.news_sentiment_keywords:
            if keyword in query_lower:
                return "news_sentiment_query"
        
        # Check for portfolio
        for keyword in self.portfolio_keywords:
            if keyword in query_lower:
                return "portfolio_query"
        
        # Default to price query
        return "price_query"

    def extract_requested_field(self, query: str, query_type: str) -> Optional[str]:
        """Extract requested field based on query type."""
        query_lower = query.lower()
        query_upper = query.upper()
        
        if query_type == "price_query":
            if 'giá mở' in query_lower or 'open' in query_upper:
                return "open"
            elif 'giá đóng' in query_lower or 'giá chốt' in query_lower or 'close' in query_upper:
                return "close"
            elif 'volume' in query_upper or 'khối lượng' in query_lower:
                return "volume"
            elif 'ohlcv' in query_upper:
                return "ohlcv"
            elif 'giá' in query_lower:
                return "close"  # Default for "giá"
        
        elif query_type == "indicator_query":
            if 'sma' in query_upper or 'ma' in query_upper:
                return "sma"
            elif 'rsi' in query_upper:
                return "rsi"
            elif 'macd' in query_upper:
                return "macd"
        
        elif query_type == "company_query":
            if 'cổ đông' in query_lower:
                return "shareholders"
            elif 'lãnh đạo' in query_lower or 'CEO' in query_upper or 'BOD' in query_upper:
                return "executives"
            elif 'công ty con' in query_lower:
                return "subsidiaries"
        
        elif query_type == "financial_ratio_query":
            if 'P/E' in query_upper or 'PE' in query_upper or 'giá trên lợi nhuận' in query_lower:
                return "pe"
            elif 'P/B' in query_upper or 'PB' in query_upper or 'giá trên sổ sách' in query_lower:
                return "pb"
            elif 'ROE' in query_upper or 'tỷ suất sinh lời' in query_lower or 'lợi nhuận trên vốn' in query_lower:
                return "roe"
            elif 'EPS' in query_upper:
                return "eps"
            elif 'tỷ lệ' in query_lower or 'ratio' in query_lower:
                return "financial_ratio"
        
        elif query_type == "news_sentiment_query":
            if 'tin tức' in query_lower or 'news' in query_lower:
                return "news"
            elif 'cảm xúc' in query_lower or 'sentiment' in query_lower:
                return "sentiment"
            elif 'tích cực' in query_lower:
                return "positive_news"
            elif 'tiêu cực' in query_lower:
                return "negative_news"
            elif 'social' in query_lower or 'volume' in query_lower:
                return "social_volume"
        
        elif query_type == "portfolio_query":
            if 'danh mục' in query_lower or 'portfolio' in query_lower:
                return "portfolio_summary"
            elif 'hiệu suất' in query_lower or 'performance' in query_lower:
                return "performance"
            elif 'phân bổ' in query_lower or 'allocation' in query_lower:
                return "sector_allocation"
            elif 'giá trị' in query_lower or 'value' in query_lower:
                return "portfolio_value"
        
        return None

    def extract_portfolio_data(self, query: str) -> Optional[Dict[str, int]]:
        """Extract portfolio holdings from query."""
        query_upper = query.upper()
        
        # Pattern to match portfolio holdings: "100 cổ FPT", "200 cổ VNM"
        portfolio_pattern = r'(\d+)\s*(CỔ|SHARES?)\s*([A-Z]{2,4})'
        matches = re.findall(portfolio_pattern, query_upper)
        
        if not matches:
            return None
        
        portfolio = {}
        for match in matches:
            quantity = int(match[0])
            ticker = match[2]
            if ticker in self.vietnamese_tickers:
                portfolio[ticker] = quantity
        
        return portfolio if portfolio else None

    def validate_and_correct(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and auto-correct parsed results."""
        # Validate tickers
        if parsed.get("tickers"):
            parsed["tickers"] = [self.correct_ticker(t) or t for t in parsed["tickers"]]
            parsed["tickers"] = [t for t in parsed["tickers"] if t in self.vietnamese_tickers]
        
        # Validate time parameters
        if parsed.get("start") and parsed.get("end"):
            # Ensure start <= end
            try:
                start_date = datetime.strptime(parsed["start"], "%Y-%m-%d")
                end_date = datetime.strptime(parsed["end"], "%Y-%m-%d")
                if start_date > end_date:
                    parsed["start"], parsed["end"] = parsed["end"], parsed["start"]
            except:
                pass
        
        # Validate query type and requested field consistency
        if parsed.get("query_type") == "price_query" and not parsed.get("requested_field"):
            parsed["requested_field"] = "close"  # Default
        
        if parsed.get("query_type") == "indicator_query" and not parsed.get("requested_field"):
            parsed["requested_field"] = "sma"  # Default
        
        if parsed.get("query_type") == "company_query" and not parsed.get("requested_field"):
            parsed["requested_field"] = "shareholders"  # Default
        
        # Validate comparison query
        if parsed.get("query_type") == "comparison_query":
            if not parsed.get("compare_with") and len(parsed.get("tickers", [])) > 1:
                # Split tickers: first is main, rest are compare_with
                tickers = parsed["tickers"]
                parsed["tickers"] = [tickers[0]]
                parsed["compare_with"] = tickers[1:]
        
        # Validate ranking query
        if parsed.get("query_type") == "ranking_query":
            if len(parsed.get("tickers", [])) < 2:
                # Fall back to price_query if not enough tickers
                parsed["query_type"] = "price_query"
        
        # Validate financial ratio query
        if parsed.get("query_type") == "financial_ratio_query":
            if not parsed.get("requested_field"):
                parsed["requested_field"] = "pe"  # Default financial ratio
        
        # Validate news sentiment query
        if parsed.get("query_type") == "news_sentiment_query":
            if not parsed.get("requested_field"):
                parsed["requested_field"] = "news"  # Default news sentiment field
        
        # Validate portfolio query
        if parsed.get("query_type") == "portfolio_query":
            if not parsed.get("requested_field"):
                parsed["requested_field"] = "portfolio_summary"  # Default portfolio field
        
        return parsed

    def preprocess(self, query: str) -> Dict[str, Any]:
        """Main preprocessing function."""
        # Extract basic components
        tickers = self.extract_tickers(query)
        time_params = self.extract_time_params(query)
        indicator_params = self.extract_indicator_params(query)
        
        # Detect query type and requested field
        query_type = self.detect_query_type(query, tickers)
        requested_field = self.extract_requested_field(query, query_type)
        
        # Special handling for portfolio queries with portfolio data
        query_lower = query.lower()
        portfolio_data = None
        if query_type == "portfolio_query" and ("portfolio" in query_lower or "danh mục" in query_lower):
            # Extract portfolio holdings from query
            portfolio_data = self.extract_portfolio_data(query)
        
        # Build initial result
        result = {
            "tickers": tickers,
            "query_type": query_type,
            "requested_field": requested_field,
            "indicator_params": indicator_params if indicator_params else None,
            **time_params
        }
        
        # Add portfolio data if available
        if portfolio_data:
            result["portfolio"] = portfolio_data
        
        # Validate and correct
        result = self.validate_and_correct(result)
        
        return result

    def has_financial_metrics(self, query: str) -> bool:
        """Check if query contains financial metrics keywords (ROE, P/E, EPS, etc.)."""
        query_lower = query.lower()
        query_upper = query.upper()
        
        for keyword in self.financial_ratio_keywords:
            if keyword in query_lower or keyword in query_upper:
                return True
        return False

    def calculate_confidence(self, query: str, preprocessed: Dict[str, Any]) -> float:
        """Calculate confidence score for the preprocessing result."""
        confidence = 0.0
        max_confidence = 100.0
        
        # Tickers confidence
        if preprocessed.get("tickers"):
            confidence += 30.0
        else:
            confidence += 10.0  # Low confidence if no tickers found
        
        # Query type confidence
        query_type = preprocessed.get("query_type")
        if query_type in ["price_query", "indicator_query", "company_query"]:
            confidence += 25.0
        elif query_type in ["comparison_query", "ranking_query", "aggregate_query", 
                           "financial_ratio_query", "news_sentiment_query", "portfolio_query"]:
            confidence += 20.0  # Slightly lower due to complexity
        
        # Time params confidence
        time_fields = ["days", "weeks", "months", "start", "end"]
        if any(preprocessed.get(field) for field in time_fields):
            confidence += 20.0
        else:
            confidence += 10.0  # Low confidence if no time params
        
        # Indicator params confidence (for indicator queries)
        if query_type == "indicator_query" and preprocessed.get("indicator_params"):
            confidence += 15.0
        elif query_type == "indicator_query":
            confidence += 5.0  # Low confidence if no indicator params
        
        # Normalize to 0-1 range
        return min(confidence / max_confidence, 1.0)

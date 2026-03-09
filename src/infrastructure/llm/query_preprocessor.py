import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta


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
        
        # Time patterns
        self.time_patterns = {
            'days': [
                (r'(\d+)\s*(ngày|day)', lambda m: int(m.group(1))),
                (r'hôm qua', lambda m: 1),
                (r'hôm nay', lambda m: 1),
                (r'ngày hôm qua', lambda m: 1),
                (r'ngày hôm nay', lambda m: 1),
            ],
            'weeks': [
                (r'(\d+)\s*(tuần|week)', lambda m: int(m.group(1))),
                (r'tuần trước', lambda m: 1),
                (r'tuần này', lambda m: 1),
                (r'tuần vừa rồi', lambda m: 1),
            ],
            'months': [
                (r'(\d+)\s*(tháng|month)', lambda m: int(m.group(1))),
                (r'tháng trước', lambda m: 1),
                (r'tháng này', lambda m: 1),
                (r'tháng vừa rồi', lambda m: 1),
                (r'quý 4', lambda m: 3),  # Quý 4 = 3 tháng
                (r'quý 3', lambda m: 3),
                (r'quý 2', lambda m: 3),
                (r'quý 1', lambda m: 3),
            ],
            'years': [
                (r'(\d+)\s*(năm|year)', lambda m: int(m.group(1))),
                (r'năm trước', lambda m: 1),
                (r'năm nay', lambda m: 1),
            ]
        }
        
        # Indicator patterns
        self.indicator_patterns = {
            'sma': r'SMA(\d+)',
            'ema': r'EMA(\d+)',
            'rsi': r'RSI(\d+)',
            'macd': r'MACD(?:\((\d+),(\d+)\))?',
            'bb': r'BB|Bollinger',
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
            'which has the lowest', 'trong các mã', 'mã nào lớn nhất', 'mã nào nhỏ nhất'
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

    def detect_query_type(self, query: str, tickers: List[str]) -> str:
        """Detect query type based on keywords and patterns."""
        query_lower = query.lower()
        
        # Check for comparison first (highest priority)
        for keyword in self.comparison_keywords:
            if keyword in query_lower:
                return "comparison_query"
        
        # Check for ranking
        for keyword in self.ranking_keywords:
            if keyword in query_lower and len(tickers) >= 2:
                return "ranking_query"
        
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
        
        return None

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
        
        # Build initial result
        result = {
            "tickers": tickers,
            "query_type": query_type,
            "requested_field": requested_field,
            "indicator_params": indicator_params if indicator_params else None,
            **time_params
        }
        
        # Validate and correct
        result = self.validate_and_correct(result)
        
        return result

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
        elif query_type in ["comparison_query", "ranking_query", "aggregate_query"]:
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
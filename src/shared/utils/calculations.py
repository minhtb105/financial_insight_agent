from typing import Dict, Any, List


def calculate_volatility(price_data: List[Dict[str, Any]]) -> float:
    if len(price_data) < 2:
        return 0.0

    returns = []
    for i in range(1, len(price_data)):
        prev_price = price_data[i-1]["close"]
        curr_price = price_data[i]["close"]
        if prev_price != 0:
            return_pct = (curr_price - prev_price) / prev_price
            returns.append(return_pct)

    if not returns:
        return 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    volatility = (variance ** 0.5) * (252 ** 0.5)

    return volatility * 100


def calculate_std_dev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5
from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


"""Handle company_query: shareholders, subsidiaries, executives"""


def get_company_info(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df = client.company

    field = query.get("requested_field")
    if field == "shareholders":
        return df.shareholders().to_dict(orient="records")
    elif field == "subsidiaries":
        return df.subsidiaries().to_dict(orient="records")
    elif field == "executives":
        return df.officers(filter_by='all').to_dict(orient="records")
    else:
        return df.overview().to_dict(orient="records")


def handle_company_query(parsed: Dict[str, Any]):
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    try:
        return get_company_info(parsed)
    except Exception as e:
        return {"error": str(e)}

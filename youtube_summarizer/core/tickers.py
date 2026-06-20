import csv
from pathlib import Path
from functools import lru_cache

_DATA_DIR = Path(__file__).parent.parent / "data"


@lru_cache(maxsize=1)
def _load_symbol_map() -> dict[str, dict]:
    symbol_map: dict[str, dict] = {}
    csv_path = _DATA_DIR / "nse_bse_symbols.csv"
    if not csv_path.exists():
        return symbol_map
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["symbol"].upper().strip()
            symbol_map[key] = {
                "company_name": row["company_name"],
                "exchange": row["exchange"],
                "sector": row["sector"],
            }
    return symbol_map


def validate_ticker(symbol: str) -> dict | None:
    return _load_symbol_map().get(symbol.upper().strip().replace(" ", ""))


def enrich_tickers(tickers: list[dict]) -> list[dict]:
    enriched = []
    for t in tickers:
        symbol = t.get("symbol", "").upper().strip()
        info = validate_ticker(symbol)
        result = dict(t)
        if info:
            result.setdefault("company_name", info["company_name"])
            result["exchange"] = info["exchange"]
            result["sector"] = info["sector"]
            result["validated"] = True
        else:
            result.setdefault("exchange", "NSE")
            result.setdefault("sector", "Unknown")
            result["validated"] = False
        enriched.append(result)
    return enriched

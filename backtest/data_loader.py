"""
backtest/data_loader.py
Historical data gateway for Phase 4 backtesting.

Loads and normalizes four data types from CSV files:
  1. price history   — daily OHLCV
  2. chain history   — daily option chain snapshots
  3. volatility history — IV, ATR, skew inputs
  4. GEX history     — pre-computed gamma context (optional)

File paths:
  data/historical/prices/{symbol}_prices.csv
  data/historical/chains/{symbol}_chains.csv
  data/historical/volatility/{symbol}_volatility.csv
  data/historical/gamma/{symbol}_gamma.csv

Schema contracts are defined in backtest/schemas.py.
All normalize_* functions must produce rows compatible with the live engine.
"""

from __future__ import annotations

import csv
from pathlib import Path
from backtest.utils import safe_float, safe_int


BASE_DIR = Path(__file__).parent.parent / "data" / "historical"


# ─────────────────────────────────────────────
# LOW-LEVEL CSV HELPERS
# ─────────────────────────────────────────────

def load_csv(path: str | Path) -> list[dict]:
    """Load a CSV file into a list of row dicts. Raises FileNotFoundError if missing."""
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def filter_rows_by_date(
    rows: list[dict],
    start: str,
    end: str,
    date_key: str = "date",
) -> list[dict]:
    """Return rows where date_key is between start and end inclusive."""
    return [r for r in rows if start <= r.get(date_key, "") <= end]


def group_rows_by_date(
    rows: list[dict],
    date_key: str = "date",
) -> dict[str, list[dict]]:
    """Group rows into a dict keyed by date string."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        key = row.get(date_key, "")
        grouped.setdefault(key, []).append(row)
    return grouped


# ─────────────────────────────────────────────
# NORMALIZATION
# ─────────────────────────────────────────────

def normalize_price_row(row: dict, symbol: str) -> dict:
    """Normalize a raw price CSV row to a clean daily price dict."""
    return {
        "date":   row["date"],
        "symbol": symbol,
        "open":   safe_float(row.get("open"),  0.0),
        "high":   safe_float(row.get("high"),  0.0),
        "low":    safe_float(row.get("low"),   0.0),
        "close":  safe_float(row.get("close"), 0.0),
        "volume": safe_int(row.get("volume"),  0),
    }


def normalize_option_row(row: dict, symbol: str) -> dict:
    """
    Normalize a raw chain CSV row to the live engine option row schema.

    CRITICAL: this schema must exactly match what strategy modules expect.
    Fields: expiration, dte, option_type, strike, bid, ask, mid,
            delta, gamma, theta, vega, iv, open_interest, volume
    """
    mid = safe_float(row.get("mid"))
    bid = safe_float(row.get("bid"), 0.0)
    ask = safe_float(row.get("ask"), 0.0)

    # Reconstruct mid from bid/ask if missing
    if mid is None and bid is not None and ask is not None:
        mid = round((bid + ask) / 2, 4)

    return {
        "date":          row.get("date", ""),
        "symbol":        symbol,
        "expiration":    row["expiration"],
        "dte":           safe_int(row.get("dte"), 0),
        "option_type":   str(row.get("option_type", "")).lower(),
        "strike":        safe_float(row.get("strike"), 0.0),
        "bid":           bid,
        "ask":           ask,
        "mid":           mid or 0.0,
        "delta":         safe_float(row.get("delta")),
        "gamma":         safe_float(row.get("gamma")),
        "theta":         safe_float(row.get("theta")),
        "vega":          safe_float(row.get("vega")),
        "iv":            safe_float(row.get("iv")),
        "open_interest": safe_int(row.get("open_interest"), 0),
        "volume":        safe_int(row.get("volume"), 0),
    }


def normalize_vol_row(row: dict, symbol: str) -> dict:
    """Normalize a raw volatility CSV row."""
    return {
        "date":          row["date"],
        "symbol":        symbol,
        "atr_14":        safe_float(row.get("atr_14")),
        "atr_prior":     safe_float(row.get("atr_prior")),
        "front_iv":      safe_float(row.get("front_iv")),
        "back_iv":       safe_float(row.get("back_iv")),
        "iv_percentile": safe_float(row.get("iv_percentile")),
        "iv_min":        safe_float(row.get("iv_min")),
        "iv_max":        safe_float(row.get("iv_max")),
        "put_25d_iv":    safe_float(row.get("put_25d_iv")),
        "call_25d_iv":   safe_float(row.get("call_25d_iv")),
    }


# ─────────────────────────────────────────────
# MAIN LOADERS
# ─────────────────────────────────────────────

def load_price_history(symbol: str, start: str, end: str) -> dict[str, dict]:
    """
    Load daily price history for a symbol.
    Returns dict[date_str, price_row].
    """
    path = BASE_DIR / "prices" / f"{symbol}_prices.csv"
    rows = load_csv(path)
    rows = filter_rows_by_date(rows, start, end)
    normalized = [normalize_price_row(r, symbol) for r in rows]
    return {r["date"]: r for r in normalized}


def load_option_chain_history(symbol: str, start: str, end: str) -> dict[str, list[dict]]:
    """
    Load daily option chain snapshots for a symbol.
    Returns dict[date_str, list[option_rows]].
    """
    path = BASE_DIR / "chains" / f"{symbol}_chains.csv"
    rows = load_csv(path)
    rows = filter_rows_by_date(rows, start, end)
    normalized = [normalize_option_row(r, symbol) for r in rows]
    return group_rows_by_date(normalized)


def load_volatility_history(symbol: str, start: str, end: str) -> dict[str, dict]:
    """
    Load daily volatility/IV snapshots for a symbol.
    Returns dict[date_str, vol_row].
    """
    path = BASE_DIR / "volatility" / f"{symbol}_volatility.csv"
    rows = load_csv(path)
    rows = filter_rows_by_date(rows, start, end)
    normalized = [normalize_vol_row(r, symbol) for r in rows]
    return {r["date"]: r for r in normalized}


def load_gex_history(symbol: str, start: str, end: str) -> dict[str, dict]:
    """
    Load pre-computed daily GEX context for a symbol.
    Returns empty dict if file doesn't exist (backtest reconstructs from chain).
    """
    path = BASE_DIR / "gamma" / f"{symbol}_gamma.csv"
    if not path.exists():
        return {}

    rows = load_csv(path)
    rows = filter_rows_by_date(rows, start, end)

    normalized = {}
    for row in rows:
        normalized[row["date"]] = {
            "date":       row["date"],
            "symbol":     symbol,
            "total_gex":  safe_float(row.get("total_gex")),
            "gamma_flip": safe_float(row.get("gamma_flip")),
            "gamma_trap": safe_float(row.get("gamma_trap")),
        }
    return normalized


# ─────────────────────────────────────────────
# SNAPSHOT MERGER
# ─────────────────────────────────────────────

def build_historical_market_snapshot(
    price_rows: dict[str, dict],
    vol_rows:   dict[str, dict],
    gex_rows:   dict[str, dict] | None = None,
    symbol:     str = "SPY",
    short_dte_target: int = 7,
    long_dte_target:  int = 60,
) -> dict[str, dict]:
    """
    Merge price, volatility, and optional GEX rows into a single
    historical market snapshot dict keyed by date.

    Output format matches the market dict expected by signal_builder
    and ultimately by the live strategy modules.
    """
    gex_rows = gex_rows or {}
    historical_market: dict[str, dict] = {}

    for date_str, price_row in price_rows.items():
        vol_row = vol_rows.get(date_str, {})
        gex_row = gex_rows.get(date_str, {})

        historical_market[date_str] = {
            "date":              date_str,
            "symbol":            symbol,
            "spot_price":        price_row.get("close", 0.0),

            # ATR inputs
            "atr_14":            vol_row.get("atr_14"),
            "atr_prior":         vol_row.get("atr_prior"),

            # IV inputs
            "front_iv":          vol_row.get("front_iv"),
            "back_iv":           vol_row.get("back_iv"),
            "iv_percentile":     vol_row.get("iv_percentile"),
            "iv_min":            vol_row.get("iv_min"),
            "iv_max":            vol_row.get("iv_max"),

            # Skew inputs
            "put_25d_iv":        vol_row.get("put_25d_iv"),
            "call_25d_iv":       vol_row.get("call_25d_iv"),

            # Pre-computed GEX (optional fallback)
            "total_gex":         gex_row.get("total_gex"),
            "gamma_flip":        gex_row.get("gamma_flip"),
            "gamma_trap":        gex_row.get("gamma_trap"),

            # Strategy parameters
            "short_dte_target":  short_dte_target,
            "long_dte_target":   long_dte_target,
            "preferred_risk_dollars": 500,
        }

    return historical_market

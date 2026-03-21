"""
adapters/chain_adapter.py
Normalizes raw option chain data from any source into the v15 engine schema.

Handles column alias resolution, option_type normalization, mid-price
computation, and liquidity filtering. The engine never sees raw broker
column names — only the normalized schema.
"""
from __future__ import annotations
from typing import Any, Iterable
import pandas as pd


# Column aliases — first match wins
CHAIN_ALIASES: dict[str, list[str]] = {
    "symbol":       ["symbol", "underlying", "ticker", "root"],
    "expiration":   ["expiration", "expiry", "exp_date", "expiration_date"],
    "dte":          ["dte", "days_to_expiry", "days_to_expiration", "days_remaining"],
    "option_type":  ["option_type", "type", "right", "cp", "call_put"],
    "strike":       ["strike", "strike_price", "strk"],
    "delta":        ["delta"],
    "gamma":        ["gamma"],
    "theta":        ["theta"],
    "vega":         ["vega"],
    "mid":          ["mid", "mark", "mid_price", "price"],
    "bid":          ["bid", "best_bid", "bid_price"],
    "ask":          ["ask", "best_ask", "ask_price"],
    "open_interest":["open_interest", "oi", "openInterest"],
    "volume":       ["volume", "vol"],
    "iv":           ["iv", "implied_vol", "implied_volatility", "mid_iv"],
}

OPT_TYPE_MAP = {
    "c": "call", "call": "call", "calls": "call",
    "p": "put",  "put": "put",  "puts": "put",
}


def _find(row: dict[str, Any], aliases: list[str], default: Any = None) -> Any:
    for key in aliases:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _sf(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _si(v: Any, default: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def normalize_chain_rows(
    rows: Iterable[dict[str, Any]],
    symbol_override: str | None = None,
) -> list[dict[str, Any]]:
    """
    Normalize raw chain rows to the v15 engine schema.
    Skips rows with invalid option_type or zero strike.
    Auto-computes mid from bid/ask when mid is missing.
    """
    out = []
    for row in rows:
        opt_type = OPT_TYPE_MAP.get(
            str(_find(row, CHAIN_ALIASES["option_type"], "")).strip().lower(), ""
        )
        if opt_type not in ("call", "put"):
            continue

        strike = _sf(_find(row, CHAIN_ALIASES["strike"]))
        if strike <= 0:
            continue

        expiration = str(_find(row, CHAIN_ALIASES["expiration"], "")).strip()
        if not expiration:
            continue

        bid = _sf(_find(row, CHAIN_ALIASES["bid"]))
        ask = _sf(_find(row, CHAIN_ALIASES["ask"]))
        mid = _sf(_find(row, CHAIN_ALIASES["mid"]))
        if mid <= 0 and bid > 0 and ask > 0:
            mid = round((bid + ask) / 2.0, 4)

        out.append({
            "symbol":        (symbol_override or str(_find(row, CHAIN_ALIASES["symbol"], ""))).upper(),
            "expiration":    expiration,
            "dte":           _si(_find(row, CHAIN_ALIASES["dte"])),
            "option_type":   opt_type,
            "strike":        strike,
            "bid":           bid,
            "ask":           ask,
            "mid":           mid,
            "delta":         _sf(_find(row, CHAIN_ALIASES["delta"])),
            "gamma":         _sf(_find(row, CHAIN_ALIASES["gamma"])),
            "theta":         _sf(_find(row, CHAIN_ALIASES["theta"])),
            "vega":          _sf(_find(row, CHAIN_ALIASES["vega"])),
            "iv":            _sf(_find(row, CHAIN_ALIASES["iv"])),
            "open_interest": _si(_find(row, CHAIN_ALIASES["open_interest"])),
            "volume":        _si(_find(row, CHAIN_ALIASES["volume"])),
        })
    return out


def normalize_chain_df(
    df: pd.DataFrame,
    symbol_override: str | None = None,
) -> list[dict[str, Any]]:
    """Convenience wrapper for DataFrames."""
    return normalize_chain_rows(df.to_dict(orient="records"), symbol_override=symbol_override)


def filter_chain(
    rows: list[dict[str, Any]],
    min_oi:                  int   = 1,
    max_bid_ask_spread_pct:  float = 0.35,
    min_mid:                 float = 0.01,
) -> list[dict[str, Any]]:
    """
    Liquidity filter — removes rows with thin markets.
    Applied after normalization.
    """
    out = []
    for r in rows:
        if r.get("open_interest", 0) < min_oi:
            continue
        mid = r.get("mid", 0)
        if mid < min_mid:
            continue
        if mid > 0:
            spread_pct = (r.get("ask", 0) - r.get("bid", 0)) / mid
            if spread_pct > max_bid_ask_spread_pct:
                continue
        out.append(r)
    return out

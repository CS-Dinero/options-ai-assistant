"""
adapters/positions_adapter.py
Maps raw broker position rows (from CSV, Tradier, IBKR, etc.) into
the format expected by position_manager/position_tracker.py.

Infers strategy type from leg structure:
  2 put legs, same expiration  → bull_put
  2 call legs, same expiration → bear_call
  same-strike same-type legs, different expirations → calendar
  different-strike call legs, different expirations → diagonal (call)
  different-strike put legs, different expirations  → diagonal (put)
"""
from __future__ import annotations
from typing import Any


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


def infer_strategy(legs: list[dict]) -> str:
    """Infer strategy_type from 2 legs."""
    if len(legs) != 2:
        return "unknown"

    a, b = legs
    a_type = str(a.get("option_type", "")).lower()
    b_type = str(b.get("option_type", "")).lower()
    a_exp  = str(a.get("expiration", ""))
    b_exp  = str(b.get("expiration", ""))
    a_k    = _sf(a.get("strike"))
    b_k    = _sf(b.get("strike"))
    a_qty  = _si(a.get("quantity"))
    b_qty  = _si(b.get("quantity"))

    same_exp     = a_exp == b_exp
    same_strike  = abs(a_k - b_k) < 0.01
    diff_exp     = not same_exp

    # Calendar: same strike, same type, different expirations
    if a_type == b_type and same_strike and diff_exp:
        return "calendar"

    # Diagonal: same type, different strike, different expirations
    if a_type == b_type and not same_strike and diff_exp:
        return f"diagonal"

    # Verticals: same expiration, same type, different strikes
    if same_exp and a_type == "put"  and not same_strike:
        return "bull_put"
    if same_exp and a_type == "call" and not same_strike:
        return "bear_call"

    return "unknown"


def normalize_position_legs(
    rows: list[dict[str, Any]],
    symbol_override: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize raw broker position rows to a standard leg schema."""
    out = []
    for r in rows:
        sym = symbol_override or str(r.get("symbol", "")).upper()
        qty = _si(r.get("quantity"))
        out.append({
            "symbol":      sym,
            "expiration":  str(r.get("expiration", "")).strip(),
            "option_type": str(r.get("option_type", "")).lower(),
            "strike":      _sf(r.get("strike")),
            "quantity":    qty,
            "dte":         _si(r.get("dte")),
            "avg_price":   _sf(r.get("avg_price", r.get("cost_basis"))),
            "mark":        _sf(r.get("mark", r.get("last"))),
            "side":        "long" if qty > 0 else "short",
        })
    return out


def legs_to_tracker_row(
    legs:          list[dict[str, Any]],
    spot:          float,
    expected_move: float,
    trade_id:      str | None = None,
) -> dict[str, Any] | None:
    """
    Convert 2 normalized legs into a position_tracker-compatible row.
    Returns None if strategy cannot be inferred.
    """
    if len(legs) != 2:
        return None

    strategy = infer_strategy(legs)
    if strategy == "unknown":
        return None

    short_legs = [l for l in legs if l["side"] == "short"]
    long_legs  = [l for l in legs if l["side"] == "long"]

    if not short_legs or not long_legs:
        return None

    short_leg = short_legs[0]
    long_leg  = long_legs[0]

    if strategy in ("bull_put", "bear_call"):
        entry_credit = max(_sf(short_leg["avg_price"]) - _sf(long_leg["avg_price"]), 0.0)
        entry_px     = entry_credit
        target_exit  = round(entry_credit * 0.50, 4)
        stop_val     = round(entry_credit * 2.0, 4)
    else:
        entry_debit  = max(_sf(long_leg["avg_price"]) - _sf(short_leg["avg_price"]), 0.0)
        entry_px     = entry_debit
        target_exit  = round(entry_debit * 1.20, 4)
        stop_val     = round(entry_debit * 0.75, 4)

    return {
        "trade_id":          trade_id or "",
        "symbol":            short_leg["symbol"],
        "strategy_type":     strategy,
        "direction":         strategy,
        "short_strike":      short_leg["strike"],
        "long_strike":       long_leg["strike"],
        "short_expiration":  short_leg["expiration"],
        "long_expiration":   long_leg["expiration"],
        "short_dte":         short_leg["dte"],
        "long_dte":          long_leg["dte"],
        "entry_debit_credit": entry_px,
        "entry_price":       entry_px,
        "target_exit_value": target_exit,
        "target_price":      target_exit,
        "stop_value":        stop_val,
        "stop_price":        stop_val,
        "spot_open":         spot,
        "expected_move":     expected_move,
        "date_close":        "",   # open position
    }


def broker_positions_to_tracker_rows(
    raw_rows:      list[dict[str, Any]],
    spot:          float,
    expected_move: float,
    symbol:        str | None = None,
) -> list[dict[str, Any]]:
    """
    Convert a list of raw broker position rows into tracker-compatible rows.
    Groups by strategy inference on pairs of legs.
    Handles both individual rows (one leg each) and pre-paired dicts.
    """
    legs     = normalize_position_legs(raw_rows, symbol_override=symbol)
    # Group by symbol for pairing
    by_sym: dict[str, list[dict]] = {}
    for leg in legs:
        by_sym.setdefault(leg["symbol"], []).append(leg)

    results = []
    for sym, sym_legs in by_sym.items():
        # Try to pair legs into 2-leg structures
        # Simple pairing: consecutive pairs
        for i in range(0, len(sym_legs) - 1, 2):
            pair = sym_legs[i:i+2]
            row  = legs_to_tracker_row(pair, spot, expected_move)
            if row:
                results.append(row)

    return results

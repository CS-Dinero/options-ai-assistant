"""
engines/deep_itm_calendar_engine.py
Scans option chains for cheap deep-ITM calendar entry opportunities.

scan_deep_itm_calendars(chain_bundle, symbol, spot, market_context)
→ ranked list of entry candidates

chain_bundle format:
  {"calls": [...chain rows...], "puts": [...chain rows...]}
  where each row has: symbol, option_type, expiry/expiration, strike,
                      dte, bid, ask, mid, delta, iv, oi, volume
"""
from __future__ import annotations

from typing import Any

from config.transition_config import ENTRY_RULES, get_symbol_rule


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _safe_mid(row: dict) -> float:
    mid = _sf(row.get("mid"))
    if mid > 0:
        return mid
    bid = _sf(row.get("bid"))
    ask = _sf(row.get("ask"))
    return round((bid + ask) / 2.0, 4) if bid > 0 and ask > 0 else 0.0


def _ba_pct(row: dict) -> float:
    mid = _safe_mid(row)
    if mid <= 0:
        return 1.0
    return (_sf(row.get("ask")) - _sf(row.get("bid"))) / mid


def _intrinsic(option_type: str, spot: float, strike: float) -> float:
    if option_type == "call":
        return max(0.0, spot - strike)
    return max(0.0, strike - spot)


def _extrinsic(mid: float, intrinsic: float) -> float:
    return max(0.0, mid - intrinsic)


def _expiry_key(row: dict) -> str:
    return str(row.get("expiry") or row.get("expiration", ""))


def _dte_val(row: dict) -> int:
    return int(_sf(row.get("dte"), 0))


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def _cheapness_score(long_extrinsic: float, long_mid: float, short_mid: float) -> float:
    """Higher = cheaper entry relative to intrinsic content."""
    if long_mid <= 0:
        return 0.0
    ext_ratio = long_extrinsic / long_mid
    score     = 100.0 - (ext_ratio * 100.0) + min(20.0, short_mid * 2.5)
    return max(0.0, min(100.0, round(score, 2)))


def _harvestability_score(short_delta_abs: float, short_mid: float) -> float:
    """Higher = short leg still has good harvest premium."""
    score = 0.0
    if 0.18 <= short_delta_abs <= 0.42:
        score += 60.0
    elif 0.10 <= short_delta_abs <= 0.50:
        score += 35.0
    score += min(40.0, short_mid * 8.0)
    return max(0.0, min(100.0, round(score, 2)))


def _liquidity_score(row: dict, max_ba_pct: float) -> float:
    ba = _ba_pct(row)
    if ba >= max_ba_pct * 2:
        return 0.0
    return max(0.0, round(100.0 * (1.0 - ba / max_ba_pct), 2))


def _entry_score(cheapness: float, harvestability: float, liquidity: float) -> float:
    return round(cheapness * 0.45 + harvestability * 0.35 + liquidity * 0.20, 2)


# ─────────────────────────────────────────────
# MAIN SCANNER
# ─────────────────────────────────────────────

def scan_deep_itm_calendars(
    chain_bundle:   dict[str, list[dict]],
    symbol:         str,
    spot:           float,
    market_context: dict | None = None,
) -> list[dict[str, Any]]:
    """
    Scan for deep-ITM calendar entry candidates.

    Returns list sorted best-first by entry_score.
    Each candidate has: symbol, structure_type, bias, long_leg, short_leg,
                        net_debit, long_intrinsic, long_extrinsic, short_premium,
                        cheapness_score, harvestability_score, liquidity_score,
                        entry_score, notes
    """
    market_context = market_context or {}
    sym_rule       = get_symbol_rule(symbol)
    max_ba_pct     = _sf(sym_rule.get("max_ba_pct", 0.10))
    results: list[dict] = []

    for opt_type in ("call", "put"):
        key      = "calls" if opt_type == "call" else "puts"
        contracts = [r for r in chain_bundle.get(key, [])
                     if str(r.get("option_type","")).lower() == opt_type]

        back_month  = [r for r in contracts
                       if ENTRY_RULES["long_dte_min"] <= _dte_val(r) <= ENTRY_RULES["long_dte_max"]]
        front_month = [r for r in contracts
                       if ENTRY_RULES["short_dte_min"] <= _dte_val(r) <= ENTRY_RULES["short_dte_max"]]

        for long_leg in back_month:
            long_delta = abs(_sf(long_leg.get("delta")))
            if long_delta < ENTRY_RULES["min_long_delta_abs"]:
                continue

            long_mid       = _safe_mid(long_leg)
            long_intrinsic = _intrinsic(opt_type, spot, _sf(long_leg.get("strike")))
            long_extrinsic = _extrinsic(long_mid, long_intrinsic)

            if long_mid <= 0:
                continue
            if long_extrinsic / long_mid > ENTRY_RULES["max_long_extrinsic_pct_of_premium"]:
                continue

            long_liq = _liquidity_score(long_leg, max_ba_pct)

            for short_leg in front_month:
                if _sf(short_leg.get("strike")) != _sf(long_leg.get("strike")):
                    continue

                expiry_gap = _dte_val(long_leg) - _dte_val(short_leg)
                if expiry_gap < ENTRY_RULES["min_expiry_gap_days"]:
                    continue

                short_mid = _safe_mid(short_leg)
                if short_mid <= 0:
                    continue

                short_liq = _liquidity_score(short_leg, max_ba_pct)
                liq_avg   = round((long_liq + short_liq) / 2.0, 2)

                cheapness    = _cheapness_score(long_extrinsic, long_mid, short_mid)
                harvestability = _harvestability_score(
                    abs(_sf(short_leg.get("delta"))), short_mid)
                entry_score  = _entry_score(cheapness, harvestability, liq_avg)

                results.append({
                    "symbol":              symbol,
                    "structure_type":      f"deep_itm_{opt_type}_calendar",
                    "bias":                "bullish_neutral" if opt_type == "call" else "bearish_neutral",
                    "long_leg":            long_leg,
                    "short_leg":           short_leg,
                    "net_debit":           round(long_mid - short_mid, 4),
                    "long_intrinsic":      round(long_intrinsic, 4),
                    "long_extrinsic":      round(long_extrinsic, 4),
                    "short_premium":       round(short_mid, 4),
                    "cheapness_score":     cheapness,
                    "harvestability_score": harvestability,
                    "liquidity_score":     liq_avg,
                    "entry_score":         entry_score,
                    "current_risk_basis":  round(long_mid - short_mid, 4),
                    "notes": [
                        f"Long delta={long_delta:.2f}",
                        f"Long extrinsic pct={long_extrinsic/long_mid:.1%}",
                        f"Expiry gap={expiry_gap}d",
                        f"Short mid=${short_mid:.2f}",
                    ],
                })

    return sorted(results, key=lambda x: x["entry_score"], reverse=True)

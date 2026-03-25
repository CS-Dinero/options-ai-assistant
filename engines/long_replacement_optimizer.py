"""
engines/long_replacement_optimizer.py
Searches candidate replacement long legs for rebuilt structures.

Default bias: KEEP the current long unless replacement is materially better.
Use search_replacement_longs() to get ranked candidates, then pass to
rebuild_decision_engine.compare_keep_vs_replace() for final decision.
"""
from __future__ import annotations
from typing import Any

def _sf(v: Any, d: float = 0.0) -> float:
    try: return float(v) if v not in (None,"","—") else d
    except: return d

def _safe_mid(c: dict) -> float:
    mid = _sf(c.get("mid"))
    if mid > 0: return mid
    b,a = _sf(c.get("bid")), _sf(c.get("ask"))
    return round((b+a)/2,4) if b>0 and a>0 else 0.0

def _ba_pct(c: dict) -> float:
    mid = _safe_mid(c)
    if mid <= 0: return 1.0
    return (_sf(c.get("ask")) - _sf(c.get("bid"))) / mid

def _intrinsic(opt_type: str, spot: float, strike: float) -> float:
    return max(0.0, spot-strike) if opt_type=="call" else max(0.0, strike-spot)

def _extrinsic_val(c: dict, spot: float) -> float:
    return max(0.0, _safe_mid(c) - _intrinsic(str(c.get("option_type","")).lower(), spot, _sf(c.get("strike"))))

def _liquidity_score(c: dict, max_ba: float) -> float:
    ba = _ba_pct(c)
    return max(0.0, round(100*(1-ba/max_ba), 2)) if max_ba > 0 else 0.0

def _delta_fit(da: float, mode: str) -> float:
    if mode == "DIAGONAL":
        if 0.70<=da<=0.90: return 100.0
        if 0.55<=da<=0.95: return 70.0
        return 25.0
    return 100.0  # credit spread — any long is fine

def _dte_fit(dte: int, mode: str) -> float:
    if mode == "DIAGONAL":
        if 35<=dte<=90: return 100.0
        if 28<=dte<=120: return 70.0
        return 20.0
    return 100.0

def _ext_efficiency(c: dict, spot: float) -> float:
    mid = _safe_mid(c)
    if mid <= 0: return 0.0
    ext = _extrinsic_val(c, spot)
    return round(max(0.0, min(100.0, 100-(ext/mid)*100)), 2)

def _replacement_long_score(c: dict, spot: float, max_ba: float, mode: str) -> float:
    da = abs(_sf(c.get("delta")))
    return round(
        0.35*_ext_efficiency(c, spot) +
        0.25*_liquidity_score(c, max_ba) +
        0.20*_delta_fit(da, mode) +
        0.20*_dte_fit(int(_sf(c.get("dte"))), mode), 2)

def search_replacement_longs(
    current_position: dict[str, Any],
    chain_bundle: dict[str, list[dict]],
    market_context: dict[str, Any],
    target_option_type: str,
    max_ba_pct: float,
    mode: str = "DIAGONAL",
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """
    Search for replacement long legs ranked by efficiency.
    Returns dicts with 'contract', 'replacement_long_score', 'rebuild_class'.
    """
    spot      = _sf(market_context.get("spot") or market_context.get("spot_price"))
    contracts = chain_bundle.get("calls",[]) if target_option_type=="call" else chain_bundle.get("puts",[])
    out = []
    for c in contracts:
        if str(c.get("option_type","")).lower() != target_option_type: continue
        mid = _safe_mid(c)
        if mid <= 0: continue
        if _ba_pct(c) > max_ba_pct: continue
        dte  = int(_sf(c.get("dte")))
        da   = abs(_sf(c.get("delta")))
        k    = _sf(c.get("strike"))
        if mode == "DIAGONAL":
            if not (30<=dte<=90): continue
            if not (0.55<=da<=0.95): continue
            if target_option_type=="call" and k > spot*1.03: continue
            if target_option_type=="put"  and k < spot*0.97: continue
        elif mode == "CREDIT_SPREAD":
            if dte <= 0: continue
        score = _replacement_long_score(c, spot, max_ba_pct, mode)
        out.append({"contract": c, "replacement_long_score": score, "rebuild_class": "REPLACE_LONG"})
    return sorted(out, key=lambda x: x["replacement_long_score"], reverse=True)[:top_n]

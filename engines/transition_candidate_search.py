"""
engines/transition_candidate_search.py
Pre-ranks transition candidates per family before sending to the
full scorer. Acts as a fast funnel — only the top-N per family
reach evaluate_skew_flip_transition().
"""
from __future__ import annotations

from typing import Any

from config.transition_config import get_symbol_rule
from engines.skew_flip_harvest_engine import (
    _sf, _safe_mid, _bid_ask_pct, _delta_abs, _dte_val,
    _filter_contracts, _liquidity_score_single,
    _transition_net_credit_same_long, _transition_net_credit_close_rebuild,
    _structure_score_for_short, _assignment_risk_score, _closest_long_by_width,
)


# ─────────────────────────────────────────────
# SEARCH-RANK HELPERS (lighter than full scorer)
# ─────────────────────────────────────────────

def _rk_credit(net_credit: float, min_credit: float) -> float:
    if min_credit <= 0: return 100.0
    if net_credit <= 0: return 0.0
    return max(0.0, min(100.0, (net_credit / min_credit) * 100.0))


def _rk_delta(da: float) -> float:
    if 0.18 <= da <= 0.42: return 100.0
    if 0.10 <= da <= 0.50: return 65.0
    return 35.0


def _rk_dte(dte: int) -> float:
    if 7 <= dte <= 21:   return 100.0
    if 5 <= dte <= 28:   return 60.0
    return 0.0


def _rk_harvest_preservation(current_mid: float, new_mid: float) -> float:
    if current_mid <= 0: return 0.0
    r = new_mid / current_mid
    if r >= 1.00: return 100.0
    if r >= 0.75: return 75.0
    if r >= 0.50: return 45.0
    return 10.0


def _search_rank(
    net_credit: float, min_credit: float,
    preservation: float, liq: float, delta: float, dte: float,
    skew_boost: float = 0.0,
) -> float:
    return round(
        0.30 * _rk_credit(net_credit, min_credit) +
        0.20 * preservation +
        0.20 * liq +
        0.15 * delta +
        0.15 * dte +
        skew_boost,
        2,
    )


# ─────────────────────────────────────────────
# FAMILY SEARCHES
# ─────────────────────────────────────────────

def _search_same_side(
    position: dict, chain_bundle: dict, spot: float,
    min_credit: float, max_ba_pct: float,
) -> list[dict]:
    current_short  = position.get("short_leg", {})
    current_long   = position.get("long_leg",  {})
    opt_type       = str(current_short.get("option_type","")).lower()
    key            = "puts" if opt_type == "put" else "calls"
    current_strike = _sf(current_short.get("strike"))
    cur_mid        = _safe_mid(current_short)

    eligible = _filter_contracts(chain_bundle.get(key,[]), opt_type, 7, 21, 0.18, 0.42, max_ba_pct)
    out = []
    for ns in eligible:
        k = _sf(ns.get("strike"))
        if opt_type == "put"  and k > current_strike: continue
        if opt_type == "call" and k < current_strike: continue
        credit  = _transition_net_credit_same_long(current_short, ns)
        new_mid = _safe_mid(ns)
        liq     = _liquidity_score_single(ns, max_ba_pct)
        score   = _search_rank(credit, min_credit,
                               _rk_harvest_preservation(cur_mid, new_mid),
                               liq, _rk_delta(_delta_abs(ns)), _rk_dte(_dte_val(ns)))
        out.append({
            "action": f"FLIP_TO_{opt_type.upper()}_DIAGONAL",
            "type": f"{opt_type}_diagonal",
            "long_leg": current_long, "short_leg": ns,
            "transition_net_credit": credit,
            "expected_next_cycle_credit": round(new_mid * 0.75, 4),
            "current_risk_basis": _sf(position.get("current_risk_basis", 5.0)),
            "structure_score": _structure_score_for_short(ns, spot),
            "assignment_risk_score": _assignment_risk_score(ns, spot),
            "liquidity_score": liq, "search_rank_score": score,
        })
    return out


def _search_opposite_side(
    position: dict, chain_bundle: dict, spot: float,
    skew_metrics: dict, min_credit: float, max_ba_pct: float,
) -> list[dict]:
    preferred     = skew_metrics.get("preferred_flip_side")
    current_short = position.get("short_leg", {})
    current_long  = position.get("long_leg",  {})
    current_type  = str(current_short.get("option_type","")).lower()
    target_type   = "call" if current_type == "put" else "put"

    if preferred is None or preferred.lower() != target_type:
        return []

    key      = "calls" if target_type == "call" else "puts"
    eligible = _filter_contracts(chain_bundle.get(key,[]), target_type, 7, 21, 0.18, 0.42, max_ba_pct)
    cur_mid  = _safe_mid(current_short)
    skew_boost = min(20.0, abs(_sf(skew_metrics.get("skew_edge",0))) * 200.0)
    out = []
    for ns in eligible:
        k = _sf(ns.get("strike"))
        if target_type == "call" and k <= spot: continue
        if target_type == "put"  and k >= spot: continue
        credit  = _transition_net_credit_same_long(current_short, ns)
        new_mid = _safe_mid(ns)
        liq     = _liquidity_score_single(ns, max_ba_pct)
        score   = _search_rank(credit, min_credit,
                               _rk_harvest_preservation(cur_mid, new_mid),
                               liq, _rk_delta(_delta_abs(ns)), _rk_dte(_dte_val(ns)),
                               skew_boost=skew_boost)
        out.append({
            "action": f"FLIP_TO_{target_type.upper()}_DIAGONAL",
            "type": f"{target_type}_diagonal",
            "long_leg": current_long, "short_leg": ns,
            "transition_net_credit": credit,
            "expected_next_cycle_credit": round(new_mid * 0.75, 4),
            "current_risk_basis": _sf(position.get("current_risk_basis", 5.0)),
            "structure_score": _structure_score_for_short(ns, spot),
            "assignment_risk_score": _assignment_risk_score(ns, spot),
            "liquidity_score": liq, "search_rank_score": score,
        })
    return out


def _search_credit_spreads(
    position: dict, chain_bundle: dict, spot: float,
    min_credit: float, max_ba_pct: float,
) -> list[dict]:
    current_short = position.get("short_leg", {})
    current_long  = position.get("long_leg",  {})
    current_type  = str(current_short.get("option_type","")).lower()
    key           = "puts" if current_type == "put" else "calls"
    action        = "CONVERT_TO_BULL_PUT_SPREAD" if current_type == "put" else "CONVERT_TO_BEAR_CALL_SPREAD"
    direction     = "below" if current_type == "put" else "above"
    cur_mid       = _safe_mid(current_short)
    out = []

    eligible = _filter_contracts(chain_bundle.get(key,[]), current_type, 7, 21, 0.18, 0.35, max_ba_pct)
    for ns in eligible:
        k       = _sf(ns.get("strike"))
        new_lng = _closest_long_by_width(chain_bundle.get(key,[]), current_type, k, 5.0, direction, max_ba_pct)
        if new_lng is None: continue
        credit  = _transition_net_credit_close_rebuild(current_long, current_short, new_lng, ns)
        new_mid = _safe_mid(ns)
        liq_s   = _liquidity_score_single(ns, max_ba_pct)
        liq_l   = _liquidity_score_single(new_lng, max_ba_pct)
        liq     = round((liq_s + liq_l) / 2.0, 2)
        score   = _search_rank(credit, min_credit,
                               _rk_harvest_preservation(cur_mid, new_mid),
                               liq, _rk_delta(_delta_abs(ns)), _rk_dte(_dte_val(ns)))
        width   = abs(k - _sf(new_lng.get("strike")))
        out.append({
            "action": action, "type": action.replace("CONVERT_TO_","").lower(),
            "long_leg": new_lng, "short_leg": ns,
            "transition_net_credit": credit,
            "expected_next_cycle_credit": round(new_mid * 0.60, 4),
            "current_risk_basis": width,
            "structure_score": _structure_score_for_short(ns, spot),
            "assignment_risk_score": _assignment_risk_score(ns, spot),
            "liquidity_score": liq, "search_rank_score": score,
        })
    return out


# ─────────────────────────────────────────────
# MAIN RANKER
# ─────────────────────────────────────────────

def rank_transition_candidates(
    position:    dict[str, Any],
    chain_bundle: dict[str, list[dict]],
    market_context: dict[str, Any],
    skew_metrics: dict[str, Any],
    top_n_per_family: int = 5,
) -> dict[str, list[dict]]:
    """
    Return top-N candidates per family, pre-ranked by search_rank_score.
    These are then sent to the full transition scorer.
    """
    sym_rule   = get_symbol_rule(position.get("symbol",""))
    min_credit = _sf(sym_rule.get("min_flip_credit", 1.0))
    max_ba_pct = _sf(sym_rule.get("max_ba_pct", 0.12))
    spot       = _sf(market_context.get("spot") or market_context.get("spot_price"))

    same   = sorted(_search_same_side(position, chain_bundle, spot, min_credit, max_ba_pct),
                    key=lambda x: x["search_rank_score"], reverse=True)[:top_n_per_family]
    opp    = sorted(_search_opposite_side(position, chain_bundle, spot, skew_metrics, min_credit, max_ba_pct),
                    key=lambda x: x["search_rank_score"], reverse=True)[:top_n_per_family]
    credit = sorted(_search_credit_spreads(position, chain_bundle, spot, min_credit, max_ba_pct),
                    key=lambda x: x["search_rank_score"], reverse=True)[:top_n_per_family]

    return {"same_side_diagonal": same, "opposite_side_diagonal": opp, "credit_spread_conversion": credit}

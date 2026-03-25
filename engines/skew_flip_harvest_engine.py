"""
engines/skew_flip_harvest_engine.py
Skew-driven net-credit structure-transition engine.

Main entry point:
    result = evaluate_skew_flip_transition(
        current_position, chain_bundle, spot, market_context)

Sits between harvest_engine.py (same-structure rolls) and flip_optimizer.py
(directional sentiment flips). Specifically handles calendar → diagonal/spread
transitions that pay net credit AND preserve future rollability.

Architecture:
  1. Compute skew richness on both sides
  2. Search live chain for candidates (via transition_candidate_search)
  3. Gate by net credit (conservative fills)
  4. Gate by future rollability
  5. Score compositely
  6. Return best approved candidate or HOLD

All candidate generation uses conservative fill assumptions:
  close longs near bid, close shorts near ask
  open new shorts near bid, open new longs near ask
"""
from __future__ import annotations

from typing import Any

from config.transition_config import (
    SYMBOL_RULES, TRANSITION_RULES, get_symbol_rule,
)
from engines.future_rollability_engine import evaluate_future_rollability
from engines.structure_transition_scorer import score_transition


# ─────────────────────────────────────────────
# SHARED HELPERS (also imported by candidate search)
# ─────────────────────────────────────────────

def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _safe_mid(row: dict) -> float:
    mid = _sf(row.get("mid"))
    if mid > 0: return mid
    bid = _sf(row.get("bid")); ask = _sf(row.get("ask"))
    return round((bid + ask) / 2.0, 4) if bid > 0 and ask > 0 else 0.0


def _bid_ask_pct(row: dict) -> float:
    mid = _safe_mid(row)
    if mid <= 0: return 1.0
    return (_sf(row.get("ask")) - _sf(row.get("bid"))) / mid


def _delta_abs(row: dict) -> float:
    return abs(_sf(row.get("delta")))


def _expiry_key(row: dict) -> str:
    return str(row.get("expiry") or row.get("expiration", ""))


def _dte_val(row: dict) -> int:
    return int(_sf(row.get("dte"), 0))


def _is_liquid(row: dict, max_ba_pct: float, min_oi: int = 25) -> bool:
    return (
        _safe_mid(row) > 0 and
        _bid_ask_pct(row) <= max_ba_pct and
        int(_sf(row.get("open_interest") or row.get("oi") or row.get("volume") or 0)) >= min_oi
    )


def _filter_contracts(
    contracts: list[dict],
    option_type: str,
    dte_min: int,
    dte_max: int,
    delta_low: float,
    delta_high: float,
    max_ba_pct: float,
    min_oi: int = 25,
) -> list[dict]:
    out = []
    for c in contracts:
        if str(c.get("option_type","")).lower() != option_type:
            continue
        dte = _dte_val(c)
        if not (dte_min <= dte <= dte_max):
            continue
        da = _delta_abs(c)
        if da > 0 and not (delta_low <= da <= delta_high):
            continue
        if not _is_liquid(c, max_ba_pct, min_oi):
            continue
        out.append(c)
    return out


# Conservative fill assumptions
def _close_long_value(leg: dict) -> float:
    """Sell existing long near bid."""
    return _sf(leg.get("bid")) or _safe_mid(leg) * 0.95


def _close_short_cost(leg: dict) -> float:
    """Buy back existing short near ask."""
    return _sf(leg.get("ask")) or _safe_mid(leg) * 1.05


def _open_short_credit(leg: dict) -> float:
    """Sell new short near bid (conservative)."""
    return _sf(leg.get("bid")) or _safe_mid(leg) * 0.95


def _open_long_cost(leg: dict) -> float:
    """Buy new long near ask."""
    return _sf(leg.get("ask")) or _safe_mid(leg) * 1.05


def _transition_net_credit_same_long(current_short: dict, new_short: dict) -> float:
    """Roll short leg only — keep long as-is. Conservative fills."""
    return round(_open_short_credit(new_short) - _close_short_cost(current_short), 4)


def _transition_net_credit_close_rebuild(
    current_long: dict, current_short: dict,
    new_long: dict | None, new_short: dict,
) -> float:
    """Close both legs, open new structure. Conservative fills."""
    credit = _close_long_value(current_long) - _close_short_cost(current_short)
    cost   = (_open_long_cost(new_long) if new_long else 0.0)
    return round(credit + _open_short_credit(new_short) - cost, 4)


def _structure_score_for_short(short_leg: dict, spot: float) -> float:
    da  = _delta_abs(short_leg)
    dte = _dte_val(short_leg)
    ba  = _bid_ask_pct(short_leg)
    mid = _safe_mid(short_leg)
    s   = 0.0
    if 0.18 <= da  <= 0.42: s += 35.0
    elif 0.10 <= da <= 0.50: s += 20.0
    if 7 <= dte <= 21:       s += 25.0
    elif 5 <= dte <= 28:     s += 15.0
    if mid >= 0.75:          s += 20.0
    elif mid >= 0.40:        s += 10.0
    if ba <= 0.08:           s += 20.0
    elif ba <= 0.12:         s += 10.0
    return round(min(100.0, s), 2)


def _assignment_risk_score(short_leg: dict, spot: float) -> float:
    opt  = str(short_leg.get("option_type","")).lower()
    k    = _sf(short_leg.get("strike"))
    dte  = _dte_val(short_leg)
    itm  = max(0.0, (spot - k) / spot) if opt == "call" and spot > 0 else \
           max(0.0, (k - spot) / k)    if opt == "put"  and k    > 0 else 0.0
    s    = 20.0
    if itm > 0.01: s += 20.0
    if itm > 0.03: s += 25.0
    if dte <= 7:   s += 20.0
    if dte <= 3:   s += 15.0
    return round(min(100.0, s), 2)


def _liquidity_score_single(row: dict, max_ba_pct: float) -> float:
    ba = _bid_ask_pct(row)
    return max(0.0, round(100.0 * (1.0 - ba / max_ba_pct), 2))


def _closest_long_by_width(
    contracts: list[dict],
    option_type: str,
    short_strike: float,
    desired_width: float,
    direction: str,    # "below" or "above"
    max_ba_pct: float,
) -> dict | None:
    best, best_diff = None, 1e9
    for c in contracts:
        if str(c.get("option_type","")).lower() != option_type: continue
        if not _is_liquid(c, max_ba_pct, min_oi=10):            continue
        k     = _sf(c.get("strike"))
        valid = (k < short_strike) if direction == "below" else (k > short_strike)
        if not valid: continue
        diff  = abs(abs(short_strike - k) - desired_width)
        if diff < best_diff:
            best, best_diff = c, diff
    return best


# ─────────────────────────────────────────────
# SKEW COMPUTATION
# ─────────────────────────────────────────────

def compute_side_skew_metrics(
    chain_bundle: dict[str, list[dict]],
    spot: float,
    market_ctx:  dict | None = None,
) -> dict[str, Any]:
    """
    Measure relative richness of put vs call side.
    Uses 25-delta IV spread when available, falls back to
    chain_bundle richness flags or market_ctx skew fields.
    """
    # Try market_ctx first (most reliable when Massive is live)
    ctx = market_ctx or {}
    put_iv  = _sf(ctx.get("put_25d_iv") or ctx.get("put_iv"))
    call_iv = _sf(ctx.get("call_25d_iv") or ctx.get("call_iv"))

    if put_iv > 0 and call_iv > 0:
        put_richness  = put_iv
        call_richness = call_iv
    else:
        # Fall back to chain_bundle richness flags
        put_richness  = _sf(chain_bundle.get("put_side_richness",  0.0))
        call_richness = _sf(chain_bundle.get("call_side_richness", 0.0))

        # Last resort: compute from chain if available
        if put_richness == 0 and call_richness == 0:
            puts  = [r for r in chain_bundle.get("puts",[])
                     if 0.20 <= _delta_abs(r) <= 0.30 and _safe_mid(r) > 0]
            calls = [r for r in chain_bundle.get("calls",[])
                     if 0.20 <= _delta_abs(r) <= 0.30 and _safe_mid(r) > 0]
            if puts:  put_richness  = sum(_sf(r.get("iv")) for r in puts) / len(puts)
            if calls: call_richness = sum(_sf(r.get("iv")) for r in calls) / len(calls)

    skew_edge = round(call_richness - put_richness, 4)
    preferred = None
    if skew_edge > 0.02:  preferred = "CALL"
    elif skew_edge < -0.02: preferred = "PUT"

    skew_score = min(100.0, abs(skew_edge) * 500.0)

    return {
        "put_side_richness":  round(put_richness, 4),
        "call_side_richness": round(call_richness, 4),
        "skew_edge":          skew_edge,
        "preferred_flip_side": preferred,
        "skew_score":         round(skew_score, 2),
    }


# ─────────────────────────────────────────────
# CANDIDATE BUILDERS
# ─────────────────────────────────────────────

def _build_same_side_diagonals(
    position: dict, chain_bundle: dict, spot: float, max_ba_pct: float,
) -> list[dict]:
    current_short = position.get("short_leg", {})
    current_long  = position.get("long_leg",  {})
    opt_type      = str(current_short.get("option_type","")).lower()
    key           = "puts" if opt_type == "put" else "calls"
    current_strike = _sf(current_short.get("strike"))

    eligible = _filter_contracts(chain_bundle.get(key,[]), opt_type, 7, 21, 0.18, 0.42, max_ba_pct)
    out = []
    for ns in eligible:
        k = _sf(ns.get("strike"))
        if opt_type == "put"  and k > current_strike: continue
        if opt_type == "call" and k < current_strike: continue
        credit = _transition_net_credit_same_long(current_short, ns)
        liq    = _liquidity_score_single(ns, max_ba_pct)
        out.append({
            "action":                     f"FLIP_TO_{opt_type.upper()}_DIAGONAL",
            "type":                       f"{opt_type}_diagonal",
            "long_leg":                   current_long,
            "short_leg":                  ns,
            "transition_net_credit":      credit,
            "expected_next_cycle_credit": round(_safe_mid(ns) * 0.75, 4),
            "current_risk_basis":         _sf(position.get("current_risk_basis", 5.0)),
            "structure_score":            _structure_score_for_short(ns, spot),
            "assignment_risk_score":      _assignment_risk_score(ns, spot),
            "liquidity_score":            liq,
        })
    return out


def _build_opposite_side_diagonals(
    position: dict, chain_bundle: dict, spot: float,
    skew_metrics: dict, max_ba_pct: float,
) -> list[dict]:
    preferred = skew_metrics.get("preferred_flip_side")
    current_short = position.get("short_leg", {})
    current_long  = position.get("long_leg",  {})
    current_type  = str(current_short.get("option_type","")).lower()
    target_type   = "call" if current_type == "put" else "put"

    if preferred is None or preferred.lower() != target_type:
        return []

    key      = "calls" if target_type == "call" else "puts"
    eligible = _filter_contracts(chain_bundle.get(key,[]), target_type, 7, 21, 0.18, 0.42, max_ba_pct)
    out = []
    for ns in eligible:
        k = _sf(ns.get("strike"))
        if target_type == "call" and k <= spot: continue
        if target_type == "put"  and k >= spot: continue
        credit = _transition_net_credit_same_long(current_short, ns)
        liq    = _liquidity_score_single(ns, max_ba_pct)
        out.append({
            "action":                     f"FLIP_TO_{target_type.upper()}_DIAGONAL",
            "type":                       f"{target_type}_diagonal",
            "long_leg":                   current_long,
            "short_leg":                  ns,
            "transition_net_credit":      credit,
            "expected_next_cycle_credit": round(_safe_mid(ns) * 0.75, 4),
            "current_risk_basis":         _sf(position.get("current_risk_basis", 5.0)),
            "structure_score":            _structure_score_for_short(ns, spot),
            "assignment_risk_score":      _assignment_risk_score(ns, spot),
            "liquidity_score":            liq,
        })
    return out


def _build_credit_spread_conversions(
    position: dict, chain_bundle: dict, spot: float, max_ba_pct: float,
) -> list[dict]:
    current_short = position.get("short_leg", {})
    current_long  = position.get("long_leg",  {})
    current_type  = str(current_short.get("option_type","")).lower()
    key           = "puts" if current_type == "put" else "calls"
    action        = "CONVERT_TO_BULL_PUT_SPREAD" if current_type == "put" else "CONVERT_TO_BEAR_CALL_SPREAD"
    direction     = "below" if current_type == "put" else "above"

    eligible = _filter_contracts(chain_bundle.get(key,[]), current_type, 7, 21, 0.18, 0.35, max_ba_pct)
    out = []
    for ns in eligible:
        k        = _sf(ns.get("strike"))
        new_long = _closest_long_by_width(
            chain_bundle.get(key,[]), current_type, k, 5.0, direction, max_ba_pct)
        if new_long is None: continue
        credit = _transition_net_credit_close_rebuild(current_long, current_short, new_long, ns)
        liq_s  = _liquidity_score_single(ns, max_ba_pct)
        liq_l  = _liquidity_score_single(new_long, max_ba_pct)
        liq    = round((liq_s + liq_l) / 2.0, 2)
        width  = abs(k - _sf(new_long.get("strike")))
        out.append({
            "action":                     action,
            "type":                       action.replace("CONVERT_TO_","").lower().replace("_"," ").strip(),
            "long_leg":                   new_long,
            "short_leg":                  ns,
            "transition_net_credit":      credit,
            "expected_next_cycle_credit": round(_safe_mid(ns) * 0.60, 4),
            "current_risk_basis":         width,
            "structure_score":            _structure_score_for_short(ns, spot),
            "assignment_risk_score":      _assignment_risk_score(ns, spot),
            "liquidity_score":            liq,
        })
    return out


# ─────────────────────────────────────────────
# REGIME GATE
# ─────────────────────────────────────────────

def _regime_allows(action: str, market_ctx: dict) -> bool:
    vga   = str(market_ctx.get("vga_environment","")).lower()
    gamma = str(market_ctx.get("gamma_regime","")).lower()
    if "DIAGONAL" in action:
        return "negative" in gamma or "trend" in gamma or "trend" in vga
    return True   # credit spreads always allowed


# ─────────────────────────────────────────────
# MAIN ENGINE
# ─────────────────────────────────────────────

def evaluate_skew_flip_transition(
    current_position: dict[str, Any],
    chain_bundle:     dict[str, list[dict]],
    spot:             float,
    market_context:   dict[str, Any],
    symbol_rules:     dict | None = None,
    transition_rules: dict | None = None,
) -> dict[str, Any]:
    """
    Evaluate all possible net-credit transitions from a deep ITM calendar/diagonal.

    Returns:
      approved              — bool
      recommended_action    — action label
      transition_net_credit — conservative net credit per share
      future_roll_score     — harvestability of new short
      composite_score       — overall quality
      new_structure         — {type, long_leg, short_leg}
      why                   — list of reason strings
      rejected_candidates   — audit trail
      side_edge             — preferred skew side or None
    """
    symbol_rules     = symbol_rules or SYMBOL_RULES
    transition_rules = transition_rules or TRANSITION_RULES
    sym_rule         = get_symbol_rule(current_position.get("symbol",""))
    max_ba_pct       = _sf(sym_rule.get("max_ba_pct", 0.12))
    min_credit       = _sf(sym_rule.get("min_flip_credit", 1.0))

    ctx = {**market_context, "spot": spot}
    skew_metrics = compute_side_skew_metrics(chain_bundle, spot, ctx)

    # Build candidates from all three families
    candidates: list[dict] = []
    candidates.extend(_build_same_side_diagonals(current_position, chain_bundle, spot, max_ba_pct))
    candidates.extend(_build_opposite_side_diagonals(current_position, chain_bundle, spot, skew_metrics, max_ba_pct))
    candidates.extend(_build_credit_spread_conversions(current_position, chain_bundle, spot, max_ba_pct))
    candidates.append({   # always include HOLD
        "action": "HOLD_CURRENT_HARVEST",
        "type":   current_position.get("structure_type","calendar"),
        "long_leg": current_position.get("long_leg",{}),
        "short_leg": current_position.get("short_leg",{}),
        "transition_net_credit": 0.0, "expected_next_cycle_credit": 0.0,
        "current_risk_basis": _sf(current_position.get("current_risk_basis",5.0)),
        "structure_score": 60.0, "assignment_risk_score": 25.0, "liquidity_score": 90.0,
    })

    approved_list: list[dict] = []
    rejected_list: list[dict] = []

    for cand in candidates:
        action = cand.get("action","")

        # Net credit gate
        if action != "HOLD_CURRENT_HARVEST" and transition_rules.get("require_net_credit_for_flip"):
            if cand["transition_net_credit"] < min_credit:
                rejected_list.append({"action": action,
                                       "reason": f"Credit ${cand['transition_net_credit']:.2f} < min ${min_credit:.2f}"})
                continue

        # Regime gate (diagonals only in trend/negative gamma)
        if not _regime_allows(action, ctx):
            rejected_list.append({"action": action, "reason": "Regime gate blocked (neutral/positive gamma)"})
            continue

        # Rollability
        rollability = evaluate_future_rollability(cand, chain_bundle, ctx)

        # Score
        scored = score_transition(
            current_position=current_position,
            candidate_structure=cand,
            skew_metrics=skew_metrics,
            rollability=rollability,
            liquidity={"liquidity_score": cand.get("liquidity_score", 70.0)},
            rules=sym_rule,
        )
        merged = {**cand, **rollability, **scored}

        if merged.get("approved") or action == "HOLD_CURRENT_HARVEST":
            approved_list.append(merged)
        else:
            rejected_list.append({"action": action,
                                   "reason": "Failed composite gates",
                                   "composite_score": merged.get("composite_score",0)})

    if not approved_list:
        return {
            "approved": False,
            "recommended_action": "HOLD_CURRENT_HARVEST",
            "transition_net_credit": 0.0,
            "future_roll_score": 0.0,
            "composite_score": 0.0,
            "new_structure": None,
            "why": ["No transition cleared all gates"],
            "rejected_candidates": rejected_list,
            "side_edge": skew_metrics.get("preferred_flip_side"),
            "transition_summary": "HOLD — no creditworthy transition found",
        }

    best = max(approved_list, key=lambda x: x.get("composite_score", 0))

    why = [
        f"Skew edge: {skew_metrics.get('preferred_flip_side','neutral')} side richer "
        f"(skew score {skew_metrics.get('skew_score',0):.0f})",
        f"Conservative net credit ${best['transition_net_credit']:.2f} clears ${min_credit:.2f} minimum",
        f"Future roll score {best.get('future_roll_score',0):.1f}/100",
        "New short harvestable next cycle" if best.get("harvestable_next_cycle") else "Next cycle is marginal",
    ]

    is_real = best.get("action","") != "HOLD_CURRENT_HARVEST"

    return {
        "approved": is_real,
        "recommended_action": best["action"],
        "transition_net_credit": round(best.get("transition_net_credit",0.0), 4),
        "future_roll_score": round(best.get("future_roll_score",0.0), 2),
        "composite_score": round(best.get("composite_score",0.0), 2),
        "new_structure": {
            "type":      best.get("type",""),
            "long_leg":  best.get("long_leg"),
            "short_leg": best.get("short_leg"),
        },
        "why": why,
        "rejected_candidates": rejected_list,
        "all_scored": approved_list,
        "side_edge": skew_metrics.get("preferred_flip_side"),
        "transition_summary": (
            f"{best['action']} | credit ${best['transition_net_credit']:.2f} "
            f"| roll score {best.get('future_roll_score',0):.1f}"
        ),
    }

"""
engines/empirical_weight_adjuster.py
Bounded empirical bias adjuster. Uses journal outcomes to nudge
symbol-action, rebuild, and width preferences.

Biases are capped at ±8 points so hard gates are never overridden.
Gates remain hard. Biases only affect ranking among already-valid candidates.
"""
from __future__ import annotations
from typing import Any
from collections import defaultdict

MAX_BIAS = 8.0
BASELINE_SCORE = 65.0

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_empirical_adjustments(evaluated_journals: list[dict[str,Any]]) -> dict[str,Any]:
    action_s  = defaultdict(list)
    rebuild_s = defaultdict(list)
    width_s   = defaultdict(list)

    for item in evaluated_journals:
        sym    = item.get("symbol","")
        action = item.get("approved_action","")
        rebuild= item.get("approved_rebuild_class","")
        score  = _sf(item.get("outcome_score"))
        width  = item.get("approved_target_width")
        if sym and action: action_s[(sym,action)].append(score)
        if sym and rebuild: rebuild_s[(sym,rebuild)].append(score)
        if sym and width is not None: width_s[(sym,float(width))].append(score)

    def _bias(vals):
        avg = sum(vals)/len(vals) if vals else BASELINE_SCORE
        return max(-MAX_BIAS, min(MAX_BIAS, (avg-BASELINE_SCORE)/3.0))

    sym_action  = defaultdict(dict)
    rebuild_b   = defaultdict(dict)
    width_b     = defaultdict(dict)

    for (sym,act), vals in action_s.items():
        sym_action[sym][act] = round(_bias(vals),2)
    for (sym,rb), vals in rebuild_s.items():
        rebuild_b[sym][rb] = round(_bias(vals),2)
    for (sym,w), vals in width_s.items():
        width_b[sym][w] = round(_bias(vals),2)

    return {
        "symbol_action_bias": dict(sym_action),
        "rebuild_bias":       dict(rebuild_b),
        "width_bias":         dict(width_b),
    }

def apply_empirical_bias(candidate: dict[str,Any], symbol: str, adjustments: dict[str,Any]) -> dict[str,Any]:
    """Apply empirical bias to composite_score. Gates remain unchanged."""
    if not adjustments: return candidate
    adjusted = dict(candidate)
    action   = candidate.get("action","")
    rebuild  = candidate.get("rebuild_class","")
    width    = candidate.get("target_width")
    score    = _sf(candidate.get("composite_score"))

    ab = _sf(adjustments.get("symbol_action_bias",{}).get(symbol,{}).get(action))
    rb = _sf(adjustments.get("rebuild_bias",{}).get(symbol,{}).get(rebuild))
    wb = _sf(adjustments.get("width_bias",{}).get(symbol,{}).get(float(width) if width else None))

    total_bias = round(ab+rb+wb, 2)
    adjusted["composite_score_pre_bias"] = score
    adjusted["empirical_bias_total"]     = total_bias
    adjusted["composite_score"]          = round(score + total_bias, 2)
    return adjusted

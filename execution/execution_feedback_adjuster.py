"""execution/execution_feedback_adjuster.py — Bounded execution bias from slippage history."""
from __future__ import annotations
from typing import Any

MIN_COUNT = 5  # minimum observations before any bias

def build_execution_adjustments(slippage_model: dict[str,Any]) -> dict[str,Any]:
    def _bias(stats, max_pos, max_neg, multiplier):
        if stats.get("count",0) < MIN_COUNT: return 0.0
        return max(max_neg, min(max_pos, stats["avg_slippage_dollars"]*multiplier))

    sym_b={}; win_b={}; pol_b={}; act_b={}; rb_b={}
    for sym,s in slippage_model.get("by_symbol",{}).items():
        sym_b[sym]=round(_bias(s,4,-8,4.0),2)
    for w,s in slippage_model.get("by_window",{}).items():
        win_b[w]=round(_bias(s,4,-6,5.0),2)
    for p,s in slippage_model.get("by_policy",{}).items():
        pol_b[p]=round(_bias(s,4,-6,5.0),2)
    for a,s in slippage_model.get("by_action",{}).items():
        act_b[a]=round(_bias(s,4,-6,4.0),2)
    for r,s in slippage_model.get("by_rebuild",{}).items():
        rb_b[r]=round(_bias(s,3,-5,4.0),2)
    return {"symbol_execution_bias":sym_b,"window_execution_bias":win_b,
            "policy_execution_bias":pol_b,"action_execution_bias":act_b,
            "rebuild_execution_bias":rb_b}

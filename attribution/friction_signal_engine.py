"""attribution/friction_signal_engine.py — Measures cost, delay, churn, and burden."""
from __future__ import annotations
from typing import Any

def compute_friction_signals(row: dict[str,Any]) -> dict[str,Any]:
    hc=int(row.get("handoff_count",0)); rc=int(row.get("review_count",0))
    ov=int(row.get("decision_override_count",0))
    dl=1 if row.get("transition_execution_policy")=="DELAY" else 0
    bl=1 if (row.get("transition_execution_surface_ok") is False or
             row.get("transition_timing_ok") is False or
             row.get("transition_portfolio_fit_ok") is False or
             row.get("capital_commitment_ok") is False) else 0
    pc=int(row.get("policy_change_touch_count",0))
    fs=round(10*hc+8*rc+10*ov+15*dl+20*bl+6*pc,2)
    return {"handoff_count":hc,"review_count":rc,"decision_override_count":ov,
            "delay_flag":dl,"blocked_flag":bl,"policy_churn":pc,"friction_score":fs}

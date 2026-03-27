"""command/command_summary_engine.py — Builds the one-page executive summary."""
from __future__ import annotations
from typing import Any

def build_command_summary(executive_state: dict[str,Any], priority_stack: list[dict[str,Any]],
                           kpis: dict[str,Any]) -> dict[str,Any]:
    top_issue=priority_stack[0]["title"] if priority_stack else "No major issues"
    q=executive_state.get("queue",[]); top_opp=q[0].get("symbol") if q else "No active queue leader"
    causal=executive_state.get("causal_summary",{}); learning=causal.get("headline","No major causal insight yet.")
    return {"headline":f"{executive_state.get('environment')} | {executive_state.get('active_mandate')} | {executive_state.get('active_risk_envelope')}",
            "top_issue":top_issue,"top_opportunity":top_opp,"important_learning":learning,"kpis":kpis}

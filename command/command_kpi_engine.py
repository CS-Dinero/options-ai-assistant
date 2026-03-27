"""command/command_kpi_engine.py — Computes top-level operating KPIs."""
from __future__ import annotations
from typing import Any

def build_command_kpis(executive_state: dict[str,Any]) -> dict[str,Any]:
    q=executive_state.get("queue",[]); al=executive_state.get("alerts",[])
    rv=executive_state.get("reviews",[]); rl=executive_state.get("releases",[])
    cb=executive_state.get("capital_budget",{}); mat=executive_state.get("maturity_results",{})
    order={"PROTOTYPE":0,"USABLE":1,"STABLE":2,"GOVERNED":3,"SCALABLE":4}
    levels={k:v.get("level") for k,v in mat.items()} if isinstance(mat,dict) else {}
    weakest=min(levels,key=lambda k:order.get(levels[k],0)) if levels else None
    return {"queue_depth":len(q),
            "ready_now_count":sum(1 for x in q if x.get("transition_execution_policy")=="FULL_NOW"),
            "critical_alert_count":sum(1 for a in al if a.get("severity")=="CRITICAL"),
            "urgent_review_count":sum(1 for r in rv if r.get("priority") in ("P0","P1")),
            "active_release_count":sum(1 for r in rl if r.get("state") not in ("COMPLETED","CANCELLED")),
            "deployable_capital":cb.get("deployable_capital",0.0),
            "available_incremental_risk":cb.get("available_incremental_risk",0.0),
            "weakest_capability":weakest}

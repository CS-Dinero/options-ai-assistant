"""env/promotion_gate_engine.py — Gate checks for DEV→SIM and SIM→LIVE promotions."""
from __future__ import annotations
from typing import Any

def evaluate_environment_promotion(
    source_environment: str, target_environment: str,
    validation_summary: dict[str,Any], active_alerts: list[dict[str,Any]],
    approval_present: bool,
) -> dict[str,Any]:
    fail_count    = int(validation_summary.get("total_fail",0))
    critical_alerts=[a for a in active_alerts if a.get("severity")=="CRITICAL"]
    allowed=True; reasons=[]
    if fail_count>0:
        allowed=False; reasons.append("validation suite has failures")
    if target_environment=="LIVE" and critical_alerts:
        allowed=False; reasons.append("critical alerts active; live promotion blocked")
    if target_environment=="LIVE" and not approval_present:
        allowed=False; reasons.append("live promotion requires explicit approval")
    return {"promotion_allowed":allowed,"reasons":reasons,
            "source_environment":source_environment,"target_environment":target_environment}

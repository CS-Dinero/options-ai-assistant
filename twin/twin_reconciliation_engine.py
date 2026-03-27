"""twin/twin_reconciliation_engine.py — Aligns recommendation, decision, execution, and outcome."""
from __future__ import annotations
from typing import Any

def reconcile_twin_record(decision_moment: dict[str,Any], recommendation: dict[str,Any]|None,
                           approved_action: dict[str,Any]|None, executed_action: dict[str,Any]|None,
                           realized_outcome: dict[str,Any]|None) -> dict[str,Any]:
    rec=(recommendation or {}).get("recommended_path_code")
    appr=(approved_action or {}).get("chosen_path_code")
    exec_=(executed_action or {}).get("executed_path_code")
    return {"twin_id":decision_moment.get("twin_id"),
            "recommended_path_code":rec,"approved_path_code":appr,"executed_path_code":exec_,
            "recommendation_followed":rec==appr if appr else None,
            "approval_executed_match":appr==exec_ if exec_ else None,
            "realized_outcome":realized_outcome or {}}

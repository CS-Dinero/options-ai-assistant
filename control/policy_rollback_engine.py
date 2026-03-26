"""control/policy_rollback_engine.py — Restores a prior live version safely."""
from __future__ import annotations
from typing import Any
from datetime import datetime

def rollback_to_policy_version(registry: list[dict[str,Any]], target_version_id: str,
                                rolled_back_by: str, rollback_reason: str) -> list[dict[str,Any]]:
    updated=[]
    for v in registry:
        vv=dict(v)
        if vv.get("status")=="LIVE":
            vv["status"]="ROLLED_BACK"; vv["rolled_back_utc"]=datetime.utcnow().isoformat()
            vv["rolled_back_by"]=rolled_back_by; vv["rollback_reason"]=rollback_reason
        if vv.get("policy_version_id")==target_version_id:
            vv["status"]="LIVE"; vv["activated_utc"]=datetime.utcnow().isoformat()
            vv["activated_by"]=rolled_back_by; vv["activation_note"]=f"Rollback: {rollback_reason}"
        updated.append(vv)
    return updated

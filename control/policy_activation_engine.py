"""control/policy_activation_engine.py — Promotes approved version to live."""
from __future__ import annotations
from typing import Any
from datetime import datetime

def activate_policy_version(registry: list[dict[str,Any]], policy_version_id: str,
                             activated_by: str, activation_note: str="") -> list[dict[str,Any]]:
    updated=[]
    for v in registry:
        vv=dict(v)
        if vv.get("status")=="LIVE": vv["status"]="ARCHIVED"
        if vv.get("policy_version_id")==policy_version_id:
            vv["status"]="LIVE"; vv["activated_utc"]=datetime.utcnow().isoformat()
            vv["activated_by"]=activated_by; vv["activation_note"]=activation_note
        updated.append(vv)
    return updated

"""control/policy_version_registry.py — Stores every live and draft policy snapshot."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def create_policy_version(policy_bundle: dict[str,Any], status: str="DRAFT",
                           parent_version_id: str|None=None, scenario_name: str|None=None,
                           notes: str="") -> dict[str,Any]:
    return {"policy_version_id":str(uuid.uuid4()),"parent_version_id":parent_version_id,
            "status":status,"scenario_name":scenario_name,"notes":notes,
            "created_utc":datetime.utcnow().isoformat(),"approved_utc":None,
            "activated_utc":None,"rolled_back_utc":None,"policy_bundle":policy_bundle}

def append_policy_version(registry: list[dict[str,Any]], version: dict[str,Any]) -> list[dict[str,Any]]:
    return list(registry or []) + [version]

def get_live_policy_version(registry: list[dict[str,Any]]) -> dict[str,Any]|None:
    live=[v for v in registry if v.get("status")=="LIVE"]
    return max(live, key=lambda v: v.get("activated_utc") or "") if live else None

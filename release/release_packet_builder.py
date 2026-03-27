"""release/release_packet_builder.py — Creates the structured release packet."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_release_packet(environment: str, bundle: dict[str,Any], scope: dict[str,Any],
                          validation_requirements: dict[str,Any], rollout_plan: dict[str,Any],
                          monitoring_plan: dict[str,Any], rollback_plan: dict[str,Any]) -> dict[str,Any]:
    return {"release_id":str(uuid.uuid4()),"environment":environment,
            "bundle_type":bundle.get("bundle_type"),"title":bundle.get("title"),
            "rationale":bundle.get("rationale"),"included_changes":bundle.get("included_changes",[]),
            "scope":scope,"validation_requirements":validation_requirements,
            "rollout_plan":rollout_plan,"monitoring_plan":monitoring_plan,"rollback_plan":rollback_plan,
            "state":"DRAFT","created_utc":datetime.utcnow().isoformat()}

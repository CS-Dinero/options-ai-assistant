"""workspace/workspace_state_builder.py — Builds the common workspace envelope."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_workspace_state(environment: str, workspace_type: str, symbol: str,
                           selected_path: dict[str,Any],
                           linked_object_ids: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"workspace_id":str(uuid.uuid4()),"environment":environment,
            "workspace_type":workspace_type,"symbol":symbol,"selected_path":selected_path,
            "linked_object_ids":linked_object_ids or {},"state":"OPEN",
            "blockers":[],"ticket_readiness":{},"captured_actions":[],
            "created_utc":datetime.utcnow().isoformat()}

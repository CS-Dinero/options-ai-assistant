"""workspace/action_capture_engine.py — Captures what the operator actually did."""
from __future__ import annotations
from typing import Any
from datetime import datetime

def capture_workspace_action(workspace: dict[str,Any], action_type: str, actor: str,
                              note: str="", metadata: dict[str,Any]|None=None) -> dict[str,Any]:
    out=dict(workspace); actions=list(out.get("captured_actions",[]))
    actions.append({"action_type":action_type,"actor":actor,"note":note,
                    "metadata":metadata or {},"timestamp_utc":datetime.utcnow().isoformat()})
    out["captured_actions"]=actions; return out

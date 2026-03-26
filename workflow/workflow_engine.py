"""workflow/workflow_engine.py — Applies valid state transitions with event emission."""
from __future__ import annotations
from typing import Any
from workflow.workflow_guard import validate_transition
from workflow.workflow_events import build_workflow_event

def _obj_id(obj: dict) -> str:
    for k in ("policy_version_id","change_request_id","journal_id","id","trade_id"):
        if obj.get(k): return str(obj[k])
    return "unknown"

def apply_state_transition(obj: dict[str,Any], object_type: str, target_state: str,
                            actor: str, note: str="",
                            metadata: dict[str,Any]|None=None) -> tuple[dict[str,Any],dict[str,Any]]:
    current_state = obj.get("state") or obj.get("status","UNKNOWN")
    validate_transition(object_type, current_state, target_state)
    updated = dict(obj); updated["state"] = target_state
    event = build_workflow_event(object_type=object_type, object_id=_obj_id(obj),
                                  from_state=current_state, to_state=target_state,
                                  actor=actor, note=note, metadata=metadata)
    return updated, event

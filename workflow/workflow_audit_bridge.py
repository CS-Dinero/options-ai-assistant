"""workflow/workflow_audit_bridge.py — Converts workflow events into control-plane audit events."""
from __future__ import annotations
from typing import Any
from control.control_plane_audit_log import build_control_plane_event

def workflow_event_to_audit_event(workflow_event: dict[str,Any]) -> dict[str,Any]:
    return build_control_plane_event(
        event_type="WORKFLOW_STATE_CHANGE",
        actor=workflow_event.get("actor","unknown"),
        object_id=workflow_event.get("object_id","unknown"),
        summary=(f"{workflow_event.get('object_type')} "
                 f"{workflow_event.get('from_state')} → {workflow_event.get('to_state')}"),
        metadata=workflow_event)

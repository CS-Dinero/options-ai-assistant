"""auth/audit_enforcer.py — Builds permission-stamped audit events for privileged actions."""
from __future__ import annotations
from typing import Any
from control.control_plane_audit_log import build_control_plane_event

def build_permission_audit_event(session_context: dict[str,Any], event_type: str,
                                  object_id: str, summary: str, required_permission: str,
                                  metadata: dict[str,Any]|None=None) -> dict[str,Any]:
    meta = dict(metadata or {})
    meta["required_permission"] = required_permission
    meta["active_role"] = session_context.get("active_role")
    return build_control_plane_event(
        event_type=event_type,
        actor=session_context.get("display_name", session_context.get("user_id","unknown")),
        object_id=object_id, summary=summary, metadata=meta)

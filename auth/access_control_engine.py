"""auth/access_control_engine.py — Central permission checker."""
from __future__ import annotations
from typing import Any
from auth.role_resolver import resolve_permissions

def check_permission(session_context: dict[str,Any], required_permission: str) -> dict[str,Any]:
    perms = resolve_permissions(session_context)
    return {"allowed":required_permission in perms,"required_permission":required_permission,
            "active_role":session_context.get("active_role"),"user_id":session_context.get("user_id")}

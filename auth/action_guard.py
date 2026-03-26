"""auth/action_guard.py — Hard permission wrapper for privileged actions."""
from __future__ import annotations
from typing import Any
from auth.access_control_engine import check_permission

class PermissionDenied(Exception):
    pass

def guard_action(session_context: dict[str,Any], required_permission: str, action_name: str) -> None:
    result = check_permission(session_context, required_permission)
    if not result["allowed"]:
        raise PermissionDenied(
            f"{action_name} denied: requires {required_permission}, "
            f"active_role={result['active_role']}, user={result['user_id']}")

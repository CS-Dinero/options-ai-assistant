"""auth/session_context.py — Active operator identity and role."""
from __future__ import annotations
from typing import Any

def build_session_context(user_id: str, display_name: str, roles: list[str],
                           active_role: str|None=None) -> dict[str,Any]:
    chosen = active_role or (roles[0] if roles else "ANALYST")
    return {"user_id":user_id,"display_name":display_name,"roles":roles,"active_role":chosen}

def default_admin_context() -> dict[str,Any]:
    return build_session_context("admin","Admin",["ADMIN"],"ADMIN")

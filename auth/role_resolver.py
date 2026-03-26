"""auth/role_resolver.py — Derives effective permissions from all assigned roles."""
from __future__ import annotations
from typing import Any
from auth.permission_matrix import PERMISSION_MATRIX

def resolve_permissions(session_context: dict[str,Any]) -> set[str]:
    perms: set[str] = set()
    for role in session_context.get("roles",[]):
        perms |= set(PERMISSION_MATRIX.get(role, set()))
    return perms

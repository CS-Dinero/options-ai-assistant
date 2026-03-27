"""autopilot/boundary_policy_engine.py — Resolves the boundary for any action."""
from __future__ import annotations
from autopilot.delegation_matrix import DELEGATION_MATRIX

def get_allowed_authority(environment: str, action_family: str) -> str:
    return str(DELEGATION_MATRIX.get(str(environment),{}).get(str(action_family),"NEVER_AUTOMATE"))

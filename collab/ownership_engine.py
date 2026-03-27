"""collab/ownership_engine.py — Tracks current owner and pending target."""
from __future__ import annotations
from typing import Any

def assign_handoff_owner(handoff_packet: dict[str,Any], target_user_id: str|None=None,
                          target_display_name: str|None=None) -> dict[str,Any]:
    out=dict(handoff_packet)
    out["current_owner_role"]=handoff_packet.get("target_role")
    out["current_owner_user_id"]=target_user_id
    out["current_owner_display_name"]=target_display_name
    return out

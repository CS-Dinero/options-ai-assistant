"""collab/handoff_queue_engine.py — Builds inbound handoff queue by role."""
from __future__ import annotations
from typing import Any

def build_handoff_queue(handoff_packets: list[dict[str,Any]], role: str) -> list[dict[str,Any]]:
    return [h for h in handoff_packets if h.get("target_role")==role and h.get("state") in ("OPEN","ACCEPTED")]

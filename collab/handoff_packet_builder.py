"""collab/handoff_packet_builder.py — Builds the transfer object."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_handoff_packet(environment: str, handoff_type: str, source_role: str, target_role: str,
                          linked_object_ids: dict[str,Any], summary: str, required_next_action: str,
                          blockers: list[dict[str,Any]]|None=None,
                          notes: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    return {"handoff_id":str(uuid.uuid4()),"environment":environment,"handoff_type":handoff_type,
            "source_role":source_role,"target_role":target_role,"linked_object_ids":linked_object_ids,
            "summary":summary,"required_next_action":required_next_action,
            "blockers":blockers or [],"notes":notes or [],"state":"OPEN",
            "created_utc":datetime.utcnow().isoformat(),"accepted_utc":None,"completed_utc":None}

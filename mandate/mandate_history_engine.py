"""mandate/mandate_history_engine.py — Tracks mandate changes over time."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_mandate_history_entry(environment: str, old_mandate: str, new_mandate: str,
                                 changed_by: str, rationale: str,
                                 live_policy_version_id: str|None=None) -> dict[str,Any]:
    return {"mandate_history_id":str(uuid.uuid4()),"environment":environment,
            "old_mandate":old_mandate,"new_mandate":new_mandate,"changed_by":changed_by,
            "rationale":rationale,"live_policy_version_id":live_policy_version_id,
            "timestamp_utc":datetime.utcnow().isoformat()}

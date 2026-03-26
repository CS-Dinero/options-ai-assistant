"""review/review_trigger_engine.py — Triggers human review tasks from system signals."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

REVIEW_TRIGGERS: set = {"ROLLBACK_WATCH","PROMOTED_PLAYBOOK_REVIEW","POLICY_SIMULATION_REVIEW"}

def build_review_task(review_type: str, environment: str, object_id: str,
                      summary: str, source: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"review_id":str(uuid.uuid4()),"review_type":review_type,"environment":environment,
            "object_id":object_id,"summary":summary,"state":"PENDING",
            "source":source or {},"created_utc":datetime.utcnow().isoformat()}

def should_trigger_review(signal_type: str, score: float) -> bool:
    return signal_type in {"PLAYBOOK_DEGRADATION_SIGNAL","ROLLBACK_RECOMMENDATION_REPORT"} and score>=60.0

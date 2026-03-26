"""reporting/report_builder.py — Common envelope for all reports."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_report_envelope(report_type: str, environment: str, live_policy_version_id: str|None,
                           title: str, sections: list[dict[str,Any]],
                           summary_bullets: list[str]) -> dict[str,Any]:
    return {"report_id":str(uuid.uuid4()),"report_type":report_type,"environment":environment,
            "timestamp_utc":datetime.utcnow().isoformat(),"live_policy_version_id":live_policy_version_id,
            "title":title,"summary_bullets":summary_bullets,"sections":sections}

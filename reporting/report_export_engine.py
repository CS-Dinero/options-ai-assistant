"""reporting/report_export_engine.py — Exports report payloads as JSON string."""
from __future__ import annotations
from typing import Any
import json

def export_report_payload(report: dict[str,Any]) -> str:
    return json.dumps(report, indent=2, default=str)

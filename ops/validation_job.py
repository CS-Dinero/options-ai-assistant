"""ops/validation_job.py — Runs validation suite and packages result."""
from __future__ import annotations
from tests.run_validation import run_all_validations
from datetime import datetime
import uuid

def run_validation_job(ctx: dict) -> dict:
    summary=run_all_validations()
    return {"validation_run_id":str(uuid.uuid4()),"environment":ctx["environment"],
            "timestamp_utc":datetime.utcnow().isoformat(),
            "total_pass":summary.get("total_pass",0),"total_fail":summary.get("total_fail",0),
            "results":summary.get("results",[])}

"""ops/job_runner.py — Orchestrates job execution with environment checks and result capture."""
from __future__ import annotations
from typing import Any, Callable
from datetime import datetime
import uuid
from ops.job_registry import JOB_REGISTRY

def run_job(job_name: str, environment: str, job_fn: Callable, context: dict[str,Any]) -> dict[str,Any]:
    spec=JOB_REGISTRY.get(job_name,{}); allowed=spec.get("allowed_environments",[])
    base={"job_run_id":str(uuid.uuid4()),"job_name":job_name,"environment":environment,
          "timestamp_utc":datetime.utcnow().isoformat()}
    if environment not in allowed:
        return {**base,"status":"SKIPPED","error":f"{job_name} not allowed in {environment}"}
    try:
        result=job_fn(context)
        return {**base,"status":"SUCCESS","result":result}
    except Exception as e:
        return {**base,"status":"FAILED","error":str(e)}

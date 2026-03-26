"""ops/job_result_router.py — Routes job outputs to correct repositories."""
from __future__ import annotations
from typing import Any

def route_job_result(job_run: dict[str,Any], storage_router) -> None:
    job_name=job_run.get("job_name"); result=job_run.get("result",{}); status=job_run.get("status")
    try: storage_router.save_environment_state(f"job_run::{job_run['job_run_id']}", job_run)
    except: pass
    if status!="SUCCESS" or not result: return
    try:
        if job_name=="VALIDATION_JOB":
            storage_router.save_validation_run(result)
        elif job_name in ("DAILY_DESK_REPORT_JOB","WEEKLY_PLAYBOOK_REVIEW_JOB",
                           "POLICY_FOLLOWUP_JOB","END_OF_SESSION_JOB"):
            repo=getattr(storage_router,"repos",{}).get("reports")
            if repo and result.get("report_id"): repo.insert(result["report_id"],result)
        elif job_name=="RECURRING_SNAPSHOT_JOB":
            for snap in result.get("snapshots",[]):
                repo=getattr(storage_router,"repos",{}).get("snapshots")
                if repo: repo.insert(snap["snapshot_id"],snap)
        elif job_name=="ALERT_SWEEP_JOB":
            for a in result.get("alerts",[]): storage_router.save_alert(a)
    except: pass

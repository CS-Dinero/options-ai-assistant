"""ops/job_registry.py — Operational job catalog."""
JOB_REGISTRY: dict = {
    "RECURRING_SNAPSHOT_JOB":       {"description":"Capture queue/portfolio/execution snapshots.","allowed_environments":["DEV","SIM","LIVE"]},
    "VALIDATION_JOB":               {"description":"Run validation suites and store result.","allowed_environments":["DEV","SIM","LIVE"]},
    "DAILY_DESK_REPORT_JOB":        {"description":"Generate daily desk summary report.","allowed_environments":["SIM","LIVE"]},
    "WEEKLY_PLAYBOOK_REVIEW_JOB":   {"description":"Generate weekly playbook review report.","allowed_environments":["SIM","LIVE"]},
    "POLICY_FOLLOWUP_JOB":          {"description":"Generate post-activation impact review.","allowed_environments":["SIM","LIVE"]},
    "ALERT_SWEEP_JOB":              {"description":"Recompute metrics and refresh alerts.","allowed_environments":["DEV","SIM","LIVE"]},
    "END_OF_SESSION_JOB":           {"description":"Generate closeout state package.","allowed_environments":["SIM","LIVE"]},
}

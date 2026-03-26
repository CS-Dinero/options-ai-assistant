"""ops/schedule_registry.py — Cadence definitions for recurring and event-based jobs."""
SCHEDULE_REGISTRY: dict = {
    "HOURLY_SNAPSHOT":              {"type":"TIME_BASED","cadence":"HOURLY","job_name":"RECURRING_SNAPSHOT_JOB"},
    "PREMARKET_VALIDATION":         {"type":"TIME_BASED","cadence":"DAILY_PREMARKET","job_name":"VALIDATION_JOB"},
    "DAILY_DESK_SUMMARY":           {"type":"TIME_BASED","cadence":"DAILY_PREMARKET","job_name":"DAILY_DESK_REPORT_JOB"},
    "END_OF_SESSION":               {"type":"TIME_BASED","cadence":"DAILY_POSTCLOSE","job_name":"END_OF_SESSION_JOB"},
    "WEEKLY_PLAYBOOK_REVIEW":       {"type":"TIME_BASED","cadence":"WEEKLY","job_name":"WEEKLY_PLAYBOOK_REVIEW_JOB"},
    "POST_POLICY_ACTIVATION":       {"type":"EVENT_BASED","event":"POLICY_ACTIVATED","job_name":"POLICY_FOLLOWUP_JOB"},
    "POST_EXECUTION_SWEEP":         {"type":"EVENT_BASED","event":"EXECUTION_BATCH_COMPLETE","job_name":"ALERT_SWEEP_JOB"},
}

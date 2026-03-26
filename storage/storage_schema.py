"""storage/storage_schema.py — Canonical record key definitions."""
SCHEMA_KEYS: dict = {
    "policy_version":["policy_version_id","environment","status","created_utc","approved_utc","activated_utc","policy_bundle"],
    "policy_change_request":["change_request_id","environment","baseline_version_id","scenario_name","status","requested_utc","proposed_policy_bundle"],
    "workflow_event":["workflow_event_id","environment","object_type","object_id","from_state","to_state","actor","timestamp_utc"],
    "transition_journal":["journal_id","environment","campaign_id","position_id","symbol","playbook_code","status","timestamp_utc"],
    "slippage_event":["slippage_id","environment","journal_id","symbol","action","time_window","actual_credit","slippage_dollars","fill_score","timestamp_utc"],
    "alert":["alert_id","environment","metric_name","severity","summary","timestamp_utc"],
    "validation_run":["validation_run_id","environment","timestamp_utc","total_pass","total_fail","results"],
}

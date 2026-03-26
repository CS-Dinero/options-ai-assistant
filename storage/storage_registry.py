"""storage/storage_registry.py — Storage domain definitions."""
STORAGE_REGISTRY: dict = {
    "POLICY":     {"tables":["policy_versions","policy_change_requests","control_plane_audit_log"]},
    "WORKFLOW":   {"tables":["workflow_events","object_state_index"]},
    "JOURNAL":    {"tables":["transition_journals","transition_outcomes","slippage_events"]},
    "ALERTING":   {"tables":["alerts","alert_history"]},
    "RESEARCH":   {"tables":["research_rows","playbook_stats_snapshots","playbook_rankings"]},
    "VALIDATION": {"tables":["validation_runs","validation_suite_results"]},
    "ENVIRONMENT":{"tables":["environment_runtime_state"]},
}

"""reporting/report_registry.py — Report type universe."""
REPORT_REGISTRY: dict = {
    "DAILY_DESK_SUMMARY":           {"description":"Current day operational summary."},
    "WEEKLY_PLAYBOOK_REVIEW":       {"description":"Weekly playbook evidence and drift."},
    "POLICY_IMPACT_MEMO":           {"description":"Before/after analysis for a policy activation."},
    "EXECUTION_QUALITY_REPORT":     {"description":"Fill quality, slippage, and execution analysis."},
    "ROLLBACK_RECOMMENDATION_REPORT":{"description":"Structured justification for policy review or rollback."},
    "END_OF_SESSION_REPORT":        {"description":"Operational closeout package."},
}

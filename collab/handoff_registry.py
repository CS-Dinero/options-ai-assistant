"""collab/handoff_registry.py — Handoff type definitions."""
HANDOFF_REGISTRY: dict = {
    "ANALYST_TO_APPROVER":   {"description":"Analyst hands a reviewed item to approver for decision."},
    "APPROVER_TO_OPERATOR":  {"description":"Approved item moves to operator for execution or action."},
    "OPERATOR_TO_ANALYST":   {"description":"Operator returns item for analysis or re-evaluation."},
    "OPERATOR_TO_APPROVER":  {"description":"Operator escalates an issue requiring approval judgment."},
    "REVIEW_ESCALATION":     {"description":"Review item escalated to higher-authority role."},
    "WORKSPACE_ESCALATION":  {"description":"Workspace cannot proceed without role transfer."},
    "POST_ACTION_FOLLOWUP":  {"description":"Completed action requires follow-up by another role."},
}

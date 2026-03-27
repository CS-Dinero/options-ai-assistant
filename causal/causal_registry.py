"""causal/causal_registry.py — Intervention types worth evaluating."""
CAUSAL_REGISTRY: dict = {
    "POLICY_CHANGE":         {"description":"A policy version change intended to improve behavior."},
    "MANDATE_SWITCH":        {"description":"A change in active operating objective."},
    "PLAYBOOK_STATUS_CHANGE":{"description":"Promotion, demotion, or selective-use change."},
    "EXECUTION_RULE_CHANGE": {"description":"Change to stagger, execution caution, or threshold logic."},
    "REVIEW_WORKFLOW_CHANGE":{"description":"Change to review routing, escalation, or approval workflow."},
    "HANDOFF_SIMPLIFICATION":{"description":"Removal, merge, or reduction of collaboration friction."},
    "RISK_ENVELOPE_CHANGE":  {"description":"Change to capital posture or deployment bounds."},
    "REFINEMENT_ADOPTION":   {"description":"Adoption of a recommendation into active behavior."},
}

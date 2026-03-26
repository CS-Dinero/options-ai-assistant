"""decision/decision_registry.py — Decision type universe."""
DECISION_REGISTRY: dict = {
    "APPROVE_POLICY_CHANGE":  {"family":"POLICY",    "description":"Human approved a policy change request."},
    "REJECT_POLICY_CHANGE":   {"family":"POLICY",    "description":"Human rejected a policy change request."},
    "ACTIVATE_POLICY":        {"family":"POLICY",    "description":"Human activated an approved policy version."},
    "ROLLBACK_POLICY":        {"family":"POLICY",    "description":"Human rolled back live policy."},
    "APPROVE_EXECUTION":      {"family":"EXECUTION", "description":"Human approved an execution recommendation."},
    "DEFER_EXECUTION":        {"family":"EXECUTION", "description":"Human deferred an execution recommendation."},
    "REJECT_EXECUTION":       {"family":"EXECUTION", "description":"Human rejected an execution recommendation."},
    "OVERRIDE_QUEUE_PRIORITY":{"family":"QUEUE",     "description":"Human changed queue handling."},
    "OVERRIDE_PLAYBOOK_STATUS":{"family":"PLAYBOOK", "description":"Human overrode system playbook status."},
    "DISMISS_REVIEW":         {"family":"REVIEW",    "description":"Human dismissed a review task."},
    "ESCALATE_REVIEW":        {"family":"REVIEW",    "description":"Human escalated a review task."},
}

"""review/review_registry.py — Review type universe."""
REVIEW_REGISTRY: dict = {
    "POLICY_CHANGE_APPROVAL_REVIEW": {"description":"Formal approval review for a submitted policy change request."},
    "ROLLBACK_WATCH_REVIEW":         {"description":"Human review of rollback-watch conditions under live policy."},
    "PLAYBOOK_DEGRADATION_REVIEW":   {"description":"Review a playbook whose live evidence is deteriorating."},
    "SLIPPAGE_HOTSPOT_REVIEW":       {"description":"Review persistent fill-quality or slippage degradation."},
    "QUEUE_STARVATION_REVIEW":       {"description":"Review low queue depth or excessive blocking."},
    "CAPITAL_CHOKE_REVIEW":          {"description":"Review elevated capital block rate or concurrency choke."},
    "POLICY_SIMULATION_REVIEW":      {"description":"Review a policy simulation result before escalation."},
    "PROMOTED_PLAYBOOK_REVIEW":      {"description":"Review a promoted playbook that may no longer deserve status."},
}

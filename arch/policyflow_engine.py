"""arch/policyflow_engine.py — How the system evolves its own policy safely."""
POLICY_FLOW: list = [
    "refinement_candidate_engine","refinement_to_policy_request_engine",
    "policy_change_request_engine","policy_simulator",
    "policy_approval_engine","policy_activation_engine",
    "rollback_watch_engine","policy_impact_tracker",
]

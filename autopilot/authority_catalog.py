"""autopilot/authority_catalog.py — Action family definitions."""
AUTHORITY_CATALOG: dict = {
    "QUEUE_RANKING":         {"description":"Ranking and prioritization of candidates."},
    "REPORT_GENERATION":     {"description":"Automated report and memo creation."},
    "ALERT_GENERATION":      {"description":"Threshold-based and monitoring-driven alerting."},
    "REVIEW_CREATION":       {"description":"Creation of review packets and review queue items."},
    "REFINEMENT_SUGGESTION": {"description":"Generation of improvement recommendations."},
    "POLICY_SIMULATION":     {"description":"Simulation of policy behavior outside LIVE application."},
    "POLICY_APPROVAL":       {"description":"Approving a policy or change request."},
    "POLICY_ACTIVATION":     {"description":"Promoting or activating policy into an environment."},
    "CAPITAL_SIZING":        {"description":"Sizing and capital deployment labeling."},
    "TICKET_DRAFTING":       {"description":"Drafting execution tickets from workspace/path context."},
    "LIVE_EXECUTION":        {"description":"Actual live execution of risk-bearing action."},
    "PRUNING_RECOMMENDATION":{"description":"Recommending simplification or retirement."},
    "RELEASE_ROLLOUT":       {"description":"Advancing a release bundle through environments."},
}

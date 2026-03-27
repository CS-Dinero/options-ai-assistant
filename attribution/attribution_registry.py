"""attribution/attribution_registry.py — Components available for attribution."""
ATTRIBUTION_REGISTRY: dict = {
    "PLAYBOOK":      {"description":"Impact attributable to a playbook family or code."},
    "MANDATE":       {"description":"Impact attributable to the active operating mandate."},
    "POLICY_VERSION":{"description":"Impact attributable to a live policy version."},
    "REVIEW_TYPE":   {"description":"Impact attributable to a review class."},
    "DECISION_TYPE": {"description":"Impact attributable to a human decision class."},
    "HANDOFF_TYPE":  {"description":"Impact attributable to a collaboration handoff pattern."},
    "WORKSPACE_PATH":{"description":"Impact attributable to a selected execution path."},
    "AUTOMATION_JOB":{"description":"Impact attributable to a scheduled operations job."},
    "REFINEMENT_TYPE":{"description":"Impact attributable to a refinement recommendation class."},
}

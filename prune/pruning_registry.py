"""prune/pruning_registry.py — Prunable component family definitions."""
PRUNING_REGISTRY: dict = {
    "PLAYBOOK":              {"description":"Playbook may be kept, demoted, merged, or retired."},
    "REVIEW_TYPE":           {"description":"Review classes may be simplified or merged."},
    "HANDOFF_TYPE":          {"description":"Handoff patterns may be reduced if they add friction without improving outcomes."},
    "AUTOMATION_JOB":        {"description":"Scheduled jobs may be retained or retired based on operational value."},
    "REFINEMENT_TYPE":       {"description":"Refinement classes may be simplified if they create churn."},
    "WORKSPACE_STEP_PATTERN":{"description":"Workspace SOP flows may be simplified if steps are redundant."},
    "POLICY_RULE":           {"description":"Policy rules may be simplified, merged, or retired."},
    "ALERT_RULE":            {"description":"Alert rules may be simplified or retired if noisy and low-value."},
    "REPORT_TYPE":           {"description":"Reports may be demoted or retired if rarely used."},
}

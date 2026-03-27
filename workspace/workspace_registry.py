"""workspace/workspace_registry.py — Workspace type definitions."""
WORKSPACE_REGISTRY: dict = {
    "PATH_EXECUTION_WORKSPACE": {"description":"Guided work surface for executing the selected path."},
    "REVIEW_WORKSPACE":         {"description":"Guided work surface for human review tasks."},
    "POLICY_WORKSPACE":         {"description":"Guided work surface for policy simulations and approvals."},
    "POST_ACTION_WORKSPACE":    {"description":"Guided work surface for post-execution follow-up."},
}

"""arch/system_registry.py — Major layer/domain definitions."""
SYSTEM_REGISTRY: dict = {
    "DECISION":           {"description":"Core scoring and structure-selection engines."},
    "INTELLIGENCE":       {"description":"Narratives, research, diagnostics, forecasts, and knowledge context."},
    "GOVERNANCE":         {"description":"Policies, roles, permissions, workflow states, environments, and validation."},
    "OPERATIONS":         {"description":"Alerts, jobs, reports, trends, monitoring, and runtime health."},
    "HUMAN_SUPERVISION":  {"description":"Reviews, decisions, rationale, overrides, and handoffs."},
    "EXECUTION_WORKFLOW": {"description":"Workspace, SOP, ticket readiness, action capture, and follow-through."},
    "ADAPTATION":         {"description":"Refinements, mandates, stress testing, attribution, and pruning."},
    "ARCHITECTURE":       {"description":"System map, impact tracing, dependency graph, and living reference docs."},
}

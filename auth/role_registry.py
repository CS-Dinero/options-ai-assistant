"""auth/role_registry.py — Supported roles and their intended scope."""
ROLE_REGISTRY: dict = {
    "ANALYST":        {"description":"Can inspect, simulate, and draft. Cannot approve, activate, or execute."},
    "APPROVER":       {"description":"Can approve change requests. Cannot execute trades unless dual-role."},
    "TRADER_OPERATOR":{"description":"Can execute tickets and manage live queue. Cannot approve policy."},
    "ADMIN":          {"description":"Full system administration. Should still respect approval workflow."},
}

"""mandate/mandate_registry.py — Named operating mandate universe."""
MANDATE_REGISTRY: dict = {
    "BASIS_RECOVERY":              {"description":"Prioritize reducing campaign basis and improving recovery speed."},
    "CAPITAL_PRESERVATION":        {"description":"Prioritize capital efficiency, lower concurrency, and reduced expansion."},
    "EXECUTION_QUALITY":           {"description":"Prioritize fill quality, slippage control, and cleaner execution."},
    "QUEUE_HEALTH":                {"description":"Prioritize a healthy, actionable queue and reduce starvation."},
    "PLAYBOOK_PROMOTION_UTILIZATION":{"description":"Favor promoted playbooks and validated operating patterns."},
    "RISK_CONCENTRATION_REDUCTION":{"description":"Reduce symbol/structure concentration and improve balance."},
    "POLICY_STABILITY":            {"description":"Reduce policy churn and favor conservative, repeatable behavior."},
}
DEFAULT_MANDATE = "BASIS_RECOVERY"

"""twin/twin_registry.py — Digital twin object family definitions."""
TWIN_REGISTRY: dict = {
    "DECISION_MOMENT":     {"description":"A point in time when one or more actionable paths existed."},
    "SYSTEM_RECOMMENDATION":{"description":"What the system preferred at that decision moment."},
    "APPROVED_ACTION":     {"description":"What the human approved or selected."},
    "EXECUTED_ACTION":     {"description":"What was actually executed or deferred."},
    "COUNTERFACTUAL_PATH": {"description":"An alternative path not taken but worth tracking."},
    "REALIZED_OUTCOME":    {"description":"What actually happened after action or non-action."},
}

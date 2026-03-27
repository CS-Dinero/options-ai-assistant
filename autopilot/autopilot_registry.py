"""autopilot/autopilot_registry.py — Automation authority level definitions."""
AUTOPILOT_REGISTRY: dict = {
    "AUTO":            {"description":"May run end-to-end without human intervention."},
    "AUTO_DRAFT":      {"description":"May generate proposed outputs, but may not finalize or apply them."},
    "HUMAN_APPROVAL":  {"description":"Requires explicit human approval before applying."},
    "HUMAN_EXECUTION": {"description":"System may draft; final execution must be performed by a human."},
    "NEVER_AUTOMATE":  {"description":"Must never be delegated to automation."},
}

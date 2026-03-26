"""env/environment_registry.py — Three-environment registry."""
ENVIRONMENT_REGISTRY: dict = {
    "DEV":  {"description":"Developer sandbox for building, debugging, and structural validation."},
    "SIM":  {"description":"Paper-trading environment for operational rehearsal and policy testing."},
    "LIVE": {"description":"Production environment with live policy, alerts, and execution authority."},
}

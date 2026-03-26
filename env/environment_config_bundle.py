"""env/environment_config_bundle.py — Per-environment behaviour config."""
from __future__ import annotations

ENVIRONMENT_CONFIG: dict = {
    "DEV": {
        "execution_enabled": False,
        "policy_activation_enabled": False,
        "requires_validation_pass": False,
        "ticket_prefix": "DEV",
        "alert_threshold_profile": "DEV",
        "max_operator_scope": "ADMIN",
    },
    "SIM": {
        "execution_enabled": False,
        "policy_activation_enabled": True,
        "requires_validation_pass": True,
        "ticket_prefix": "SIM",
        "alert_threshold_profile": "SIM",
        "max_operator_scope": "APPROVER",
    },
    "LIVE": {
        "execution_enabled": True,
        "policy_activation_enabled": True,
        "requires_validation_pass": True,
        "ticket_prefix": "LIVE",
        "alert_threshold_profile": "LIVE",
        "max_operator_scope": "ADMIN",
    },
}

def get_env_config(environment: str) -> dict:
    return ENVIRONMENT_CONFIG.get(str(environment).upper(), ENVIRONMENT_CONFIG["DEV"])

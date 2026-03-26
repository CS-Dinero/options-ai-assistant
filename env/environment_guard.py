"""env/environment_guard.py — Hard blocks for environment-illegal actions."""
from __future__ import annotations
from env.environment_config_bundle import get_env_config

class EnvironmentDenied(Exception):
    pass

def guard_environment_action(environment: str, action_name: str,
                              require_execution_enabled: bool=False,
                              require_policy_activation_enabled: bool=False) -> None:
    cfg = get_env_config(environment)
    if require_execution_enabled and not cfg.get("execution_enabled",False):
        raise EnvironmentDenied(f"{action_name} denied in {environment}: execution not enabled")
    if require_policy_activation_enabled and not cfg.get("policy_activation_enabled",False):
        raise EnvironmentDenied(f"{action_name} denied in {environment}: policy activation not enabled")

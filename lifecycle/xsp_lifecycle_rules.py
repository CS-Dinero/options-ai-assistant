"""lifecycle/xsp_lifecycle_rules.py — Shared config and state constants for XSP lifecycle."""
from dataclasses import dataclass

XSP_STATE_HOLD        = "HOLD"
XSP_STATE_HARVEST     = "HARVEST"
XSP_STATE_FORCE_CLOSE = "FORCE_CLOSE"

@dataclass(slots=True)
class XSPLifecycleConfig:
    profit_take_min: float    = 0.30
    profit_take_target: float = 0.50
    stop_multiple: float      = 1.50
    force_exit_dte: int       = 2
    threatened_em_fraction: float = 0.50

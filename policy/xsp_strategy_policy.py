"""policy/xsp_strategy_policy.py — All XSP thresholds in one place."""
from dataclasses import dataclass

@dataclass(slots=True)
class XSPStrategyPolicy:
    # Credit spreads
    credit_short_dte_min: int   = 5
    credit_short_dte_max: int   = 10
    credit_short_delta_min: float = 0.20
    credit_short_delta_max: float = 0.30
    credit_spread_widths: tuple   = (1.0, 2.0)
    credit_min_credit: float      = 0.30
    credit_min_cwr: float         = 0.35
    credit_profit_take_min: float = 0.30
    credit_profit_take_target: float = 0.50
    credit_force_exit_dte: int    = 2
    credit_stop_multiple: float   = 1.50

    # Debit spreads
    debit_dte_min: int   = 7
    debit_dte_max: int   = 21
    debit_long_delta_min: float = 0.45
    debit_long_delta_max: float = 0.70
    debit_spread_widths: tuple  = (1.0, 2.0)
    debit_min: float = 0.20
    debit_max: float = 0.75
    debit_min_reward_risk: float = 0.75

    # Allocation
    max_contracts_cap: int       = 5
    max_risk_per_trade_pct: float = 0.02
    max_total_exposure_pct: float = 0.35

    # Liquidity
    min_open_interest: int = 200
    max_bid_ask_width: float = 0.10

"""
backtest/schemas.py
Central data contracts for Phase 4 backtesting.

All TypedDicts are total=False so partial construction is allowed
during iterative building. Required fields are documented in comments.
"""

from __future__ import annotations
from typing import TypedDict, Optional


class DailyContext(TypedDict, total=False):
    """Historical daily context — mirrors live derived context + VGA label."""
    date:            str       # required
    symbol:          str       # required
    spot_price:      float     # required
    expected_move:   float     # required
    upper_em:        float
    lower_em:        float
    em_method:       str
    atr_14:          Optional[float]
    atr_trend:       Optional[str]
    em_atr_ratio:    Optional[float]
    front_iv:        Optional[float]
    back_iv:         Optional[float]
    iv_percentile:   Optional[float]
    iv_rank:         Optional[float]
    iv_regime:       Optional[str]
    term_slope:      Optional[float]
    term_structure:  str
    skew_value:      Optional[float]
    skew_state:      str
    gex_by_strike:   dict
    total_gex:       Optional[float]
    gamma_regime:    str       # required
    gamma_flip:      Optional[float]
    gamma_trap:      Optional[float]
    vga_environment: str       # required


class SimulatedTradeResult(TypedDict, total=False):
    """Normalized result returned by trade_simulator.simulate_trade()."""
    trade_id:        str       # required
    symbol:          str       # required
    strategy_type:   str       # required
    direction:       str
    entry_date:      str       # required
    exit_date:       str       # required
    entry_price:     float     # required
    exit_price:      float     # required
    contracts:       int       # required
    pnl:             float     # required
    return_pct:      float     # required
    max_loss:        float     # required
    exit_reason:     str       # required — one of EXIT_REASONS
    days_held:       int       # required
    vga_environment: Optional[str]
    iv_regime:       Optional[str]
    gamma_regime:    Optional[str]
    term_structure:  Optional[str]
    score:           Optional[int]


class EquityCurvePoint(TypedDict, total=False):
    """One point in the equity curve timeline."""
    date:      str    # required
    cashflow:  float  # required
    equity:    float  # required


class GroupMetrics(TypedDict, total=False):
    """Performance metrics for any group of trades."""
    trades:           int
    win_rate:         float
    average_win:      float
    average_loss:     float
    expectancy:       float
    profit_factor:    float
    average_days_held: float
    return_on_risk:   float
    total_pnl:        float


# ── Valid exit reasons ────────────────────────────────────────────────────────
EXIT_REASONS = ("target_hit", "stop_hit", "expiration", "max_hold", "missing_data")

# ── Valid VGA environments ────────────────────────────────────────────────────
VGA_ENVIRONMENTS = (
    "premium_selling",
    "neutral_time_spreads",
    "cautious_directional",
    "trend_directional",
    "mixed",
)

# ── Required keys for validation ─────────────────────────────────────────────
REQUIRED_CONTEXT_KEYS = [
    "date", "symbol", "spot_price", "expected_move",
    "upper_em", "lower_em", "iv_regime", "term_structure",
    "gamma_regime", "vga_environment",
]

REQUIRED_SIM_TRADE_KEYS = [
    "trade_id", "symbol", "strategy_type",
    "entry_date", "exit_date", "entry_price", "exit_price",
    "contracts", "pnl", "return_pct", "max_loss",
    "exit_reason", "days_held",
    "vga_environment", "iv_regime", "gamma_regime", "term_structure", "score",
]

REQUIRED_EQUITY_KEYS = ["date", "cashflow", "equity"]

REQUIRED_REPORT_KEYS = ["by_strategy", "by_environment", "by_symbol", "by_regime"]

REQUIRED_GROUP_METRICS = [
    "trades", "win_rate", "average_win", "average_loss",
    "expectancy", "profit_factor", "average_days_held",
    "return_on_risk", "total_pnl",
]

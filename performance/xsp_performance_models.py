"""performance/xsp_performance_models.py — XSP spread + diagonal performance models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

XSPStructureType = Literal[
    "BULL_PUT_SPREAD",
    "BEAR_CALL_SPREAD",
    "BULL_CALL_SPREAD",
    "BEAR_PUT_SPREAD",
    "PUT_CREDIT_DIAGONAL",
    "CALL_CREDIT_DIAGONAL",
]

XSPExitType = Literal[
    "HARVEST",
    "FORCE_CLOSE",
    "ROLL",
    "FLIP",
    "CLOSE",
    "STOP",
]

@dataclass(slots=True)
class XSPTradeRecord:
    trade_id: str
    ticker: str
    structure: str              # XSPStructureType
    opened_utc: str
    closed_utc: str | None

    max_risk: float             # max loss in dollars (spread width × contracts × 100)
    entry_credit: float = 0.0   # credit received on entry
    entry_debit: float  = 0.0   # debit paid on entry

    realized_pnl: float   = 0.0
    exit_type: str | None = None  # XSPExitType

    hold_minutes: int | None  = None
    was_force_closed: bool    = False

    # spread-specific
    profit_capture_pct: float | None = None  # realized / max possible

    # diagonal-specific
    harvest_collected: float  = 0.0   # total short-leg premium harvested
    roll_count: int           = 0     # number of short rolls completed
    roll_credit_total: float  = 0.0   # total roll credits collected
    flip_count: int           = 0     # number of covered flips executed
    flip_realized_value: float= 0.0   # total intrinsic banked via flips
    long_leg_sale_value: float= 0.0   # proceeds when long leg closed

    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class XSPPerformanceSummary:
    # Global
    total_trades: int   = 0
    spread_trades: int  = 0
    diagonal_trades: int= 0
    win_rate: float     = 0.0
    avg_realized_pnl: float     = 0.0
    avg_return_on_risk: float   = 0.0
    total_realized_pnl: float   = 0.0

    # Spreads
    spread_win_rate: float           = 0.0
    avg_spread_profit_capture: float = 0.0
    spread_force_close_rate: float   = 0.0

    # Diagonals
    diagonal_win_rate: float         = 0.0
    avg_diagonal_harvest: float      = 0.0
    avg_roll_count: float            = 0.0
    roll_success_rate: float         = 0.0
    avg_flip_realized_value: float   = 0.0
    diagonal_force_close_rate: float = 0.0

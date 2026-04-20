"""performance/xsp_performance_models.py — XSP spread performance data models."""
from dataclasses import dataclass, field
from datetime import date

@dataclass(slots=True)
class XSPTradeRecord:
    trade_id: str
    ticker: str
    structure: str
    entry_date: str
    close_date: str
    entry_credit_debit: float   # positive = credit, negative = debit
    close_debit_credit: float   # positive = credit received on close, negative = cost
    max_loss: float
    contracts: int
    close_reason: str           # HARVEST | FORCE_CLOSE | STOP
    realized_pnl: float         # dollars
    profit_capture_pct: float   # realized / max possible

@dataclass
class XSPPerformanceSummary:
    total_trades: int       = 0
    wins: int               = 0
    losses: int             = 0
    win_rate: float         = 0.0
    avg_realized_pnl: float = 0.0
    avg_return_on_risk: float = 0.0
    avg_profit_capture_pct: float = 0.0
    force_close_rate: float = 0.0
    total_realized_pnl: float = 0.0

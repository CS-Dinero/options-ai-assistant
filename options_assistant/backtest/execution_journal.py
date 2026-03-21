"""
backtest/execution_journal.py
Tracks trades from engine selection → entry fill → management → exit.

This is the discipline layer: compares what the engine selected vs what
you actually entered, how you filled, how you managed, and realized P&L
vs model expectations.

Event stages: selected → entered → adjusted → exited | skipped | canceled
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


JOURNAL_HEADERS = [
    "timestamp", "journal_id", "run_id",
    "symbol", "strategy", "side_bias",
    "event_stage", "status",
    "engine_decision", "engine_score",
    "vga_environment", "regime_name", "regime_confidence",
    "short_strike", "long_strike", "short_dte", "long_dte",
    "planned_contracts", "actual_contracts",
    "entry_credit_expected", "entry_debit_expected",
    "entry_fill", "entry_fill_type",
    "target_exit_expected", "stop_level_expected",
    "exit_fill", "exit_reason",
    "fees", "slippage",
    "model_max_profit", "model_max_loss",
    "risk_dollars_planned", "risk_dollars_realized",
    "realized_pnl", "variance_vs_model",
    "notes",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        if v in (None, "", "—", "Open"):
            return d
        if isinstance(v, str):
            v = v.replace("$", "").replace(",", "").strip()
        return float(v)
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "") else d
    except (TypeError, ValueError):
        return d


def _cloud_path(path: str) -> str:
    if os.path.exists("/mount/src"):
        return f"/tmp/options_ai_logs/{Path(path).name}"
    return path


def _init(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=JOURNAL_HEADERS).writeheader()


@dataclass
class JournalEntry:
    timestamp:              str
    journal_id:             str
    run_id:                 str
    symbol:                 str
    strategy:               str
    side_bias:              str   = ""
    event_stage:            str   = "selected"
    status:                 str   = "pending"
    engine_decision:        str   = ""
    engine_score:           float = 0.0
    vga_environment:        str   = ""
    regime_name:            str   = ""
    regime_confidence:      float = 0.0
    short_strike:           float = 0.0
    long_strike:            float = 0.0
    short_dte:              int   = 0
    long_dte:               int   = 0
    planned_contracts:      int   = 0
    actual_contracts:       int   = 0
    entry_credit_expected:  float = 0.0
    entry_debit_expected:   float = 0.0
    entry_fill:             float = 0.0
    entry_fill_type:        str   = ""
    target_exit_expected:   float = 0.0
    stop_level_expected:    float = 0.0
    exit_fill:              float = 0.0
    exit_reason:            str   = ""
    fees:                   float = 0.0
    slippage:               float = 0.0
    model_max_profit:       float = 0.0
    model_max_loss:         float = 0.0
    risk_dollars_planned:   float = 0.0
    risk_dollars_realized:  float = 0.0
    realized_pnl:           float = 0.0
    variance_vs_model:      float = 0.0
    notes:                  str   = ""


class ExecutionJournal:
    def __init__(self, path: str = "logs/execution_journal.csv") -> None:
        self.path = _cloud_path(path)
        _init(self.path)

    def _write(self, entry: JournalEntry) -> None:
        row = {h: getattr(entry, h, "") for h in JOURNAL_HEADERS}
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=JOURNAL_HEADERS).writerow(row)

    def log_selected_trade(
        self, *, run_id: str, trade: dict[str, Any],
        journal_id: str | None = None, notes: str = "",
    ) -> str:
        jid = journal_id or self.make_id(
            str(trade.get("symbol", "")),
            str(trade.get("strategy_type", trade.get("strategy", "")))
        )
        entry_c = _sf(trade.get("entry_debit_credit"))
        is_credit = entry_c > 0
        ml = _sf(trade.get("max_loss"))
        self._write(JournalEntry(
            timestamp=_ts(), journal_id=jid, run_id=run_id,
            symbol=str(trade.get("symbol", "")),
            strategy=str(trade.get("strategy_type", trade.get("strategy", ""))),
            side_bias=str(trade.get("direction", "")),
            event_stage="selected", status="pending",
            engine_decision=str(trade.get("decision", "")),
            engine_score=_sf(trade.get("confidence_score", trade.get("score"))),
            vga_environment=str(trade.get("vga_environment", trade.get("environment_label", ""))),
            regime_name=str(trade.get("regime_name", "")),
            regime_confidence=_sf(trade.get("regime_confidence")),
            short_strike=_sf(trade.get("short_strike")),
            long_strike=_sf(trade.get("long_strike")),
            short_dte=_si(trade.get("short_dte")),
            long_dte=_si(trade.get("long_dte")),
            planned_contracts=_si(trade.get("contracts")),
            entry_credit_expected=entry_c if is_credit else 0.0,
            entry_debit_expected=abs(entry_c) if not is_credit else 0.0,
            target_exit_expected=_sf(trade.get("target_exit_value")),
            stop_level_expected=_sf(trade.get("stop_value")),
            model_max_profit=_sf(trade.get("max_profit")),
            model_max_loss=ml,
            risk_dollars_planned=ml,
            notes=notes,
        ))
        return jid

    def log_entry_fill(
        self, *, run_id: str, journal_id: str, symbol: str, strategy: str,
        actual_contracts: int, entry_fill: float, entry_fill_type: str,
        entry_credit_expected: float = 0.0, entry_debit_expected: float = 0.0,
        model_max_loss: float = 0.0, notes: str = "",
    ) -> None:
        expected = entry_credit_expected or entry_debit_expected
        slippage = round(entry_fill - expected, 4) if expected else 0.0
        self._write(JournalEntry(
            timestamp=_ts(), journal_id=journal_id, run_id=run_id,
            symbol=symbol, strategy=strategy,
            event_stage="entered", status="open",
            actual_contracts=actual_contracts,
            entry_credit_expected=entry_credit_expected,
            entry_debit_expected=entry_debit_expected,
            entry_fill=entry_fill, entry_fill_type=entry_fill_type,
            slippage=slippage, model_max_loss=model_max_loss,
            risk_dollars_planned=model_max_loss, notes=notes,
        ))

    def log_exit(
        self, *, run_id: str, journal_id: str, symbol: str, strategy: str,
        actual_contracts: int, entry_fill: float, exit_fill: float,
        exit_reason: str, fees: float = 0.0,
        model_max_profit: float = 0.0, model_max_loss: float = 0.0,
        is_credit: bool = True, notes: str = "",
    ) -> None:
        gross = (entry_fill - exit_fill) if is_credit else (exit_fill - entry_fill)
        pnl   = round(gross * 100 * actual_contracts - fees, 2)
        ref   = model_max_profit if pnl >= 0 else -abs(model_max_loss)
        self._write(JournalEntry(
            timestamp=_ts(), journal_id=journal_id, run_id=run_id,
            symbol=symbol, strategy=strategy,
            event_stage="exited", status="closed",
            actual_contracts=actual_contracts,
            entry_fill=entry_fill, exit_fill=exit_fill,
            exit_reason=exit_reason, fees=fees,
            model_max_profit=model_max_profit, model_max_loss=model_max_loss,
            risk_dollars_realized=abs(model_max_loss),
            realized_pnl=pnl, variance_vs_model=round(pnl - ref, 2),
            notes=notes,
        ))

    def log_skipped(self, *, run_id: str, symbol: str, strategy: str, reason: str) -> str:
        jid = self.make_id(symbol, strategy)
        self._write(JournalEntry(
            timestamp=_ts(), journal_id=jid, run_id=run_id,
            symbol=symbol, strategy=strategy,
            event_stage="selected", status="skipped", notes=reason,
        ))
        return jid

    @staticmethod
    def make_id(symbol: str, strategy: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{symbol}_{strategy}_{ts}"

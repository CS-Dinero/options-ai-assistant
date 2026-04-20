"""
backtest/backtest_logger.py
Structured event logger for the portfolio engine.

Records every ranked trade, selected trade, rejected trade, position
monitor action, and portfolio run summary into two CSV files:
  logs/backtest_events.csv   — every individual event
  logs/backtest_runs.csv     — one row per portfolio run

This is the raw material for metrics_reader.py analytics:
  win rate, expectancy, rejection diagnostics, regime performance.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVENT_HEADERS = [
    "timestamp", "run_id", "event_type",
    "symbol", "strategy", "decision", "action",
    "score", "vga_environment", "regime_name", "regime_confidence",
    "spot", "expected_move", "upper_em", "lower_em",
    "short_strike", "long_strike", "short_dte", "long_dte",
    "entry_credit", "entry_debit",
    "current_debit_to_close", "current_value",
    "max_profit", "max_loss", "target_exit", "stop_level",
    "contracts", "risk_dollars", "pnl_estimate",
    "reject_reason", "notes", "payload_json",
]

SUMMARY_HEADERS = [
    "run_id", "timestamp",
    "symbols_processed", "total_ranked_trades", "selected_trades",
    "rejected_trades", "total_open_positions",
    "portfolio_risk_budget", "portfolio_risk_used", "portfolio_risk_remaining",
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


def _js(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def _init_csv(path: str, headers: list[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=headers).writeheader()


class BacktestLogger:
    def __init__(
        self,
        events_path:  str = "logs/backtest_events.csv",
        summary_path: str = "logs/backtest_runs.csv",
    ) -> None:
        # Cloud-safe path
        if os.path.exists("/mount/src"):
            events_path  = "/tmp/options_ai_logs/backtest_events.csv"
            summary_path = "/tmp/options_ai_logs/backtest_runs.csv"
        self.events_path  = events_path
        self.summary_path = summary_path
        _init_csv(events_path,  EVENT_HEADERS)
        _init_csv(summary_path, SUMMARY_HEADERS)

    def _append(self, path: str, headers: list[str], row: dict[str, Any]) -> None:
        payload = {h: row.get(h, "") for h in headers}
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=headers).writerow(payload)

    def _event(
        self,
        run_id:     str,
        event_type: str,
        symbol:     str,
        strategy:   str = "",
        decision:   str = "",
        action:     str = "",
        score:      float = 0.0,
        vga:        str = "",
        regime:     str = "",
        reg_conf:   float = 0.0,
        spot:       float = 0.0,
        em:         float = 0.0,
        upper_em:   float = 0.0,
        lower_em:   float = 0.0,
        short_k:    float = 0.0,
        long_k:     float = 0.0,
        short_dte:  int   = 0,
        long_dte:   int   = 0,
        credit:     float = 0.0,
        debit:      float = 0.0,
        cur_dtc:    float = 0.0,
        cur_val:    float = 0.0,
        max_profit: float = 0.0,
        max_loss:   float = 0.0,
        target:     float = 0.0,
        stop:       float = 0.0,
        contracts:  int   = 0,
        risk:       float = 0.0,
        pnl:        float = 0.0,
        reject:     str   = "",
        notes:      str   = "",
        payload:    Any   = None,
    ) -> None:
        self._append(self.events_path, EVENT_HEADERS, {
            "timestamp": _ts(), "run_id": run_id, "event_type": event_type,
            "symbol": symbol, "strategy": strategy, "decision": decision, "action": action,
            "score": score, "vga_environment": vga, "regime_name": regime, "regime_confidence": reg_conf,
            "spot": spot, "expected_move": em, "upper_em": upper_em, "lower_em": lower_em,
            "short_strike": short_k, "long_strike": long_k, "short_dte": short_dte, "long_dte": long_dte,
            "entry_credit": credit, "entry_debit": debit,
            "current_debit_to_close": cur_dtc, "current_value": cur_val,
            "max_profit": max_profit, "max_loss": max_loss, "target_exit": target, "stop_level": stop,
            "contracts": contracts, "risk_dollars": risk, "pnl_estimate": pnl,
            "reject_reason": reject, "notes": notes,
            "payload_json": _js(payload),
        })

    def log_ranked_trade(
        self, *, run_id: str, symbol: str, vga: str, regime: str,
        reg_conf: float, meta: dict[str, Any], trade: dict[str, Any],
    ) -> None:
        risk = _sf(trade.get("max_loss"))
        self._event(
            run_id=run_id, event_type="ranked_trade", symbol=symbol,
            strategy=str(trade.get("strategy_type", trade.get("strategy", ""))),
            decision=str(trade.get("decision", "")),
            score=_sf(trade.get("confidence_score", trade.get("score"))),
            vga=vga, regime=regime, reg_conf=reg_conf,
            spot=_sf(meta.get("spot_price")),
            em=_sf(trade.get("expected_move") or meta.get("expected_move")),
            upper_em=_sf(meta.get("upper_em")), lower_em=_sf(meta.get("lower_em")),
            short_k=_sf(trade.get("short_strike")), long_k=_sf(trade.get("long_strike")),
            short_dte=_si(trade.get("short_dte")), long_dte=_si(trade.get("long_dte")),
            credit=_sf(trade.get("entry_debit_credit")) if _sf(trade.get("entry_debit_credit")) > 0 else 0,
            debit=abs(_sf(trade.get("entry_debit_credit"))) if _sf(trade.get("entry_debit_credit")) < 0 else 0,
            max_loss=_sf(trade.get("max_loss")), max_profit=_sf(trade.get("max_profit")),
            target=_sf(trade.get("target_exit_value")), stop=_sf(trade.get("stop_value")),
            contracts=_si(trade.get("contracts")), risk=risk,
            notes=str(trade.get("notes", "")), payload=trade,
        )

    def log_selected_trade(self, *, run_id: str, trade: dict[str, Any]) -> None:
        risk = _sf(trade.get("_risk") or trade.get("max_loss"))
        self._event(
            run_id=run_id, event_type="selected_trade",
            symbol=str(trade.get("symbol", "")),
            strategy=str(trade.get("strategy_type", trade.get("strategy", ""))),
            decision=str(trade.get("decision", "")),
            score=_sf(trade.get("confidence_score", trade.get("score"))),
            vga=str(trade.get("vga_environment", trade.get("environment_label", ""))),
            regime=str(trade.get("regime_name", "")),
            reg_conf=_sf(trade.get("regime_confidence")),
            short_k=_sf(trade.get("short_strike")), long_k=_sf(trade.get("long_strike")),
            short_dte=_si(trade.get("short_dte")), long_dte=_si(trade.get("long_dte")),
            max_loss=_sf(trade.get("max_loss")), max_profit=_sf(trade.get("max_profit")),
            contracts=_si(trade.get("contracts")), risk=risk,
            notes=str(trade.get("notes", "")), payload=trade,
        )

    def log_rejected_trade(self, *, run_id: str, trade: dict[str, Any]) -> None:
        self._event(
            run_id=run_id, event_type="rejected_trade",
            symbol=str(trade.get("symbol", "")),
            strategy=str(trade.get("strategy_type", trade.get("strategy", ""))),
            decision=str(trade.get("decision", "")),
            score=_sf(trade.get("confidence_score", trade.get("score"))),
            vga=str(trade.get("vga_environment", trade.get("environment_label", ""))),
            reject=str(trade.get("_reject_reason", "")),
            max_loss=_sf(trade.get("max_loss")),
            risk=_sf(trade.get("_risk") or trade.get("max_loss")),
            payload=trade,
        )

    def log_position_action(self, *, run_id: str, pos: dict[str, Any]) -> None:
        decision = pos.get("decision", {})
        if not isinstance(decision, dict):
            decision = {}
        credit  = _sf(pos.get("entry_debit_credit") or pos.get("entry_price"))
        cur_val = _sf(pos.get("current_value"))
        pnl     = round((abs(credit) - cur_val) * 100, 2) if credit and cur_val else 0.0
        self._event(
            run_id=run_id, event_type="position_action",
            symbol=str(pos.get("symbol", "")),
            strategy=str(pos.get("strategy_type", "")),
            action=str(decision.get("action", "")),
            spot=_sf(pos.get("live_spot")),
            short_k=_sf(pos.get("short_strike")), long_k=_sf(pos.get("long_strike")),
            short_dte=_si(pos.get("short_dte")), long_dte=_si(pos.get("long_dte")),
            cur_val=cur_val, pnl=pnl, payload=pos,
        )

    def log_portfolio_run(self, *, run_id: str, portfolio_output: dict[str, Any]) -> None:
        meta = portfolio_output.get("portfolio_meta", {})
        self._append(self.summary_path, SUMMARY_HEADERS, {
            "run_id":                   run_id,
            "timestamp":                _ts(),
            "symbols_processed":        meta.get("symbols_processed", 0),
            "total_ranked_trades":      meta.get("total_ranked_trades", 0),
            "selected_trades":          meta.get("selected_trades", 0),
            "rejected_trades":          meta.get("rejected_trades", 0),
            "total_open_positions":     meta.get("total_open_positions", 0),
            "portfolio_risk_budget":    meta.get("portfolio_risk_budget", 0),
            "portfolio_risk_used":      meta.get("portfolio_risk_used", 0),
            "portfolio_risk_remaining": meta.get("portfolio_risk_remaining", 0),
        })

    def log_full_portfolio_output(
        self, *, run_id: str, portfolio_output: dict[str, Any]
    ) -> None:
        self.log_portfolio_run(run_id=run_id, portfolio_output=portfolio_output)

        for sym_block in portfolio_output.get("symbols", []):
            engine  = sym_block.get("engine_output", {})
            sym     = sym_block.get("symbol", engine.get("market", {}).get("symbol", ""))
            vga     = engine.get("vga", "mixed")
            regime  = engine.get("regime", {})
            reg_name = regime.get("regime", vga)
            reg_conf = _sf(regime.get("confidence"))
            meta     = engine.get("market", {})

            for t in engine.get("candidates", []):
                self.log_ranked_trade(
                    run_id=run_id, symbol=sym, vga=vga, regime=reg_name,
                    reg_conf=reg_conf, meta=meta, trade=t,
                )

            positions = engine.get("positions", {})
            for p in positions.get("calendar_diagonal", []):
                self.log_position_action(run_id=run_id, pos=p)
            for p in positions.get("credit_spreads", []):
                self.log_position_action(run_id=run_id, pos=p)

        alloc = portfolio_output.get("allocation", {})
        for t in alloc.get("selected_trades", []):
            self.log_selected_trade(run_id=run_id, trade=t)
        for t in alloc.get("rejected_trades", []):
            self.log_rejected_trade(run_id=run_id, trade=t)

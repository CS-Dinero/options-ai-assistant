"""
engines/portfolio_runner.py
Multi-symbol portfolio orchestration — single entry point.

Call:
    output = run_portfolio_engine(symbol_payloads, ...)

Output keys:
    run_id, portfolio_meta, allocation, symbols,
    alerts, roll_suggestions (cross-symbol summary)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from engines.engine_orchestrator import run_options_engine
from engines.portfolio_allocator import (
    AllocationConfig, allocate_portfolio, enrich_trade_for_allocation,
)
from engines.roll_manager import build_roll_suggestions
from engines.alert_router import collect_portfolio_alerts


def _cfg(path: str) -> dict[str, Any]:
    for p in [path, str(Path(__file__).parent.parent / "config" / "config.yaml")]:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            continue
    return {"risk": {}}


def _run_id(prefix: str = "portfolio") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _alloc_cfg(risk: dict[str, Any]) -> AllocationConfig:
    return AllocationConfig(
        account_size=float(risk.get("account_size", 200_000)),
        max_total_portfolio_risk_pct=float(risk.get("max_total_portfolio_risk_pct", 0.03)),
        max_symbol_risk_pct=float(risk.get("max_symbol_risk_pct", 0.02)),
        max_trade_risk_pct=float(risk.get("max_trade_risk_pct", 0.01)),
        max_symbols=int(risk.get("max_symbols", 3)),
        max_trades_per_symbol=int(risk.get("max_trades_per_symbol", 2)),
        allow_both_sides_same_symbol=bool(risk.get("allow_both_sides_same_symbol", True)),
        reserve_for_calendars_pct=float(risk.get("reserve_for_calendars_pct", 0.25)),
        calendar_min_score_gate=float(risk.get("calendar_min_score_gate",
                                               risk.get("calendar_min_score_bonus_gate", 78.0))),
        min_trade_score=float(risk.get("allocation_min_trade_score", 75.0)),
    )


def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def run_portfolio_engine(
    symbol_payloads:        list[dict[str, Any]],
    *,
    config_path:            str           = "config/config.yaml",
    log_backtest_events:    bool          = False,
    backtest_events_path:   str           = "logs/backtest_events.csv",
    backtest_summary_path:  str           = "logs/backtest_runs.csv",
    log_execution_journal:  bool          = False,
    execution_journal_path: str           = "logs/execution_journal.csv",
    log_alerts:             bool          = False,
    alerts_path:            str           = "logs/alerts.csv",
    log_rolls:              bool          = False,
    rolls_path:             str           = "logs/roll_suggestions.csv",
    persist_state:          bool          = False,
    state_dir:              str           = "state",
    snapshot_history:       bool          = False,
    snapshots_dir:          str           = "snapshots",
    run_id:                 str | None    = None,
) -> dict[str, Any]:
    """
    Run full portfolio engine: per-symbol → allocate → roll → alert.

    Each symbol_payload:
      symbol, market (or report), chain (or chain_rows),
      derived (optional), open_positions (optional)
    """
    cfg           = _cfg(config_path)
    alloc_cfg     = _alloc_cfg(cfg.get("risk", {}))
    active_run_id = run_id or _run_id()

    symbol_results:    list[dict[str, Any]] = []
    allocation_inputs: list[dict[str, Any]] = []
    all_roll_inputs:   list[dict[str, Any]] = []

    # ── Per-symbol pass ───────────────────────────────────────────────────────
    for payload in symbol_payloads:
        sym      = payload.get("symbol", "")
        market   = payload.get("market",  payload.get("report", {}))
        chain    = payload.get("chain",   payload.get("chain_rows", []))
        derived  = payload.get("derived")
        positions = payload.get("open_positions")

        result = run_options_engine(
            market=market, chain=chain, derived=derived,
            open_positions=positions,
            risk_dollars=cfg.get("risk", {}).get("preferred_risk_dollars"),
        )

        # Build roll suggestions from all open positions
        pos_snap = result.get("positions", {})
        all_open = (
            pos_snap.get("calendar_diagonal", []) +
            pos_snap.get("credit_spreads", []) +
            pos_snap.get("debit_spreads", [])
        )
        rolls = build_roll_suggestions(all_open)
        result["roll_suggestions"] = rolls
        all_roll_inputs.extend(rolls)

        # Enrich candidates for portfolio allocation
        vga      = result.get("vga", "mixed")
        regime   = result.get("regime", {})
        reg_name = regime.get("regime", vga)
        reg_conf = float(regime.get("confidence", 0.0))

        for c in result.get("candidates", []):
            allocation_inputs.append(
                enrich_trade_for_allocation(c, sym, vga, reg_name, reg_conf)
            )

        symbol_results.append({"symbol": sym, "engine_output": result})

    # ── Allocation ────────────────────────────────────────────────────────────
    allocation = allocate_portfolio(allocation_inputs, alloc_cfg)

    # ── Portfolio output ──────────────────────────────────────────────────────
    total_ranked = sum(len(s["engine_output"].get("candidates", [])) for s in symbol_results)
    total_pos    = sum(
        s["engine_output"].get("positions", {}).get("total_open", 0)
        for s in symbol_results
    )

    portfolio_meta = {
        "run_id":                   active_run_id,
        "symbols_processed":        len(symbol_results),
        "total_ranked_trades":      total_ranked,
        "total_open_positions":     total_pos,
        "selected_trades":          len(allocation.selected_trades),
        "rejected_trades":          len(allocation.rejected_trades),
        "total_roll_suggestions":   len(all_roll_inputs),
        "portfolio_risk_budget":    allocation.total_risk_budget,
        "portfolio_risk_used":      allocation.used_risk_budget,
        "portfolio_risk_remaining": allocation.remaining_risk_budget,
    }

    output: dict[str, Any] = {
        "run_id":           active_run_id,
        "portfolio_meta":   portfolio_meta,
        "allocation":       allocation.to_dict(),
        "symbols":          symbol_results,
        "roll_suggestions": all_roll_inputs,
    }

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts     = collect_portfolio_alerts(output)
    alert_dicts = [a.to_dict() for a in alerts]
    output["alerts"] = alert_dicts

    # ── Optional logging ──────────────────────────────────────────────────────
    if log_backtest_events:
        try:
            from backtest.backtest_logger import BacktestLogger
            BacktestLogger(
                events_path=_cloud(backtest_events_path),
                summary_path=_cloud(backtest_summary_path),
            ).log_full_portfolio_output(run_id=active_run_id, portfolio_output=output)
        except Exception:
            pass

    if log_execution_journal:
        try:
            from backtest.execution_journal import ExecutionJournal
            ej = ExecutionJournal(path=_cloud(execution_journal_path))
            for t in allocation.selected_trades:
                ej.log_selected_trade(run_id=active_run_id, trade=t)
        except Exception:
            pass

    if log_alerts and alert_dicts:
        try:
            from engines.alert_logger import AlertLogger
            AlertLogger(path=_cloud(alerts_path)).append_many(alert_dicts)
        except Exception:
            pass

    if log_rolls and all_roll_inputs:
        try:
            from engines.roll_logger import RollLogger
            RollLogger(path=_cloud(rolls_path)).append_many(all_roll_inputs)
        except Exception:
            pass

    # ── State persistence ─────────────────────────────────────────────────────
    if persist_state:
        try:
            from engines.state_store import StateStore
            store = StateStore(base_dir=state_dir)
            store.save_portfolio_state(output, metadata={"run_id": active_run_id})
            store.save_alerts_state({"alerts": alert_dicts}, metadata={"run_id": active_run_id})
            for sym_block in symbol_results:
                sym = sym_block["symbol"]
                store.save_named_snapshot(
                    f"engine_state_{sym}",
                    sym_block["engine_output"],
                    metadata={"run_id": active_run_id, "symbol": sym},
                )
        except Exception:
            pass

    # ── Snapshot history ──────────────────────────────────────────────────────
    if snapshot_history:
        try:
            from engines.snapshot_manager import SnapshotManager
            snap = SnapshotManager(base_dir=snapshots_dir)
            snap.save_snapshot(category="portfolio", name=f"portfolio_{active_run_id}",
                               payload=output, metadata={"run_id": active_run_id})
            snap.save_snapshot(category="alerts", name=f"alerts_{active_run_id}",
                               payload={"alerts": alert_dicts}, metadata={"run_id": active_run_id})
            for sym_block in symbol_results:
                sym = sym_block["symbol"]
                snap.save_snapshot(category="engine", name=f"{sym}_{active_run_id}",
                                   payload=sym_block["engine_output"],
                                   metadata={"run_id": active_run_id, "symbol": sym})
        except Exception:
            pass

    return output

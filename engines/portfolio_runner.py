"""
engines/portfolio_runner.py
Multi-symbol portfolio orchestration — single entry point for running
the full engine across 2-4 symbols, allocating portfolio risk, and
packaging a unified dashboard payload.

Usage:
    from engines.portfolio_runner import run_portfolio_engine
    output = run_portfolio_engine(symbol_payloads, config_path="config/config.yaml")
    # output["portfolio_meta"]  → top-line counts
    # output["allocation"]      → AllocationDecision dict
    # output["symbols"]         → per-symbol engine results
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from engines.engine_orchestrator import run_options_engine
from engines.portfolio_allocator import (
    AllocationConfig, AllocationDecision,
    allocate_portfolio, enrich_trade_for_allocation,
)


def _load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_run_id(prefix: str = "portfolio") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}"


def _build_alloc_config(risk: dict[str, Any]) -> AllocationConfig:
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


def run_portfolio_engine(
    symbol_payloads:       list[dict[str, Any]],
    *,
    config_path:           str            = "config/config.yaml",
    log_backtest_events:   bool           = False,
    backtest_events_path:  str            = "logs/backtest_events.csv",
    backtest_summary_path: str            = "logs/backtest_runs.csv",
    run_id:                str | None     = None,
) -> dict[str, Any]:
    """
    Run the full options engine across multiple symbols + allocate portfolio risk.

    Each payload in symbol_payloads:
    {
        "symbol":           str,
        "market":           dict,       # normalized market dict
        "chain":            list[dict], # normalized chain rows
        "derived":          dict | None,# optional pre-built derived context
        "open_positions":   list[dict] | None,
    }

    Returns:
    {
        "run_id":         str,
        "portfolio_meta": dict,
        "allocation":     dict,   # AllocationDecision.to_dict()
        "symbols":        list[dict],  # per-symbol engine results
    }
    """
    # Try both YAML config paths (repo root and config/ subdir)
    cfg_path = config_path
    if not os.path.exists(cfg_path):
        cfg_path = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        cfg = _load_config(str(cfg_path))
    except FileNotFoundError:
        cfg = {"risk": {}}   # fallback — use defaults

    alloc_cfg    = _build_alloc_config(cfg.get("risk", {}))
    active_run_id = run_id or _make_run_id()

    symbol_results:    list[dict[str, Any]] = []
    allocation_inputs: list[dict[str, Any]] = []

    # ── Per-symbol engine pass ────────────────────────────────────────────────
    for payload in symbol_payloads:
        sym     = payload.get("symbol", "")
        market  = payload.get("market",  payload.get("report", {}))
        chain   = payload.get("chain",   payload.get("chain_rows", []))
        derived = payload.get("derived")
        positions = payload.get("open_positions")

        result = run_options_engine(
            market=market,
            chain=chain,
            derived=derived,
            open_positions=positions,
            risk_dollars=cfg.get("risk", {}).get("preferred_risk_dollars"),
        )

        # Enrich candidates for portfolio allocation
        vga      = result.get("vga", "mixed")
        regime   = result.get("regime", {})
        reg_name = regime.get("regime", vga)
        reg_conf = float(regime.get("confidence", 0.0))

        for candidate in result.get("candidates", []):
            allocation_inputs.append(
                enrich_trade_for_allocation(candidate, sym, vga, reg_name, reg_conf)
            )

        symbol_results.append({
            "symbol": sym,
            "engine_output": result,
        })

    # ── Portfolio allocation ───────────────────────────────────────────────────
    allocation = allocate_portfolio(allocation_inputs, alloc_cfg)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_ranked   = sum(len(s["engine_output"].get("candidates", [])) for s in symbol_results)
    total_pos_acts = sum(
        s["engine_output"].get("positions", {}).get("total_open", 0)
        for s in symbol_results
    )

    portfolio_meta = {
        "run_id":                  active_run_id,
        "symbols_processed":       len(symbol_results),
        "total_ranked_trades":     total_ranked,
        "total_open_positions":    total_pos_acts,
        "selected_trades":         len(allocation.selected_trades),
        "rejected_trades":         len(allocation.rejected_trades),
        "portfolio_risk_budget":   allocation.total_risk_budget,
        "portfolio_risk_used":     allocation.used_risk_budget,
        "portfolio_risk_remaining": allocation.remaining_risk_budget,
    }

    output = {
        "run_id":         active_run_id,
        "portfolio_meta": portfolio_meta,
        "allocation":     allocation.to_dict(),
        "symbols":        symbol_results,
    }

    # ── Optional backtest event logging ───────────────────────────────────────
    if log_backtest_events:
        _log_portfolio_events(active_run_id, output,
                              backtest_events_path, backtest_summary_path)

    return output


def _log_portfolio_events(
    run_id: str,
    output: dict[str, Any],
    events_path: str,
    summary_path: str,
) -> None:
    """Lazy import to avoid hard dependency on backtest module."""
    try:
        from backtest.backtest_logger import BacktestLogger
        logger = BacktestLogger(events_path=events_path, summary_path=summary_path)
        logger.log_full_portfolio_output(run_id=run_id, portfolio_output=output)
    except Exception:
        pass  # logging failure must never crash the engine

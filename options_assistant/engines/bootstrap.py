"""
engines/bootstrap.py
Seeds a fresh environment: dirs, CSV logs, state JSONs, config, placeholders.

bootstrap_environment() is idempotent — never overwrites existing files.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


DIRS = [
    "logs", "state", "config_backups", "deployment_packets",
    "snapshots", "snapshots/portfolio", "snapshots/engine",
    "snapshots/blotter", "snapshots/alerts",
]

CSV_SEEDS: dict[str, list[str]] = {
    "logs/trades.csv": [
        "timestamp","symbol","strategy","score","decision","bias","spot",
        "upper_em","lower_em","gamma_regime","iv_regime","term_structure",
        "short_strike","long_strike","short_dte","long_dte","entry_credit",
        "entry_debit","max_profit","max_loss","target_exit","stop_level",
        "contracts","rationale",
    ],
    "logs/backtest_events.csv": [
        "timestamp","run_id","event_type","symbol","strategy","decision","action",
        "score","vga_environment","regime_name","regime_confidence","spot",
        "expected_move","upper_em","lower_em","short_strike","long_strike",
        "short_dte","long_dte","entry_credit","entry_debit","current_debit_to_close",
        "current_value","max_profit","max_loss","target_exit","stop_level",
        "contracts","risk_dollars","pnl_estimate","reject_reason","notes","payload_json",
    ],
    "logs/backtest_runs.csv": [
        "run_id","timestamp","symbols_processed","total_ranked_trades",
        "selected_trades","rejected_trades","total_open_positions",
        "portfolio_risk_budget","portfolio_risk_used","portfolio_risk_remaining",
    ],
    "logs/execution_journal.csv": [
        "timestamp","journal_id","run_id","symbol","strategy","side_bias",
        "event_stage","status","engine_decision","engine_score",
        "vga_environment","regime_name","regime_confidence","short_strike",
        "long_strike","short_dte","long_dte","planned_contracts","actual_contracts",
        "entry_credit_expected","entry_debit_expected","entry_fill","entry_fill_type",
        "target_exit_expected","stop_level_expected","exit_fill","exit_reason",
        "fees","slippage","model_max_profit","model_max_loss",
        "risk_dollars_planned","risk_dollars_realized","realized_pnl","variance_vs_model","notes",
    ],
    "logs/release_manifest.csv": [
        "release_id","created_at","release_name","release_type","config_path",
        "config_backup_path","config_version_tag","portfolio_run_id",
        "state_dir","snapshots_dir","audit_path","alerts_path",
        "backtest_runs_path","execution_journal_path","roll_log_path",
        "deployment_packet_path","deployment_packet_zip",
        "health_status","health_summary_json","notes","metadata_json",
    ],
    "logs/change_audit.csv": [
        "timestamp","audit_id","parameter","old_value","new_value",
        "source","source_run_id","reviewer","backup_path","config_path",
        "confidence","direction","rationale","notes",
    ],
    "logs/approval_queue.csv": [
        "request_id","created_at","updated_at","status","parameter","current_value",
        "requested_value","confidence","direction","rationale","evidence_json",
        "governance_status","governance_reason","reviewer","review_notes","source_run_id",
    ],
    "logs/alerts.csv": [
        "timestamp","symbol","alert_type","severity","title","message",
        "action","strategy","run_id",
    ],
    "logs/roll_suggestions.csv": [
        "timestamp","symbol","strategy","action","urgency","current_spot",
        "short_strike","long_strike","short_dte","long_dte","expected_move",
        "target_short_strike","target_long_strike","target_short_dte","target_long_dte",
        "rationale","notes",
    ],
}

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {"name": "Options AI Assistant", "strategy_engine": "EGPE v1.0",
            "symbols": ["SPY","QQQ"]},
    "filters": {"credit_score_threshold": 75, "calendar_score_threshold": 72,
                "min_credit": 0.20, "min_debit": 0.10},
    "credit_spreads": {"short_delta_min": 0.15, "short_delta_max": 0.20,
                       "width_min": 3, "width_max": 10,
                       "take_profit_pct_of_credit": 0.50,
                       "stop_multiple_of_credit": 2.0, "exit_dte": 5},
    "calendar": {"short_dte_min": 7, "short_dte_max": 10, "long_dte_min": 45,
                 "long_dte_max": 60, "long_exit_dte": 35},
    "risk": {"account_size": 200000, "max_risk_per_side_pct": 0.005,
             "max_total_portfolio_risk_pct": 0.03, "max_symbol_risk_pct": 0.02,
             "max_trade_risk_pct": 0.01, "max_symbols": 3, "max_trades_per_symbol": 2,
             "allow_both_sides_same_symbol": True, "reserve_for_calendars_pct": 0.25,
             "calendar_min_score_gate": 78.0, "allocation_min_trade_score": 75.0,
             "preferred_risk_dollars": 500},
    "environment": {"allowed_gamma_regimes": ["POSITIVE"],
                    "allowed_iv_regimes": ["ELEVATED","EXTREME"],
                    "allowed_term_structures": ["FLAT","CONTANGO"]},
}

STATE_SEEDS = {
    "state/latest_engine_state.json":    {"saved_at": None, "metadata": {"seeded": True}, "engine_output": {}},
    "state/latest_portfolio_state.json": {"saved_at": None, "metadata": {"seeded": True}, "portfolio_output": {}},
    "state/latest_blotter_state.json":   {"saved_at": None, "metadata": {"seeded": True}, "blotter": {"summary": {}, "rows": []}},
    "state/latest_alerts_state.json":    {"saved_at": None, "metadata": {"seeded": True}, "alerts": {"alerts": []}},
}


def _cloud_logs() -> str:
    return "/tmp/options_ai_logs" if os.path.exists("/mount/src") else "logs"


def bootstrap_environment(
    *,
    config_path:        str  = "config/config.yaml",
    create_backup_seed: bool = True,
    backup_dir:         str  = "config_backups",
) -> dict[str, Any]:
    """Idempotent — never overwrites existing files."""
    created:  dict[str, list[str]] = {k: [] for k in ("dirs","csvs","state","config","backups","placeholders")}
    existing: dict[str, list[str]] = {k: [] for k in ("dirs","csvs","state","config","backups","placeholders")}

    # Resolve config path
    real_cfg = config_path
    if not os.path.exists(real_cfg):
        fb = str(Path(__file__).parent.parent / "config" / "config.yaml")
        if os.path.exists(fb):
            real_cfg = fb

    logs_dir = _cloud_logs()

    # Dirs
    for d in DIRS:
        if os.path.isdir(d):
            existing["dirs"].append(d)
        else:
            Path(d).mkdir(parents=True, exist_ok=True)
            created["dirs"].append(d)

    # Config
    if os.path.exists(real_cfg):
        existing["config"].append(real_cfg)
    else:
        Path(real_cfg).parent.mkdir(parents=True, exist_ok=True)
        with open(real_cfg, "w", encoding="utf-8") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, sort_keys=False)
        created["config"].append(real_cfg)

    # Config backup seed
    if create_backup_seed and os.path.exists(real_cfg):
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        bk = os.path.join(backup_dir, f"{_slug()}_{Path(real_cfg).name}")
        if not os.path.exists(bk):
            shutil.copy2(real_cfg, bk)
            created["backups"].append(bk)

    # CSVs
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    for rel_path, headers in CSV_SEEDS.items():
        real_path = os.path.join(logs_dir, Path(rel_path).name)
        if os.path.exists(real_path):
            existing["csvs"].append(real_path)
        else:
            with open(real_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=headers).writeheader()
            created["csvs"].append(real_path)

    # State JSONs
    state_base = "/tmp/options_ai_state" if os.path.exists("/mount/src") else "state"
    Path(state_base).mkdir(parents=True, exist_ok=True)
    for rel_path, payload in STATE_SEEDS.items():
        real_path = os.path.join(state_base, Path(rel_path).name)
        if os.path.exists(real_path):
            existing["state"].append(real_path)
        else:
            payload["saved_at"] = _ts()
            with open(real_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            created["state"].append(real_path)

    # Placeholder .keep files
    for placeholder in [
        "snapshots/portfolio/.keep", "snapshots/engine/.keep",
        "snapshots/blotter/.keep",   "snapshots/alerts/.keep",
        "deployment_packets/.keep",  "config_backups/.keep",
    ]:
        if os.path.exists(placeholder):
            existing["placeholders"].append(placeholder)
        else:
            Path(placeholder).parent.mkdir(parents=True, exist_ok=True)
            open(placeholder, "w").close()
            created["placeholders"].append(placeholder)

    total_created  = sum(len(v) for v in created.values())
    total_existing = sum(len(v) for v in existing.values())
    return {
        "bootstrapped_at": _ts(),
        "created":  created,
        "existing": existing,
        "summary":  {"created": total_created, "existing": total_existing},
    }

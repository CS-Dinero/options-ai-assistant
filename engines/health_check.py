"""
engines/health_check.py
System-wide health validator.

run_health_check() → {overall_status, checks, summary, recommendations}
  Checks: config, required fields, directories, required logs,
          optional logs, CSV headers, state/snapshots, pipeline links.

Integrates with deployment_packet and release_manifest.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import yaml


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

REQUIRED_CONFIG_FIELDS = [
    "app.name",
    "filters.credit_score_threshold",
    "filters.calendar_score_threshold",
    "credit_spreads.short_delta_min",
    "credit_spreads.short_delta_max",
    "risk.account_size",
    "risk.max_total_portfolio_risk_pct",
    "risk.max_symbol_risk_pct",
    "risk.max_trade_risk_pct",
]

REQUIRED_DIRS = [
    "logs", "state", "snapshots", "config_backups", "deployment_packets",
]

REQUIRED_LOGS = [
    "logs/trades.csv", "logs/backtest_events.csv", "logs/backtest_runs.csv",
    "logs/execution_journal.csv",
]

OPTIONAL_LOGS = [
    "logs/approval_queue.csv", "logs/change_audit.csv",
    "logs/alerts.csv", "logs/roll_suggestions.csv",
    "logs/release_manifest.csv",
]

CSV_HEADER_EXPECTATIONS: dict[str, list[str]] = {
    "logs/backtest_events.csv":  ["timestamp","run_id","event_type","symbol"],
    "logs/execution_journal.csv":["timestamp","journal_id","run_id","symbol","strategy"],
    "logs/backtest_runs.csv":    ["run_id","timestamp"],
}


# ─────────────────────────────────────────────
# DATA CLASS
# ─────────────────────────────────────────────

@dataclass
class CheckResult:
    name:    str
    status:  str      # PASS | WARN | FAIL
    message: str
    details: dict[str, Any]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _cloud_adjust(path: str) -> str:
    """Map local paths to /tmp equivalents on Streamlit Cloud."""
    if not os.path.exists("/mount/src"):
        return path
    p = Path(path)
    if str(p).startswith("logs/"):
        return f"/tmp/options_ai_logs/{p.name}"
    if str(p).startswith("state/"):
        return f"/tmp/options_ai_state/{p.name}"
    if str(p).startswith("snapshots/"):
        return f"/tmp/options_ai_snapshots/{p.relative_to('snapshots')}"
    return path


def _deep_get(cfg: dict, dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _find_config(p: str) -> str:
    if os.path.exists(p):
        return p
    fb = str(Path(__file__).parent.parent / "config" / "config.yaml")
    return fb if os.path.exists(fb) else p


def _writable(path: str) -> bool:
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        test = os.path.join(path, ".hc_tmp")
        open(test, "w").close()
        os.remove(test)
        return True
    except Exception:
        return False


def _csv_headers(path: str) -> list[str]:
    real = _cloud_adjust(path)
    if not os.path.exists(real):
        return []
    try:
        with open(real, "r", newline="", encoding="utf-8") as f:
            return next(csv.reader(f), [])
    except Exception:
        return []


# ─────────────────────────────────────────────
# INDIVIDUAL CHECKS
# ─────────────────────────────────────────────

def check_config_exists(config_path: str) -> CheckResult:
    real = _find_config(config_path)
    exists = os.path.exists(real)
    return CheckResult("config_exists",
                       "PASS" if exists else "FAIL",
                       f"Config {'found' if exists else 'missing'}: {real}",
                       {"config_path": real})


def check_config_fields(config_path: str) -> CheckResult:
    real = _find_config(config_path)
    if not os.path.exists(real):
        return CheckResult("config_fields","FAIL","Config file missing.",{})
    with open(real,"r",encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    missing = [p for p in REQUIRED_CONFIG_FIELDS if _deep_get(cfg, p) is None]
    status  = "FAIL" if missing else "PASS"
    msg     = f"{len(missing)} required field(s) missing." if missing else "All required fields present."
    return CheckResult("config_fields", status, msg, {"missing": missing})


def check_directories() -> CheckResult:
    missing = [d for d in REQUIRED_DIRS if not os.path.isdir(d)]
    unwr    = [d for d in REQUIRED_DIRS if os.path.isdir(d) and not _writable(d)]
    if missing:
        return CheckResult("directories","FAIL","Required dirs missing.",{"missing":missing})
    if unwr:
        return CheckResult("directories","WARN","Some dirs not writable.",{"unwritable":unwr})
    return CheckResult("directories","PASS","All dirs present and writable.",{"checked":REQUIRED_DIRS})


def check_required_logs() -> CheckResult:
    missing = [p for p in REQUIRED_LOGS if not os.path.exists(_cloud_adjust(p))]
    status  = "WARN" if missing else "PASS"
    msg     = f"{len(missing)} required log(s) missing." if missing else "Required logs present."
    return CheckResult("required_logs", status, msg, {"missing": missing})


def check_optional_logs() -> CheckResult:
    missing = [p for p in OPTIONAL_LOGS if not os.path.exists(_cloud_adjust(p))]
    status  = "WARN" if missing else "PASS"
    msg     = f"{len(missing)} optional log(s) missing." if missing else "Optional logs present."
    return CheckResult("optional_logs", status, msg, {"missing": missing})


def check_csv_headers() -> CheckResult:
    problems = []
    for path, expected in CSV_HEADER_EXPECTATIONS.items():
        actual  = _csv_headers(path)
        if not actual:
            continue
        missing = [h for h in expected if h not in actual]
        if missing:
            problems.append({"path": path, "missing": missing})
    if problems:
        return CheckResult("csv_headers","WARN","CSV header issues found.",{"problems":problems})
    return CheckResult("csv_headers","PASS","CSV headers look valid.",
                       {"checked": list(CSV_HEADER_EXPECTATIONS.keys())})


def check_state_snapshots() -> CheckResult:
    state_files = [
        "state/latest_portfolio_state.json", "state/latest_engine_state.json",
        "state/latest_alerts_state.json",    "state/latest_blotter_state.json",
    ]
    snap_dirs   = ["snapshots/portfolio","snapshots/engine",
                   "snapshots/blotter","snapshots/alerts"]
    miss_s = [p for p in state_files if not os.path.exists(_cloud_adjust(p))]
    miss_d = [p for p in snap_dirs   if not os.path.isdir(p)]
    if miss_s or miss_d:
        return CheckResult("state_snapshots","WARN","State/snapshot files incomplete.",
                           {"missing_state":miss_s,"missing_dirs":miss_d})
    return CheckResult("state_snapshots","PASS","State and snapshot structure present.",{})


def check_pipeline_links() -> CheckResult:
    links = {
        "release_manifest": os.path.exists(_cloud_adjust("logs/release_manifest.csv")),
        "change_audit":     os.path.exists(_cloud_adjust("logs/change_audit.csv")),
        "approval_queue":   os.path.exists(_cloud_adjust("logs/approval_queue.csv")),
        "deployment_packets": os.path.isdir("deployment_packets"),
        "config_backups":   os.path.isdir("config_backups"),
    }
    missing = [k for k,v in links.items() if not v]
    if missing:
        return CheckResult("pipeline_links","WARN","Some governance pipeline links inactive.",
                           {"missing":missing,"links":links})
    return CheckResult("pipeline_links","PASS","All pipeline links connected.",{"links":links})


# ─────────────────────────────────────────────
# MASTER RUNNER
# ─────────────────────────────────────────────

def run_health_check(config_path: str = "config/config.yaml") -> dict[str, Any]:
    checks = [
        check_config_exists(config_path),
        check_config_fields(config_path),
        check_directories(),
        check_required_logs(),
        check_optional_logs(),
        check_csv_headers(),
        check_state_snapshots(),
        check_pipeline_links(),
    ]
    rank    = {"PASS":0,"WARN":1,"FAIL":2}
    overall = max(checks, key=lambda c: rank[c.status]).status

    recs: list[str] = []
    if overall != "PASS":
        recs.append("Run bootstrap to seed missing folders, logs, and state files.")
    if any(c.name == "config_fields" and c.status == "FAIL" for c in checks):
        recs.append("Restore or reseed config.yaml before running the engine.")
    if any(c.name == "directories" and c.status == "FAIL" for c in checks):
        recs.append("Create required directories (bootstrap will do this automatically).")

    return {
        "overall_status": overall,
        "checks":         [asdict(c) for c in checks],
        "summary":        {"pass": sum(1 for c in checks if c.status == "PASS"),
                           "warn": sum(1 for c in checks if c.status == "WARN"),
                           "fail": sum(1 for c in checks if c.status == "FAIL")},
        "recommendations": recs,
    }

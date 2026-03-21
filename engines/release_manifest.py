"""
engines/release_manifest.py
CSV-backed release manifest — one row per portfolio run or config patch.

Captures all artifact references for a given release:
  config version, backup path, portfolio run id, snapshot dirs,
  log paths, health status, deployment packet path.
"""
from __future__ import annotations

import csv
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


HEADERS = [
    "release_id", "created_at", "release_name", "release_type",
    "config_path", "config_backup_path", "config_version_tag",
    "portfolio_run_id", "state_dir", "snapshots_dir",
    "audit_path", "alerts_path", "backtest_runs_path",
    "execution_journal_path", "roll_log_path",
    "deployment_packet_path", "deployment_packet_zip",
    "health_status", "health_summary_json",
    "notes", "metadata_json",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def _init(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()


def _js(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def _jl(s: str) -> Any:
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}


class ReleaseManifest:
    def __init__(self, path: str = "logs/release_manifest.csv") -> None:
        self.path = _cloud(path)
        _init(self.path)

    def create_release(
        self, *,
        release_name:            str,
        release_type:            str,
        config_path:             str = "config/config.yaml",
        config_backup_path:      str = "",
        config_version_tag:      str = "",
        portfolio_run_id:        str = "",
        state_dir:               str = "state",
        snapshots_dir:           str = "snapshots",
        audit_path:              str = "logs/change_audit.csv",
        alerts_path:             str = "logs/alerts.csv",
        backtest_runs_path:      str = "logs/backtest_runs.csv",
        execution_journal_path:  str = "logs/execution_journal.csv",
        roll_log_path:           str = "logs/roll_suggestions.csv",
        deployment_packet_path:  str = "",
        deployment_packet_zip:   str = "",
        health_status:           str = "",
        health_summary:          dict | None = None,
        notes:                   str = "",
        metadata:                dict | None = None,
    ) -> str:
        rid  = f"rel_{_slug()}_{uuid.uuid4().hex[:8]}"
        row  = {h: "" for h in HEADERS}
        row.update({
            "release_id": rid, "created_at": _ts(),
            "release_name": release_name, "release_type": release_type,
            "config_path": config_path, "config_backup_path": config_backup_path,
            "config_version_tag": config_version_tag,
            "portfolio_run_id": portfolio_run_id,
            "state_dir": state_dir, "snapshots_dir": snapshots_dir,
            "audit_path": audit_path, "alerts_path": alerts_path,
            "backtest_runs_path": backtest_runs_path,
            "execution_journal_path": execution_journal_path,
            "roll_log_path": roll_log_path,
            "deployment_packet_path": deployment_packet_path,
            "deployment_packet_zip": deployment_packet_zip,
            "health_status": health_status,
            "health_summary_json": _js(health_summary or {}),
            "notes": notes, "metadata_json": _js(metadata or {}),
        })
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(row)
        return rid

    def list_releases(self, *, release_type: str | None = None,
                      limit: int = 500) -> list[dict[str, Any]]:
        try:
            with open(self.path, "r", newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except FileNotFoundError:
            return []
        if release_type:
            rows = [r for r in rows if r.get("release_type") == release_type]
        return sorted(rows, key=lambda r: r.get("created_at",""), reverse=True)[:limit]

    def get_release(self, release_id: str) -> dict[str, Any]:
        for r in self.list_releases(limit=5000):
            if r.get("release_id") == release_id:
                r = dict(r)
                r["metadata"]     = _jl(r.pop("metadata_json",""))
                r["health_summary"] = _jl(r.pop("health_summary_json",""))
                return r
        return {}

    def latest_release(self, release_type: str | None = None) -> dict[str, Any]:
        rows = self.list_releases(release_type=release_type, limit=1)
        if not rows:
            return {}
        r = dict(rows[0])
        r["metadata"]     = _jl(r.pop("metadata_json",""))
        r["health_summary"] = _jl(r.pop("health_summary_json",""))
        return r

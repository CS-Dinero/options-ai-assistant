"""
engines/deployment_packet.py
Assembles a structured deployment packet: config, governance artifacts,
runtime state/snapshots, analytics logs, health check — zipped.

DeploymentPacketBuilder.build_packet() → packet dict with zip path.
"""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _mkdir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _copy(src: str, dst: str) -> Optional[str]:
    if not src or not os.path.exists(src):
        return None
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _wj(path: str, payload: Any) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    return path


def _ry(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _cloud(p: str) -> str:
    if not os.path.exists("/mount/src"):
        return p
    base = Path(p)
    if str(base).startswith("logs/"):
        return f"/tmp/options_ai_logs/{base.name}"
    if str(base).startswith("state/"):
        return f"/tmp/options_ai_state/{base.name}"
    return p


class DeploymentPacketBuilder:
    def __init__(
        self, *,
        output_dir:   str = "deployment_packets",
        logs_dir:     str = "logs",
        state_dir:    str = "state",
        snapshots_dir:str = "snapshots",
        config_path:  str = "config/config.yaml",
    ) -> None:
        self.output_dir    = output_dir
        self.logs_dir      = logs_dir
        self.state_dir     = state_dir
        self.snapshots_dir = snapshots_dir
        self.config_path   = config_path
        _mkdir(output_dir)

    def _lp(self, name: str) -> str:
        """Cloud-adjusted log path."""
        return _cloud(f"{self.logs_dir}/{name}")

    def build_packet(
        self, *,
        packet_name:          str  = "",
        include_zip:          bool = True,
        include_full_logs:    bool = False,
        approved_queue_limit: int  = 200,
        audit_limit:          int  = 500,
        manifest_limit:       int  = 50,
        bootstrap_first:      bool = False,
    ) -> dict[str, Any]:

        # Optional bootstrap
        bootstrap_result = None
        if bootstrap_first:
            try:
                from engines.bootstrap import bootstrap_environment
                bootstrap_result = bootstrap_environment(config_path=self.config_path)
            except Exception:
                pass

        packet_id   = f"packet_{_slug()}"
        packet_name = packet_name or packet_id
        root        = os.path.join(self.output_dir, packet_name)

        cfg_dir  = os.path.join(root, "config")
        gov_dir  = os.path.join(root, "governance")
        run_dir  = os.path.join(root, "runtime")
        ana_dir  = os.path.join(root, "analytics")
        meta_dir = os.path.join(root, "meta")
        for d in [cfg_dir, gov_dir, run_dir, ana_dir, meta_dir]:
            _mkdir(d)

        # ── Config ────────────────────────────────────────────────────────────
        real_cfg = self.config_path
        if not os.path.exists(real_cfg):
            from pathlib import Path as P
            fb = str(P(__file__).parent.parent / "config" / "config.yaml")
            if os.path.exists(fb):
                real_cfg = fb

        current_config     = _ry(real_cfg)
        copied_config_path = _copy(real_cfg, os.path.join(cfg_dir, "config.yaml"))

        # ── Latest release manifest ───────────────────────────────────────────
        latest_manifest: dict = {}
        manifest_rows:   list = []
        try:
            from engines.release_manifest import ReleaseManifest
            rm = ReleaseManifest(path=self._lp("release_manifest.csv"))
            latest_manifest = rm.latest_release()
            manifest_rows   = rm.list_releases(limit=manifest_limit)
        except Exception:
            pass

        latest_backup = latest_manifest.get("config_backup_path","")
        copied_backup = _copy(latest_backup, os.path.join(cfg_dir, Path(latest_backup).name)) if latest_backup else None

        # ── Governance ────────────────────────────────────────────────────────
        approved_queue: list = []
        pending_queue:  list = []
        try:
            from engines.approval_queue import ApprovalQueue
            q = ApprovalQueue(path=self._lp("approval_queue.csv"))
            approved_queue = q.approved_requests(limit=approved_queue_limit)
            pending_queue  = q.pending_requests(limit=approved_queue_limit)
        except Exception:
            pass

        audit_rows: list = []
        try:
            from engines.change_audit import ChangeAudit
            audit_rows = ChangeAudit(path=self._lp("change_audit.csv")).load()[:audit_limit]
        except Exception:
            pass

        _wj(os.path.join(gov_dir,"approved_queue.json"),    {"generated_at":_ts(),"rows":approved_queue})
        _wj(os.path.join(gov_dir,"pending_queue.json"),     {"generated_at":_ts(),"rows":pending_queue})
        _wj(os.path.join(gov_dir,"change_audit.json"),      {"generated_at":_ts(),"rows":audit_rows})
        _wj(os.path.join(gov_dir,"release_manifest.json"),  latest_manifest)
        _wj(os.path.join(gov_dir,"release_manifest_recent.json"),{"generated_at":_ts(),"rows":manifest_rows})

        # ── Runtime state ─────────────────────────────────────────────────────
        state_base = "/tmp/options_ai_state" if os.path.exists("/mount/src") else self.state_dir
        def _rs(name: str) -> dict:
            p = os.path.join(state_base, name)
            if not os.path.exists(p):
                return {}
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)

        for fname in ["latest_portfolio_state.json","latest_engine_state.json",
                      "latest_alerts_state.json","latest_blotter_state.json"]:
            _wj(os.path.join(run_dir, fname), _rs(fname))

        # ── Snapshots ─────────────────────────────────────────────────────────
        snap_base = "/tmp/options_ai_snapshots" if os.path.exists("/mount/src") else self.snapshots_dir
        for cat in ["portfolio","engine","blotter","alerts"]:
            snap: dict = {}
            try:
                from engines.snapshot_manager import SnapshotManager
                snap = SnapshotManager(base_dir=snap_base).latest_snapshot(category=cat)
            except Exception:
                pass
            _wj(os.path.join(run_dir, f"latest_{cat}_snapshot.json"), snap)

        # ── Analytics logs ────────────────────────────────────────────────────
        analytics_sources = [
            "backtest_events.csv","backtest_runs.csv","execution_journal.csv",
            "roll_suggestions.csv","alerts.csv","trades.csv",
        ]
        copied_logs: dict[str, Optional[str]] = {}
        for name in analytics_sources:
            src = self._lp(name)
            copied_logs[name] = _copy(src, os.path.join(ana_dir, name))

        if include_full_logs:
            for name in ["approval_queue.csv","change_audit.csv","release_manifest.csv"]:
                src = self._lp(name)
                copied_logs[name] = _copy(src, os.path.join(ana_dir, name))

        # ── Health check ──────────────────────────────────────────────────────
        health: dict = {}
        try:
            from engines.health_check import run_health_check
            health = run_health_check(config_path=real_cfg)
        except Exception:
            pass
        _wj(os.path.join(meta_dir, "health_check.json"), health)

        # ── Deployment manifest ───────────────────────────────────────────────
        dm: dict[str, Any] = {
            "packet_id": packet_id, "packet_name": packet_name, "generated_at": _ts(),
            "config": {"source": real_cfg, "copied": copied_config_path,
                       "current_config": current_config, "backup": copied_backup},
            "latest_release_manifest": latest_manifest,
            "artifacts": {"approved_queue": len(approved_queue),
                          "pending_queue":  len(pending_queue),
                          "audit_rows":     len(audit_rows),
                          "copied_logs":    copied_logs},
            "health_check": health,
            "bootstrap_result": bootstrap_result,
        }
        _wj(os.path.join(meta_dir,"deployment_manifest.json"), dm)

        # ── Zip ───────────────────────────────────────────────────────────────
        zip_path: Optional[str] = None
        if include_zip:
            zip_path = os.path.join(self.output_dir, f"{packet_name}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for r, _, files in os.walk(root):
                    for fn in files:
                        fp = os.path.join(r, fn)
                        zf.write(fp, os.path.relpath(fp, root))

        # ── Release manifest entry ────────────────────────────────────────────
        try:
            from engines.release_manifest import ReleaseManifest
            ReleaseManifest(path=self._lp("release_manifest.csv")).create_release(
                release_name=packet_name, release_type="snapshot_bundle",
                config_path=real_cfg, config_backup_path=latest_backup,
                portfolio_run_id=str(latest_manifest.get("portfolio_run_id","")),
                deployment_packet_path=root, deployment_packet_zip=zip_path or "",
                health_status=health.get("overall_status",""),
                health_summary=health.get("summary",{}),
                notes="Deployment packet assembled.",
                metadata={"packet_id": packet_id},
            )
        except Exception:
            pass

        return {
            "packet_id":           packet_id,
            "packet_name":         packet_name,
            "packet_root":         root,
            "zip_path":            zip_path,
            "deployment_manifest": dm,
        }

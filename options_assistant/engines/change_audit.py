"""
engines/change_audit.py
Immutable append-only log of every config change applied through config_patcher.

Every APPLIED PatchPreview gets one audit row recording:
  - what changed (parameter, old → new)
  - who triggered it (source: tuner | queue | manual)
  - reviewer, run_id, backup path, notes
  - timestamp

load_audit() → DataFrame for dashboard display.
audit_summary() → quick stats.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


HEADERS = [
    "timestamp", "audit_id",
    "parameter", "old_value", "new_value",
    "source",           # tuner | queue | manual | test
    "source_run_id",
    "reviewer",
    "backup_path",
    "config_path",
    "confidence",
    "direction",
    "rationale",
    "notes",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _aid() -> str:
    return f"audit_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ%f')}"


def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def _init(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()


class ChangeAudit:
    def __init__(self, path: str = "logs/change_audit.csv") -> None:
        self.path = _cloud(path)
        _init(self.path)

    def _append(self, row: dict[str, Any]) -> None:
        full = {h: row.get(h, "") for h in HEADERS}
        full["timestamp"] = full.get("timestamp") or _ts()
        full["audit_id"]  = full.get("audit_id")  or _aid()
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(full)

    def log_patch_result(
        self, *,
        patch_result_dict:  dict[str, Any],
        source:             str          = "tuner",
        source_run_id:      str          = "",
        reviewer:           str          = "",
        notes:              str          = "",
        tuning_payload:     dict | None  = None,
    ) -> list[str]:
        """
        Log all APPLIED previews from a PatchResult dict.
        Returns list of audit_ids for the written rows.
        """
        audit_ids: list[str] = []
        config_path  = patch_result_dict.get("config_path", "")
        backup_path  = patch_result_dict.get("backup_path", "")

        # Build a lookup from parameter → suggestion metadata
        suggestion_map: dict[str, dict] = {}
        if tuning_payload:
            for s in tuning_payload.get("suggestions", []):
                param = str(s.get("parameter",""))
                if param:
                    suggestion_map[param] = s

        for preview in patch_result_dict.get("previews", []):
            if preview.get("status") != "APPLIED":
                continue
            param = str(preview.get("parameter",""))
            meta  = suggestion_map.get(param, {})
            aid   = _aid()
            self._append({
                "audit_id":      aid,
                "parameter":     param,
                "old_value":     str(preview.get("old_value", "")),
                "new_value":     str(preview.get("new_value", "")),
                "source":        source,
                "source_run_id": source_run_id,
                "reviewer":      reviewer,
                "backup_path":   backup_path,
                "config_path":   config_path,
                "confidence":    meta.get("confidence", ""),
                "direction":     meta.get("direction", ""),
                "rationale":     meta.get("rationale", ""),
                "notes":         notes,
            })
            audit_ids.append(aid)
        return audit_ids

    def log_manual_change(
        self, *,
        parameter:    str,
        old_value:    Any,
        new_value:    Any,
        reviewer:     str = "",
        config_path:  str = "",
        backup_path:  str = "",
        notes:        str = "",
    ) -> str:
        aid = _aid()
        self._append({"audit_id": aid, "parameter": parameter,
                       "old_value": str(old_value), "new_value": str(new_value),
                       "source": "manual", "reviewer": reviewer,
                       "config_path": config_path, "backup_path": backup_path,
                       "notes": notes})
        return aid

    def load(self) -> list[dict[str, Any]]:
        try:
            with open(self.path, "r", newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except FileNotFoundError:
            return []

    def summary(self) -> dict[str, Any]:
        rows = self.load()
        if not rows:
            return {"total_changes": 0, "parameters_changed": [], "last_change": None}
        params = list(dict.fromkeys(r["parameter"] for r in rows))
        return {
            "total_changes":      len(rows),
            "parameters_changed": params,
            "last_change":        rows[-1].get("timestamp", ""),
            "reviewers":          list(dict.fromkeys(r["reviewer"] for r in rows if r["reviewer"])),
        }

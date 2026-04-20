"""
engines/config_patcher.py
Safe config mutation: preview, backup, governance enforcement, audit logging.

Closes the governance loop:
  tuner → governance_guard → approval_queue → config_patcher → config.yaml
        → change_audit
"""
from __future__ import annotations

import copy
import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


def _slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _deep_get(cfg: dict[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _deep_set(cfg: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node  = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


@dataclass
class PatchPreview:
    parameter: str
    old_value: Any
    new_value: Any
    changed:   bool
    status:    str  # READY|NO_CHANGE|APPLIED|SKIPPED_*|REJECTED_*


@dataclass
class PatchResult:
    config_path: str
    backup_path: Optional[str]
    applied:     bool
    previews:    list[PatchPreview]
    notes:       list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"config_path": self.config_path, "backup_path": self.backup_path,
                "applied": self.applied,
                "previews": [asdict(p) for p in self.previews],
                "notes": self.notes}


def _find_config(p: str) -> str:
    if os.path.exists(p):
        return p
    fb = str(Path(__file__).parent.parent / "config" / "config.yaml")
    if os.path.exists(fb):
        return fb
    raise FileNotFoundError(f"Config not found: {p}")


def load_config(config_path: str = "config/config.yaml") -> dict[str, Any]:
    with open(_find_config(config_path), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict[str, Any], config_path: str) -> None:
    with open(_find_config(config_path), "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def backup_config(config_path: str, backup_dir: str = "config_backups") -> str:
    real = _find_config(config_path)
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    dest = os.path.join(backup_dir, f"{_slug()}_{os.path.basename(real)}")
    shutil.copy2(real, dest)
    return dest


def normalize_tuner_suggestions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"parameter":       str(s.get("parameter","")),
             "current_value":   s.get("current_value"),
             "suggested_value": s.get("suggested_value"),
             "confidence":      float(s.get("confidence",0.0)),
             "direction":       str(s.get("direction","")),
             "rationale":       str(s.get("rationale","")),
             }
            for s in payload.get("suggestions",[]) if s.get("parameter")]


def build_tuning_payload_from_queue_requests(
    queue_requests: list[dict[str, Any]]
) -> dict[str, Any]:
    """Convert ApprovalQueue approved rows into a tuning_payload for apply_config_patch."""
    return {
        "summary": {"source": "approval_queue"},
        "suggestions": [
            {"parameter":       s.get("parameter",""),
             "current_value":   s.get("current_value"),
             "suggested_value": s.get("requested_value"),
             "confidence":      float(s.get("confidence",0.0)),
             "direction":       str(s.get("direction","")),
             "rationale":       str(s.get("rationale","")),
             "evidence":        s.get("evidence",{})}
            for s in queue_requests
        ],
    }


def _gov_map(cfg: dict, payload: dict) -> dict[str, dict]:
    try:
        from engines.governance_guard import evaluate_patch_payload
        gov = evaluate_patch_payload(config=cfg, tuning_payload=payload)
        return {x["parameter"]: x for x in gov.get("all",[])}
    except Exception:
        return {}


def preview_config_patch(
    *,
    config_path:        str,
    tuning_payload:     dict[str, Any],
    include_parameters: list[str] | None = None,
    min_confidence:     float = 0.0,
    enforce_governance: bool  = True,
) -> PatchResult:
    cfg  = load_config(config_path)
    sugs = normalize_tuner_suggestions(tuning_payload)
    gmap = _gov_map(cfg, tuning_payload) if enforce_governance else {}
    previews: list[PatchPreview] = []

    for s in sugs:
        param, conf, old, new = s["parameter"], s["confidence"], _deep_get(cfg, s["parameter"]), s["suggested_value"]
        if include_parameters and param not in include_parameters:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_NOT_SELECTED")); continue
        if conf < min_confidence:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_LOW_CONFIDENCE")); continue
        gd = gmap.get(param, {})
        if gd and not gd.get("allowed", True):
            previews.append(PatchPreview(param, old, new, False, gd.get("status","REJECTED_GOVERNANCE"))); continue
        previews.append(PatchPreview(param, old, new, old != new, "READY" if old != new else "NO_CHANGE"))

    return PatchResult(_find_config(config_path), None, False, previews,
                       [] if previews else ["No suggestions to preview."])


def apply_config_patch(
    *,
    config_path:        str,
    tuning_payload:     dict[str, Any],
    include_parameters: list[str] | None = None,
    min_confidence:     float = 0.0,
    make_backup:        bool  = True,
    backup_dir:         str   = "config_backups",
    enforce_governance: bool  = True,
    audit_log:          bool  = True,
    audit_path:         str   = "logs/change_audit.csv",
    source:             str   = "tuner",
    source_run_id:      str   = "",
    reviewer:           str   = "",
    audit_notes:        str   = "",
) -> PatchResult:
    real     = _find_config(config_path)
    cfg      = load_config(config_path)
    original = copy.deepcopy(cfg)
    sugs     = normalize_tuner_suggestions(tuning_payload)
    gmap     = _gov_map(cfg, tuning_payload) if enforce_governance else {}
    previews: list[PatchPreview] = []
    notes:    list[str]          = []
    blocked  = 0

    for s in sugs:
        param, conf, old, new = s["parameter"], s["confidence"], _deep_get(cfg, s["parameter"]), s["suggested_value"]
        if include_parameters and param not in include_parameters:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_NOT_SELECTED")); continue
        if conf < min_confidence:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_LOW_CONFIDENCE")); continue
        gd = gmap.get(param, {})
        if gd and not gd.get("allowed", True):
            previews.append(PatchPreview(param, old, new, False, gd.get("status","REJECTED_GOVERNANCE")))
            blocked += 1; continue
        if old == new:
            previews.append(PatchPreview(param, old, new, False, "NO_CHANGE")); continue
        _deep_set(cfg, param, new)
        previews.append(PatchPreview(param, old, new, True, "APPLIED"))

    backup_path: str | None = None
    changed = cfg != original
    if changed:
        if make_backup:
            backup_path = backup_config(config_path, backup_dir)
            notes.append(f"Backup: {backup_path}")
        save_config(cfg, config_path)
        notes.append(f"Config updated: {real}")
    else:
        notes.append("No changes applied.")
    if blocked:
        notes.append(f"Governance blocked {blocked} change(s).")

    result = PatchResult(real, backup_path, changed, previews, notes)

    if audit_log and changed:
        try:
            from engines.change_audit import ChangeAudit
            ChangeAudit(path=audit_path).log_patch_result(
                patch_result_dict=result.to_dict(), source=source,
                source_run_id=source_run_id, reviewer=reviewer, notes=audit_notes,
                tuning_payload=tuning_payload)
        except Exception:
            pass

    return result

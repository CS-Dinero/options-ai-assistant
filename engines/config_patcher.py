"""
engines/config_patcher.py
Safe config mutation with preview, backup, selective application, and confidence gating.

Closes the loop:
  logs → analytics → optimizer → tuner → config_patcher → config.yaml

Usage:
    tuning = tune_parameters(...)
    preview = preview_config_patch(config_path=..., tuning_payload=tuning.to_dict(), min_confidence=0.65)
    result  = apply_config_patch(config_path=..., tuning_payload=tuning.to_dict(), min_confidence=0.70)

IMPORTANT: apply_config_patch modifies config.yaml. Always use make_backup=True in production.
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


# ─────────────────────────────────────────────
# RESULT TYPES
# ─────────────────────────────────────────────

@dataclass
class PatchPreview:
    parameter:  str
    old_value:  Any
    new_value:  Any
    changed:    bool
    status:     str   # READY | NO_CHANGE | SKIPPED_NOT_SELECTED | SKIPPED_LOW_CONFIDENCE | APPLIED


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


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _find_config(config_path: str) -> str:
    if os.path.exists(config_path):
        return config_path
    fallback = str(Path(__file__).parent.parent / "config" / "config.yaml")
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError(f"Config not found: {config_path}")


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
    return [
        {
            "parameter":       str(s.get("parameter", "")),
            "current_value":   s.get("current_value"),
            "suggested_value": s.get("suggested_value"),
            "confidence":      float(s.get("confidence", 0.0)),
            "direction":       str(s.get("direction", "")),
            "rationale":       str(s.get("rationale", "")),
        }
        for s in payload.get("suggestions", [])
        if s.get("parameter")
    ]


# ─────────────────────────────────────────────
# PREVIEW
# ─────────────────────────────────────────────

def preview_config_patch(
    *,
    config_path:         str,
    tuning_payload:      dict[str, Any],
    include_parameters:  list[str] | None = None,
    min_confidence:      float = 0.0,
) -> PatchResult:
    cfg  = load_config(config_path)
    sugs = normalize_tuner_suggestions(tuning_payload)
    previews: list[PatchPreview] = []

    for s in sugs:
        param = s["parameter"]
        conf  = s["confidence"]
        old   = _deep_get(cfg, param)
        new   = s["suggested_value"]

        if include_parameters and param not in include_parameters:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_NOT_SELECTED"))
            continue
        if conf < min_confidence:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_LOW_CONFIDENCE"))
            continue

        status = "READY" if old != new else "NO_CHANGE"
        previews.append(PatchPreview(param, old, new, old != new, status))

    return PatchResult(_find_config(config_path), None, False, previews,
                       [] if previews else ["No suggestions to preview."])


# ─────────────────────────────────────────────
# APPLY
# ─────────────────────────────────────────────

def apply_config_patch(
    *,
    config_path:         str,
    tuning_payload:      dict[str, Any],
    include_parameters:  list[str] | None = None,
    min_confidence:      float = 0.0,
    make_backup:         bool  = True,
    backup_dir:          str   = "config_backups",
) -> PatchResult:
    real     = _find_config(config_path)
    cfg      = load_config(config_path)
    original = copy.deepcopy(cfg)
    sugs     = normalize_tuner_suggestions(tuning_payload)
    previews: list[PatchPreview] = []
    notes:    list[str]          = []

    for s in sugs:
        param = s["parameter"]
        conf  = s["confidence"]
        old   = _deep_get(cfg, param)
        new   = s["suggested_value"]

        if include_parameters and param not in include_parameters:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_NOT_SELECTED"))
            continue
        if conf < min_confidence:
            previews.append(PatchPreview(param, old, new, False, "SKIPPED_LOW_CONFIDENCE"))
            continue
        if old == new:
            previews.append(PatchPreview(param, old, new, False, "NO_CHANGE"))
            continue

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

    return PatchResult(real, backup_path, changed, previews, notes)

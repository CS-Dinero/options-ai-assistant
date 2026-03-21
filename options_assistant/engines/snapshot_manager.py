"""
engines/snapshot_manager.py
Timestamped historical snapshots — one file per run, never overwritten.

Folders: snapshots/{category}/{timestamp}_{name}.json

Usage:
    mgr = SnapshotManager()
    mgr.save_snapshot(category="portfolio", name="run", payload=output)
    items = mgr.list_snapshots(category="portfolio", limit=10)
    snap  = mgr.load_snapshot(items[0]["path"])
    latest = mgr.latest_snapshot(category="portfolio")
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _cloud(base: str) -> str:
    return "/tmp/options_ai_snapshots" if os.path.exists("/mount/src") else base


def _json_default(obj: Any) -> Any:
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.to_dict()
    except Exception:
        pass
    return str(obj)


class SnapshotManager:
    def __init__(self, base_dir: str = "snapshots") -> None:
        self.base_dir = _cloud(base_dir)
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def _cat_dir(self, category: str) -> str:
        d = os.path.join(self.base_dir, category)
        Path(d).mkdir(parents=True, exist_ok=True)
        return d

    def save_snapshot(self, *, category: str, name: str,
                      payload: dict[str, Any],
                      metadata: dict | None = None) -> str:
        safe = name.replace(" ", "_").replace("/", "_").lower()
        path = os.path.join(self._cat_dir(category), f"{_slug()}_{safe}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"saved_at": _ts(), "category": category, "name": name,
                       "metadata": metadata or {}, "payload": payload},
                      f, indent=2, ensure_ascii=False, default=_json_default)
        return path

    def list_snapshots(self, *, category: Optional[str] = None,
                       limit: int = 100) -> list[dict[str, Any]]:
        cats = [category] if category else [
            d for d in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, d))
        ]
        results = []
        for cat in cats:
            cat_dir = os.path.join(self.base_dir, cat)
            if not os.path.isdir(cat_dir):
                continue
            for fn in os.listdir(cat_dir):
                if fn.endswith(".json"):
                    fp = os.path.join(cat_dir, fn)
                    results.append({"category": cat, "filename": fn,
                                    "path": fp, "mtime": os.path.getmtime(fp)})
        results.sort(key=lambda x: x["mtime"], reverse=True)
        return results[:limit]

    def load_snapshot(self, path: str) -> dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def latest_snapshot(self, *, category: str) -> dict[str, Any]:
        items = self.list_snapshots(category=category, limit=1)
        return self.load_snapshot(items[0]["path"]) if items else {}

    def latest_snapshots(self, *, category: str, n: int = 5) -> list[dict[str, Any]]:
        return self.list_snapshots(category=category, limit=n)

    def delete_snapshot(self, path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def category_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.list_snapshots(limit=100_000):
            counts[item["category"]] = counts.get(item["category"], 0) + 1
        return counts

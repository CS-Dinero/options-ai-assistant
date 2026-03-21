"""
engines/state_store.py
Lightweight JSON-backed latest-state persistence.

Stores one "current" file per state type — overwritten each run.
For historical snapshots, see engines/snapshot_manager.py.

Files (default base_dir="state"):
  latest_engine_state.json
  latest_portfolio_state.json
  latest_blotter_state.json
  latest_alerts_state.json
  {name}.json          (named snapshots)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cloud(base: str) -> str:
    if os.path.exists("/mount/src"):
        return "/tmp/options_ai_state"
    return base


def _json_default(obj: Any) -> Any:
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.to_dict()
    except Exception:
        pass
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


class StateStore:
    """Latest-state JSON persistence. One file per state type, always overwritten."""

    def __init__(self, base_dir: str = "state") -> None:
        self.base_dir = _cloud(base_dir)
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> str:
        return os.path.join(self.base_dir, filename)

    def _write(self, filename: str, payload: dict[str, Any]) -> str:
        path = self._path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=_json_default)
        return path

    def _read(self, filename: str) -> dict[str, Any]:
        path = self._path(filename)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_portfolio_state(self, output: dict[str, Any],
                             filename: str = "latest_portfolio_state.json",
                             metadata: dict | None = None) -> str:
        return self._write(filename, {"saved_at": _ts(),
                                       "metadata": metadata or {},
                                       "portfolio_output": output})

    def load_portfolio_state(self, filename: str = "latest_portfolio_state.json") -> dict[str, Any]:
        return self._read(filename)

    def save_engine_state(self, output: dict[str, Any],
                          filename: str = "latest_engine_state.json",
                          metadata: dict | None = None) -> str:
        return self._write(filename, {"saved_at": _ts(),
                                       "metadata": metadata or {},
                                       "engine_output": output})

    def load_engine_state(self, filename: str = "latest_engine_state.json") -> dict[str, Any]:
        return self._read(filename)

    def save_alerts_state(self, alerts_payload: dict[str, Any],
                          filename: str = "latest_alerts_state.json",
                          metadata: dict | None = None) -> str:
        return self._write(filename, {"saved_at": _ts(),
                                       "metadata": metadata or {},
                                       "alerts": alerts_payload})

    def load_alerts_state(self, filename: str = "latest_alerts_state.json") -> dict[str, Any]:
        return self._read(filename)

    def save_named_snapshot(self, name: str, payload: dict[str, Any],
                            metadata: dict | None = None) -> str:
        safe = name.replace(" ", "_").lower()
        return self._write(f"{safe}.json",
                           {"saved_at": _ts(), "metadata": metadata or {}, "payload": payload})

    def load_named_snapshot(self, name: str) -> dict[str, Any]:
        return self._read(f"{name.replace(' ','_').lower()}.json")

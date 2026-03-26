"""history/snapshot_repository.py — Stores historical snapshots."""
from __future__ import annotations
from storage.repository_base import RepositoryBase
from typing import Any

class SnapshotRepository(RepositoryBase):
    def list_by_type(self, snapshot_type: str, environment: str|None=None) -> list[dict[str,Any]]:
        results=[r for r in self.list_all() if r.get("snapshot_type")==snapshot_type]
        if environment: results=[r for r in results if r.get("environment")==environment]
        return sorted(results, key=lambda r: r.get("timestamp_utc",""))

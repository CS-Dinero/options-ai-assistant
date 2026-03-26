"""storage/repository_base.py — In-memory repository base (swap backend later)."""
from __future__ import annotations
from typing import Any

class RepositoryBase:
    def __init__(self): self._store: dict[str,dict[str,Any]] = {}
    def insert(self, object_id: str, record: dict[str,Any]) -> None:
        self._store[object_id]=dict(record)
    def upsert(self, object_id: str, record: dict[str,Any]) -> None:
        self._store[object_id]=dict(record)
    def get(self, object_id: str) -> dict[str,Any]|None:
        rec=self._store.get(object_id); return dict(rec) if rec else None
    def list_all(self) -> list[dict[str,Any]]:
        return [dict(v) for v in self._store.values()]
    def filter(self, **conditions) -> list[dict[str,Any]]:
        out=[]
        for rec in self._store.values():
            if all(rec.get(k)==v for k,v in conditions.items()): out.append(dict(rec))
        return out
    def count(self) -> int: return len(self._store)

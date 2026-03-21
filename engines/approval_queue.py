"""
engines/approval_queue.py
Staged approval workflow for governance-approved config changes.

Flow:
  tuner → governance_guard → approval_queue (pending)
        → manual approve/reject
        → config_patcher apply (→ applied)
        → change_audit log

CSV: logs/approval_queue.csv — one row per request, mutable status column.
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
    "request_id", "created_at", "updated_at", "status",
    "parameter", "current_value", "requested_value",
    "confidence", "direction", "rationale", "evidence_json",
    "governance_status", "governance_reason",
    "reviewer", "review_notes", "source_run_id",
]
# status: pending | approved | rejected | applied | expired


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def _js(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def _jl(s: str) -> Any:
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {"raw": s}


def _init(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()


class ApprovalQueue:
    def __init__(self, path: str = "logs/approval_queue.csv") -> None:
        self.path = _cloud(path)
        _init(self.path)

    def _read(self) -> list[dict[str, Any]]:
        with open(self.path, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write(self, rows: list[dict[str, Any]]) -> None:
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=HEADERS)
            w.writeheader()
            w.writerows(rows)

    def create_request(
        self, *,
        parameter:         str,
        current_value:     Any,
        requested_value:   Any,
        confidence:        float = 0.0,
        direction:         str   = "",
        rationale:         str   = "",
        evidence:          dict | None = None,
        governance_status: str   = "",
        governance_reason: str   = "",
        source_run_id:     str   = "",
    ) -> str:
        rid = str(uuid.uuid4())
        now = _ts()
        row = {h: "" for h in HEADERS}
        row.update({"request_id": rid, "created_at": now, "updated_at": now,
                    "status": "pending", "parameter": parameter,
                    "current_value": str(current_value), "requested_value": str(requested_value),
                    "confidence": confidence, "direction": direction, "rationale": rationale,
                    "evidence_json": _js(evidence or {}),
                    "governance_status": governance_status, "governance_reason": governance_reason,
                    "source_run_id": source_run_id})
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(row)
        return rid

    def create_many_from_governed_suggestions(
        self, *, governance_payload: dict[str, Any],
        source_run_id: str = "", approved_only: bool = True,
    ) -> list[str]:
        key = "approved" if approved_only else "all"
        return [
            self.create_request(
                parameter=s.get("parameter",""),
                current_value=s.get("current_value"),
                requested_value=s.get("requested_value"),
                confidence=float(s.get("confidence",0.0)),
                direction=str(s.get("direction","")),
                rationale=str(s.get("rationale","")),
                evidence=s.get("evidence",{}),
                governance_status=str(s.get("status","")),
                governance_reason=str(s.get("reason","")),
                source_run_id=source_run_id,
            )
            for s in governance_payload.get(key, [])
        ]

    def list_requests(self, *, status: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        rows = self._read()
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return sorted(rows, key=lambda r: r.get("updated_at",""), reverse=True)[:limit]

    def get_request(self, request_id: str) -> dict[str, Any]:
        for r in self._read():
            if r.get("request_id") == request_id:
                r = dict(r)
                r["evidence"] = _jl(r.pop("evidence_json",""))
                return r
        return {}

    def _update(self, request_id: str, status: str,
                reviewer: str = "", review_notes: str = "") -> bool:
        rows = self._read()
        updated = False
        for r in rows:
            if r.get("request_id") == request_id:
                r["status"]       = status
                r["updated_at"]   = _ts()
                r["reviewer"]     = reviewer or r.get("reviewer","")
                r["review_notes"] = review_notes or r.get("review_notes","")
                updated = True
                break
        if updated:
            self._write(rows)
        return updated

    def approve(self, rid: str, *, reviewer: str = "", review_notes: str = "") -> bool:
        return self._update(rid, "approved", reviewer, review_notes)

    def reject(self, rid: str, *, reviewer: str = "", review_notes: str = "") -> bool:
        return self._update(rid, "rejected", reviewer, review_notes)

    def mark_applied(self, rid: str, *, reviewer: str = "", review_notes: str = "") -> bool:
        return self._update(rid, "applied", reviewer, review_notes)

    def approved_requests(self, limit: int = 500) -> list[dict[str, Any]]:
        rows = self.list_requests(status="approved", limit=limit)
        for r in rows:
            r["evidence"] = _jl(r.pop("evidence_json",""))
        return rows

    def pending_requests(self, limit: int = 500) -> list[dict[str, Any]]:
        rows = self.list_requests(status="pending", limit=limit)
        for r in rows:
            r["evidence"] = _jl(r.pop("evidence_json",""))
        return rows

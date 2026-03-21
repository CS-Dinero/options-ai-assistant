"""engines/roll_logger.py — CSV logger for roll suggestions."""
from __future__ import annotations
import csv, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HEADERS = [
    "timestamp","symbol","strategy","action","urgency",
    "current_spot","short_strike","long_strike","short_dte","long_dte",
    "expected_move","target_short_strike","target_long_strike",
    "target_short_dte","target_long_dte","rationale","notes",
]

def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p

class RollLogger:
    def __init__(self, path: str = "logs/roll_suggestions.csv") -> None:
        self.path = _cloud(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=HEADERS).writeheader()

    def append(self, s: dict[str, Any]) -> None:
        row = {h: s.get(h, "") for h in HEADERS}
        row.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(row)

    def append_many(self, suggestions: list[dict[str, Any]]) -> None:
        for s in suggestions: self.append(s)

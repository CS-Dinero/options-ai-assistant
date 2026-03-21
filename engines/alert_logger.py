"""engines/alert_logger.py — CSV logger for alerts."""
from __future__ import annotations
import csv, os
from pathlib import Path
from typing import Any

HEADERS = ["timestamp","symbol","alert_type","severity","title","message",
           "action","strategy","run_id"]

def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p

class AlertLogger:
    def __init__(self, path: str = "logs/alerts.csv") -> None:
        self.path = _cloud(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=HEADERS).writeheader()

    def append(self, alert: dict[str, Any]) -> None:
        row = {h: alert.get(h,"") for h in HEADERS}
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(row)

    def append_many(self, alerts: list[dict[str, Any]]) -> None:
        for a in alerts: self.append(a)

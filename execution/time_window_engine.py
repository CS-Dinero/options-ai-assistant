"""execution/time_window_engine.py — Session window classifier."""
from __future__ import annotations
from datetime import datetime, time
from typing import Any

WINDOW_RULES = {
    "OPENING_VOL":    {"start": time(9,30),  "end": time(10,0)},
    "MORNING_TREND":  {"start": time(10,0),  "end": time(11,30)},
    "MIDDAY":         {"start": time(11,30), "end": time(14,30)},
    "POWER_HOUR":     {"start": time(14,30), "end": time(15,45)},
    "LATE_CLOSE":     {"start": time(15,45), "end": time(16,0)},
}
NEXT_WINDOW = {"OPENING_VOL":"MORNING_TREND","MORNING_TREND":"MIDDAY",
               "MIDDAY":"POWER_HOUR","POWER_HOUR":"NEXT_SESSION_OPEN",
               "LATE_CLOSE":"NEXT_SESSION_OPEN","OUTSIDE_RTH":"NEXT_SESSION_OPEN"}

def classify_time_window(now_dt: datetime | None = None) -> dict[str, Any]:
    now_dt = now_dt or datetime.now()
    t = now_dt.time()
    for label, r in WINDOW_RULES.items():
        if r["start"] <= t < r["end"]:
            return {"time_window": label, "is_rth": True,
                    "next_window": NEXT_WINDOW.get(label,"NEXT_SESSION_OPEN")}
    return {"time_window": "OUTSIDE_RTH", "is_rth": False, "next_window": "NEXT_SESSION_OPEN"}

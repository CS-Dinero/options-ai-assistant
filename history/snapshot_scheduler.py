"""history/snapshot_scheduler.py — Defines when snapshots should be captured."""
from __future__ import annotations

SNAPSHOT_EVENTS: set = {
    "DASHBOARD_REFRESH","VALIDATION_RUN","POLICY_ACTIVATION",
    "EXECUTION_BATCH","END_OF_SESSION",
}

def should_capture_snapshot(event_type: str) -> bool:
    return event_type in SNAPSHOT_EVENTS

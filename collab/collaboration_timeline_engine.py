"""collab/collaboration_timeline_engine.py — Builds chain of custody and context."""
from __future__ import annotations
from typing import Any

def build_collaboration_timeline(handoff_packet: dict[str,Any],
                                  decision_packets: list[dict[str,Any]]|None=None) -> list[dict[str,Any]]:
    dp=decision_packets or []; timeline=[]
    timeline.append({"event":"HANDOFF_CREATED","role":handoff_packet.get("source_role"),
                     "timestamp_utc":handoff_packet.get("created_utc"),"summary":handoff_packet.get("summary")})
    if handoff_packet.get("accepted_utc"):
        timeline.append({"event":"HANDOFF_ACCEPTED","role":handoff_packet.get("target_role"),
                         "timestamp_utc":handoff_packet.get("accepted_utc"),"summary":"Target role accepted handoff."})
    for note in handoff_packet.get("notes",[]):
        timeline.append({"event":"HANDOFF_NOTE","role":None,"timestamp_utc":note.get("timestamp_utc"),
                         "summary":note.get("note")})
    for d in dp:
        timeline.append({"event":"DECISION","role":None,"timestamp_utc":d.get("timestamp_utc"),
                         "summary":d.get("decision_type")})
    return sorted(timeline, key=lambda x: x.get("timestamp_utc") or "")

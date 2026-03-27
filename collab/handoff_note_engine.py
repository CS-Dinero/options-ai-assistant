"""collab/handoff_note_engine.py — Captures handoff context notes."""
from __future__ import annotations
from typing import Any
from datetime import datetime

def append_handoff_note(handoff_packet: dict[str,Any], author: str, note: str,
                         note_type: str="CONTEXT") -> dict[str,Any]:
    out=dict(handoff_packet); notes=list(out.get("notes",[]))
    notes.append({"author":author,"note":note,"note_type":note_type,"timestamp_utc":datetime.utcnow().isoformat()})
    out["notes"]=notes; return out

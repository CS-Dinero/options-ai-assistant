"""diagnostics/queue_compression_engine.py — Shows where good candidates are being crowded out."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def analyze_queue_compression(queue: list[dict[str,Any]], top_n: int=5) -> dict[str,Any]:
    if not queue: return {"top_n_count":0,"compressed_count":0,"by_symbol_top_n":{},"by_playbook_top_n":{}}
    top=queue[:top_n]; compressed=queue[top_n:]
    sym_top=defaultdict(int); pb_top=defaultdict(int)
    for item in top:
        sym_top[item.get("symbol","?")]+=1; pb_top[item.get("playbook_code","?")]+=1
    return {"top_n_count":len(top),"compressed_count":len(compressed),
            "by_symbol_top_n":dict(sym_top),"by_playbook_top_n":dict(pb_top)}

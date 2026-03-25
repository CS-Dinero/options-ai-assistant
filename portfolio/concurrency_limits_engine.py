"""portfolio/concurrency_limits_engine.py — Caps simultaneous campaigns per symbol/playbook/family."""
from __future__ import annotations
from typing import Any
from collections import Counter

def _sf(v,d=0):
    try: return int(float(v)) if v not in(None,"") else d
    except: return d

def evaluate_concurrency_limits(
    rows: list[dict[str,Any]],
    candidate_row: dict[str,Any],
    playbook_policy: dict[str,Any],
    symbol_concurrency_overrides: dict|None = None,
) -> dict[str,Any]:
    symbol = str(candidate_row.get("symbol",""))
    pb_code = str(candidate_row.get("playbook_code",""))
    pb_family= str(candidate_row.get("playbook_family",""))

    active = [r for r in rows if str(r.get("status","OPEN")) not in ("CLOSED","EXPIRED")]
    sym_c  = Counter(r.get("symbol") for r in active)
    pb_c   = Counter(r.get("playbook_code") for r in active)
    fam_c  = Counter(r.get("playbook_family") for r in active)

    max_sym = int((symbol_concurrency_overrides or {}).get(symbol,
                   playbook_policy.get("max_symbol_concurrency",2)))
    max_pb  = int(playbook_policy.get("max_playbook_concurrency",3))

    n_sym=int(sym_c.get(symbol,0)); n_pb=int(pb_c.get(pb_code,0)); n_fam=int(fam_c.get(pb_family,0))
    sym_ok = n_sym < max_sym; pb_ok  = n_pb  < max_pb
    notes=[]
    if not sym_ok: notes.append(f"symbol concurrency limit reached ({n_sym}/{max_sym})")
    if not pb_ok:  notes.append(f"playbook concurrency limit reached ({n_pb}/{max_pb})")
    return {"active_symbol_count":n_sym,"active_playbook_count":n_pb,"active_family_count":n_fam,
            "symbol_concurrency_ok":sym_ok,"playbook_concurrency_ok":pb_ok,
            "concurrency_ok":sym_ok and pb_ok,"notes":notes}

"""causal/comparison_group_engine.py — Builds similar-but-unaffected comparison cohorts."""
from __future__ import annotations
from typing import Any

def build_comparison_group(rows: list[dict[str,Any]], intervention: dict[str,Any],
                            exclude_scope_keys: list[str]|None=None) -> list[dict[str,Any]]:
    excl=set(exclude_scope_keys or []); scope=intervention.get("target_scope",{})
    env=intervention.get("environment"); eff=intervention.get("effective_utc","")
    out=[]
    for r in rows:
        if env and r.get("environment")!=env: continue
        if eff and str(r.get("timestamp_utc",""))<eff: continue
        same_non_excl=all(r.get(k)==v for k,v in scope.items() if k not in excl)
        fully_same   =all(r.get(k)==v for k,v in scope.items())
        if same_non_excl and not fully_same: out.append(r)
    return out

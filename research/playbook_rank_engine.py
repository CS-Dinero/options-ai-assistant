"""research/playbook_rank_engine.py — Converts research stats into a ranked score."""
from __future__ import annotations
from typing import Any

def _sample_conf(n):
    if n>=25: return 100.0
    if n>=10: return 75.0
    if n>=5:  return 50.0
    if n>=1:  return 25.0
    return 0.0

def _slip_score(s):
    if s>=0:   return 100.0
    if s>=-0.10: return 80.0
    if s>=-0.25: return 60.0
    if s>=-0.50: return 40.0
    return 20.0

def build_playbook_rankings(playbook_stats: dict[str,Any]) -> dict[str,Any]:
    ranked={}
    for code,s in playbook_stats.get("by_playbook",{}).items():
        n=int(s.get("count",0)); sr=float(s.get("success_rate",0))
        oc=float(s.get("avg_outcome_score",0)); bs=float(s.get("avg_basis_reduction",0))
        fs=float(s.get("avg_fill_score",0)); sl=float(s.get("avg_slippage_dollars",0))
        ps=float(s.get("avg_path_score",0))
        rank=round(0.20*_sample_conf(n)+0.20*min(100,sr*100)+0.20*min(100,oc)
                   +0.15*min(100,bs*25)+0.10*min(100,fs)+0.05*_slip_score(sl)+0.10*min(100,ps),2)
        ranked[code]={"count":n,"sample_score":_sample_conf(n),"success_score":min(100,sr*100),
                      "outcome_score":min(100,oc),"basis_score":min(100,bs*25),
                      "fill_score":min(100,fs),"slippage_score":_slip_score(sl),
                      "path_score":min(100,ps),"rank_score":rank}
    return {"rankings":ranked}

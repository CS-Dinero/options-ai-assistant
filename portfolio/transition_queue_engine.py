"""portfolio/transition_queue_engine.py — Ranks all valid transitions across the book."""
from __future__ import annotations
from typing import Any

PRIORITY_SCORE = {"P0":100,"P1":90,"P2":80,"P3":70,"P4":60,"P5":50,"P6":40}

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_transition_queue(rows: list[dict[str,Any]]) -> list[dict[str,Any]]:
    """Return sorted queue of portfolio-approved transitions. All gates must pass."""
    queue=[]
    for r in rows:
        if not r.get("transition_action"): continue
        if not r.get("transition_is_credit_approved",False): continue
        if not r.get("transition_improves_campaign",False): continue
        if not r.get("transition_path_robust",False): continue
        if not r.get("transition_portfolio_fit_ok",False): continue
        ps = PRIORITY_SCORE.get(str(r.get("bot_priority","P6")),40)
        qs_base = round(
            0.18*_sf(r.get("transition_structure_score")) +
            0.15*_sf(r.get("transition_campaign_improvement_score")) +
            0.12*_sf(r.get("transition_avg_path_score")) +
            0.14*_sf(r.get("transition_allocator_score")) +
            0.10*_sf(r.get("transition_recycling_score")) +
            0.10*_sf(r.get("transition_timing_score")) +
            0.09*_sf(r.get("transition_execution_surface_score")) +
            0.12*ps, 2)
        # Capital rotation + playbook bias overlays (bounded)
        rotation_bias = {"ALLOW_FULL":4.0,"ALLOW_NORMAL":1.5,
                         "ALLOW_REDUCED":-2.0,"BLOCK_EXPANSION":-8.0}.get(
                          r.get("capital_commitment_decision","NO_ADD"), 0.0)
        pb_bias = max(-15.0, min(8.0, _sf(r.get("playbook_queue_bias",0.0))))
        qs = round(qs_base + rotation_bias + pb_bias, 2)
        queue.append({
            "position_id":        r.get("trade_id") or r.get("id"),
            "symbol":             r.get("symbol"),
            "transition_action":  r.get("transition_action"),
            "queue_score":        qs,
            "transition_credit":  _sf(r.get("transition_net_credit")),
            "campaign_basis_after":_sf(r.get("transition_campaign_net_basis_after")),
            "allocator_score":    _sf(r.get("transition_allocator_score")),
            "priority":           r.get("bot_priority","P6"),
            "time_window":        r.get("transition_time_window","—"),
            "execution_policy":   r.get("transition_execution_policy","DELAY"),
            "timing_score":       _sf(r.get("transition_timing_score")),
            "surface_score":      _sf(r.get("transition_execution_surface_score")),
            "queue_one_liner":    r.get("queue_one_liner",""),
            "desk_note":          r.get("transition_desk_note",""),
            "playbook_code":      r.get("playbook_code","—"),
            "playbook_status":    r.get("playbook_status","WATCHLIST"),
            "capital_decision":   r.get("capital_commitment_decision","NO_ADD"),
            "contract_add":       r.get("transition_final_contract_add",0),
        })
    return sorted(queue, key=lambda x: x["queue_score"], reverse=True)

def filter_executable_queue(queue: list[dict[str,Any]], min_score: float=70.0) -> list[dict[str,Any]]:
    return [q for q in queue if _sf(q.get("queue_score"))>=min_score]

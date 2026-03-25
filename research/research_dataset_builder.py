"""research/research_dataset_builder.py — Assembles clean historical decision/outcome rows."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_research_dataset(evaluated_journals: list[dict[str,Any]],
                            slippage_entries: list[dict[str,Any]]|None=None) -> list[dict[str,Any]]:
    slippage_by_journal={str(e.get("journal_id")):e for e in (slippage_entries or []) if e.get("journal_id")}
    rows=[]
    for j in evaluated_journals:
        jid=str(j.get("journal_id","")); sl=slippage_by_journal.get(jid,{})
        rows.append({
            "journal_id":jid,"campaign_id":j.get("campaign_id"),"symbol":j.get("symbol"),
            "playbook_code":j.get("playbook_code"),"playbook_name":j.get("playbook_name"),
            "playbook_family":j.get("playbook_family"),
            "action":j.get("approved_action"),"rebuild_class":j.get("approved_rebuild_class"),
            "target_width":j.get("approved_target_width"),"time_window":j.get("time_window"),
            "execution_policy":j.get("execution_policy"),
            "vga_environment":j.get("vga_environment"),"gamma_regime":j.get("gamma_regime"),
            "iv_state":j.get("iv_state"),"skew_state":j.get("skew_state"),
            "transition_credit":_sf(j.get("approved_transition_credit")),
            "campaign_basis_before":_sf(j.get("campaign_net_basis_before")),
            "campaign_basis_after":_sf(j.get("campaign_net_basis_after")),
            "recovered_pct_before":_sf(j.get("recovered_pct_before")),
            "recovered_pct_after":_sf(j.get("recovered_pct_after")),
            "campaign_improvement_score":_sf(j.get("campaign_improvement_score")),
            "avg_path_score":_sf(j.get("approved_avg_path_score")),
            "worst_path_score":_sf(j.get("approved_worst_path_score")),
            "allocator_score":_sf(j.get("allocator_score")),
            "timing_score":_sf(j.get("timing_score")),
            "surface_score":_sf(j.get("surface_score")),
            "actual_credit":_sf(j.get("actual_fill_credit",sl.get("actual_credit",0))),
            "fill_score":_sf(j.get("fill_score",sl.get("fill_score",0))),
            "slippage_dollars":_sf(j.get("fill_slippage_dollars",sl.get("slippage_dollars",0))),
            "outcome_score":_sf(j.get("outcome_score")),"success":bool(j.get("success",False)),
        })
    return rows

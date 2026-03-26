"""reporting/weekly_playbook_review.py — Weekly playbook evidence and drift."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_weekly_playbook_review(environment: str, live_policy_version_id: str|None,
                                  playbook_stats: dict[str,Any], playbook_statuses: dict[str,Any],
                                  playbook_drag: dict[str,Any],
                                  refinements: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    by_pb=playbook_stats.get("by_playbook",{}); status_map=playbook_statuses.get("playbook_statuses",{})
    rows=[{"playbook_code":c,"status":status_map.get(c,{}).get("status","?"),
           "count":s.get("count",0),"success_rate":s.get("success_rate",0),
           "avg_outcome":s.get("avg_outcome_score",0),"avg_fill":s.get("avg_fill_score",0),
           "avg_slip":s.get("avg_slippage_dollars",0)} for c,s in by_pb.items()]
    promoted=sum(1 for _,v in status_map.items() if v.get("status")=="PROMOTED")
    demoted=sum(1 for _,v in status_map.items() if v.get("status")=="DEMOTED")
    bullets=[f"Tracked playbooks: {len(rows)}",f"Promoted: {promoted}",f"Demoted: {demoted}"]
    sections=[{"title":"Playbook Summary","content":rows},
              {"title":"Playbook Drag","content":playbook_drag.get("playbook_drag",[])[:10]}]
    if refinements:
        sections.append({"title":"Refinement Recommendations","content":refinements[:5]})
    return build_report_envelope("WEEKLY_PLAYBOOK_REVIEW",environment,live_policy_version_id,
                                  "Weekly Playbook Review",sections,bullets)

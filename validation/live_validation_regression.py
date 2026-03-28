"""validation/live_validation_regression.py — Compare two JSON artifacts, flag drift."""
from __future__ import annotations
import json, sys
from pathlib import Path
from typing import Any

TRACKED_FIELDS = [
    "candidate_found","campaign_state","campaign_action","selected_transition_type",
    "best_path_code","best_path_score","alt_path_code","queue_priority_band",
    "queue_priority_score","ticket_ready",
]
SCORE_THRESHOLD = 5.0   # flag if best_path_score drifts by ±5 points
WARN_THRESHOLD  = 0     # flag if warning count increases

def load_report(path: str) -> dict[str,Any]:
    return json.loads(Path(path).read_text())

def _rows_by_symbol(report: dict) -> dict[str,dict]:
    return {r["symbol"]:r for r in report.get("rows",[])}

def compare_reports(old_path: str, new_path: str) -> dict[str,Any]:
    old=load_report(old_path); new=load_report(new_path)
    old_rows=_rows_by_symbol(old); new_rows=_rows_by_symbol(new)
    diffs=[]; changes=0

    for sym in sorted(set(old_rows)|set(new_rows)):
        o=old_rows.get(sym,{}); n=new_rows.get(sym,{})
        sym_diffs=[]
        for field in TRACKED_FIELDS:
            ov=o.get(field); nv=n.get(field)
            if ov!=nv:
                sym_diffs.append({"field":field,"old":ov,"new":nv})
                changes+=1
        # Score drift check
        os=o.get("best_path_score"); ns=n.get("best_path_score")
        if os is not None and ns is not None and abs(float(ns)-float(os))>SCORE_THRESHOLD:
            sym_diffs.append({"field":"best_path_score_drift","old":os,"new":ns,
                               "delta":round(float(ns)-float(os),4)})
            changes+=1
        # Warning count check
        ow=o.get("warning_count",0); nw=n.get("warning_count",0)
        if nw>ow:
            sym_diffs.append({"field":"warning_count_increased","old":ow,"new":nw})
            changes+=1
        if sym_diffs:
            diffs.append({"symbol":sym,"changes":sym_diffs})

    old_s=old.get("summary",{}); new_s=new.get("summary",{})
    summary_diffs={}
    for k in("candidate_found_count","ticket_ready_count","warning_count",
              "roll_ready_count","best_path_roll_count"):
        if old_s.get(k)!=new_s.get(k):
            summary_diffs[k]={"old":old_s.get(k),"new":new_s.get(k)}

    return {"total_changes":changes,"symbol_diffs":diffs,"summary_diffs":summary_diffs,
            "clean":changes==0 and not summary_diffs}

def render_regression_report(result: dict[str,Any]) -> str:
    lines=["REGRESSION COMPARISON"]
    if result["clean"]: lines.append("  ✓ No drift detected."); return "\n".join(lines)
    lines.append(f"  ✗ {result['total_changes']} changes detected")
    if result["summary_diffs"]:
        lines.append("  Summary changes:")
        for k,v in result["summary_diffs"].items():
            lines.append(f"    {k}: {v['old']} → {v['new']}")
    for sym_diff in result["symbol_diffs"]:
        lines.append(f"  {sym_diff['symbol']}:")
        for c in sym_diff["changes"]:
            lines.append(f"    {c['field']}: {c.get('old')} → {c.get('new')}")
    return "\n".join(lines)

if __name__=="__main__":
    if len(sys.argv)<3:
        print("Usage: python validation/live_validation_regression.py old.json new.json"); sys.exit(1)
    result=compare_reports(sys.argv[1],sys.argv[2])
    print(render_regression_report(result))
    sys.exit(0 if result["clean"] else 1)

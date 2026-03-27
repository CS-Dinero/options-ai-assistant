"""prune/pruning_renderer.py — Displays simplification candidates in the cockpit."""
from __future__ import annotations
import streamlit as st

REC_COLORS={"KEEP":"#22c55e","SIMPLIFY":"#f59e0b","MERGE":"#2563eb","DEMOTE":"#b45309","RETIRE":"#ef4444"}

def render_pruning_recommendations(recommendations: list[dict]) -> None:
    st.markdown("### ✂️ Simplification Recommendations")
    if not recommendations: st.info("No active pruning recommendations."); return
    import pandas as pd
    rows=[{"Family":r.get("component_family","?"),"Component":r.get("component_id","?"),
           "Rec":r.get("recommendation","?"),"Score":f'{r.get("simplify_score",0):.1f}',
           "Safety":f'{r.get("safety_to_change",0):.1f}',"Reason":r.get("reason","")[:60]}
          for r in sorted(recommendations,key=lambda x: x.get("simplify_score",0),reverse=True)]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

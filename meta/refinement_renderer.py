"""meta/refinement_renderer.py — Renders refinement recommendations in the cockpit."""
from __future__ import annotations
import streamlit as st

def render_refinements(refinements: list[dict]) -> None:
    st.markdown("### 🧬 Refinement Recommendations")
    if not refinements: st.info("No active refinement recommendations."); return
    import pandas as pd
    rows=[{"Signal":r.get("signal_type","?"),"Target":r.get("target_id","?"),
           "Type":r.get("refinement_type","?"),"Score":f'{r.get("refinement_score",0):.1f}',
           "Safety":f'{r.get("safety_score",0):.1f}',"State":r.get("state","?")}
          for r in sorted(refinements,key=lambda x: x.get("refinement_score",0),reverse=True)]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

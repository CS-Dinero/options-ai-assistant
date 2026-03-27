"""causal/causal_renderer.py — Renders causal review results."""
from __future__ import annotations
import streamlit as st

STRENGTH_COLORS={"STRONG":"#22c55e","MODERATE":"#f59e0b","WEAK":"#ef4444"}

def render_causal_review(report: dict) -> None:
    st.markdown("### 🔬 Causal Review")
    for b in report.get("summary_bullets",[]): st.caption(f"• {b}")
    for sec in report.get("sections",[]):
        with st.expander(sec.get("title","?")):
            c=sec.get("content")
            if isinstance(c,list):
                import pandas as pd; st.dataframe(pd.DataFrame(c),use_container_width=True,hide_index=True)
            elif isinstance(c,dict): st.json(c)
            else: st.write(str(c))

"""compare/path_renderer.py — Renders comparative paths in the cockpit."""
from __future__ import annotations
import streamlit as st

def render_path_comparison(ranked_paths: list[dict]) -> None:
    st.markdown("### ⚖️ Comparative Paths")
    if not ranked_paths: st.info("No comparative paths available."); return
    import pandas as pd
    rows=[{"Rank":i+1,"Path":p["path_code"],"Score":f'{p["path_total_score"]:.1f}',
           "Mandate Fit":f'{p.get("mandate_fit_score",0):.1f}',
           "Basis Recovery":f'{p.get("basis_recovery_score",0):.1f}',
           "Capital Eff.":f'{p.get("capital_efficiency_score",0):.1f}',
           "Tradeoff":p.get("tradeoff_note","")[:60]} for i,p in enumerate(ranked_paths)]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    if ranked_paths:
        best=ranked_paths[0]; alt=ranked_paths[1] if len(ranked_paths)>1 else None
        st.caption(f"✅ **{best['path_code']}** — {best.get('tradeoff_note','')}")
        if alt: st.caption(f"🔁 Alternative: **{alt['path_code']}** — {alt.get('tradeoff_note','')}")

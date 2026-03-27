"""twin/twin_renderer.py — Renders digital twin state in the cockpit."""
from __future__ import annotations
import streamlit as st

def render_twin_view(reconciliation: dict, comparison: dict) -> None:
    st.markdown("### 🔭 Simulation Ledger / Digital Twin")
    c1,c2,c3=st.columns(3)
    c1.metric("Recommended",reconciliation.get("recommended_path_code","—"))
    c2.metric("Approved",reconciliation.get("approved_path_code","—"))
    c3.metric("Executed",reconciliation.get("executed_path_code","—"))
    match_rec=reconciliation.get("recommendation_followed")
    match_exec=reconciliation.get("approval_executed_match")
    st.caption(f"Recommendation followed: {'✅' if match_rec else '⚠️ Override' if match_rec is False else '—'} | "
               f"Approval executed: {'✅' if match_exec else '⚠️ Drift' if match_exec is False else '—'}")
    if comparison.get("chosen_vs_counterfactual_delta") is not None:
        delta=comparison["chosen_vs_counterfactual_delta"]
        color="#22c55e" if delta>=0 else "#ef4444"
        st.markdown(f'<div style="padding:6px 12px;border-left:3px solid {color};background:#0f1117;border-radius:6px">'
                    f'Chosen <strong>{comparison.get("chosen_path_code")}</strong> vs '
                    f'next-best <strong>{comparison.get("next_best_counterfactual_path","—")}</strong>: '
                    f'<strong style="color:{color}">{delta:+.2f}</strong></div>',unsafe_allow_html=True)

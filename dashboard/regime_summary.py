"""dashboard/regime_summary.py — Top-of-screen regime band."""
from __future__ import annotations
import streamlit as st

REGIME_COLORS = {"premium_selling":"#15803d","neutral_time_spreads":"#2563eb",
                 "trend_directional":"#7c3aed","cautious_directional":"#b45309",
                 "defensive":"#dc2626","mixed":"#6b7280"}

def render_regime_summary(global_context: dict, symbol_contexts: list[dict]) -> None:
    vga=str(global_context.get("vga_environment","mixed"))
    color=REGIME_COLORS.get(vga,"#6b7280")
    gamma=global_context.get("gamma_regime","?"); iv=global_context.get("iv_regime","?")
    skew=global_context.get("skew_state","?"); term=global_context.get("term_structure","?")
    st.markdown(f'<div style="padding:10px 16px;border-radius:10px;background:{color};color:#fff;margin-bottom:10px">'
                f'<strong>VGA: {vga.upper().replace("_"," ")}</strong> &nbsp;|&nbsp; '
                f'Gamma: {gamma} &nbsp;|&nbsp; IV: {iv} &nbsp;|&nbsp; '
                f'Skew: {skew} &nbsp;|&nbsp; Term: {term}</div>', unsafe_allow_html=True)
    if symbol_contexts:
        import pandas as pd
        st.dataframe(pd.DataFrame([{"Symbol":s.get("symbol"),"VGA":s.get("vga_environment"),
            "Gamma":s.get("gamma_regime"),"IV":s.get("iv_regime"),
            "Preferred Family":s.get("preferred_structure_family",s.get("vga_environment","—"))}
            for s in symbol_contexts]), use_container_width=True, hide_index=True)

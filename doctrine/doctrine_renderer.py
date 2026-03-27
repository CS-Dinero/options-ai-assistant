"""doctrine/doctrine_renderer.py — Renders the charter and current doctrine tensions."""
from __future__ import annotations
import streamlit as st
from doctrine.principle_catalog import PRINCIPLE_CATALOG

def render_doctrine_view(charter: dict, doctrine_tensions: list[dict]|None=None) -> None:
    st.markdown("### 📜 Operating Charter / Doctrine")
    st.caption(f"**{charter.get('title')}** | Effective: {charter.get('effective_utc','')[:10]}")
    with st.expander(f"Active Principles ({len(charter.get('active_principles',[]))})"):
        for p in charter.get("active_principles",[]):
            desc=PRINCIPLE_CATALOG.get(p,{}).get("description","")
            pri=PRINCIPLE_CATALOG.get(p,{}).get("priority",0)
            st.caption(f"**[{pri}] {p}** — {desc}")
    with st.expander("Tradeoff Order (highest priority first)"):
        for i,p in enumerate(charter.get("tradeoff_order",[])):
            st.caption(f"{i+1}. {p}")
    tensions=doctrine_tensions or []
    if tensions:
        st.warning(f"⚠️ {len(tensions)} doctrine tension(s) active")
        for t in tensions: st.caption(f"• {t}")
    else:
        st.success("✅ No active doctrine tensions")

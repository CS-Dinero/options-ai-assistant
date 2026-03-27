"""mandate/mandate_renderer.py — Shows active mandate and its implications."""
from __future__ import annotations
import streamlit as st
from mandate.mandate_registry import MANDATE_REGISTRY

MANDATE_COLORS={"BASIS_RECOVERY":"#15803d","CAPITAL_PRESERVATION":"#b45309","EXECUTION_QUALITY":"#2563eb",
                "QUEUE_HEALTH":"#7c3aed","PLAYBOOK_PROMOTION_UTILIZATION":"#0891b2",
                "RISK_CONCENTRATION_REDUCTION":"#dc2626","POLICY_STABILITY":"#6b7280"}

def render_mandate_panel(active_mandate: str, mandate_note: str="") -> None:
    color=MANDATE_COLORS.get(active_mandate,"#6b7280")
    desc=MANDATE_REGISTRY.get(active_mandate,{}).get("description","")
    st.markdown(f'<div style="padding:8px 14px;border-radius:8px;border-left:4px solid {color};'
                f'background:#0f1117">'
                f'<strong style="color:{color}">⚑ {active_mandate}</strong> — {desc}</div>',
                unsafe_allow_html=True)
    if mandate_note: st.caption(mandate_note)

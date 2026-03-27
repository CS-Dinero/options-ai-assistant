"""risk/risk_envelope_renderer.py — Displays live capital posture."""
from __future__ import annotations
import streamlit as st

ENV_COLORS={"LOCKDOWN":"#ef4444","DEFENSIVE":"#f59e0b","NORMAL":"#2563eb","OFFENSIVE":"#22c55e"}
LABEL_COLORS={"NO_DEPLOY":"#ef4444","TOKEN":"#f59e0b","REDUCED":"#f59e0b","NORMAL":"#2563eb","EXPANDED":"#22c55e"}

def render_risk_envelope(active_envelope: str, capital_budget: dict,
                          capital_decision: dict|None=None) -> None:
    color=ENV_COLORS.get(active_envelope,"#6b7280")
    st.markdown(f'<div style="padding:8px 14px;border-left:4px solid {color};background:#0f1117;border-radius:8px">'
                f'<strong style="color:{color}">⚖ Risk Envelope: {active_envelope}</strong></div>',
                unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    c1.metric("Deployable Capital",f'${capital_budget.get("deployable_capital",0):,.0f}')
    c2.metric("Committed Risk",f'${capital_budget.get("committed_risk",0):,.0f}')
    c3.metric("Available Incremental",f'${capital_budget.get("available_incremental_risk",0):,.0f}')
    if capital_decision:
        lbl=capital_decision.get("capital_deployment_label","?")
        lc=LABEL_COLORS.get(lbl,"#6b7280")
        st.markdown(f'<div style="margin-top:6px;padding:6px 12px;border-left:3px solid {lc};background:#0f1117;border-radius:6px">'
                    f'<strong style="color:{lc}">Deployment: {lbl}</strong> — '
                    f'Contract add: {capital_decision.get("final_contract_add",0):.2f} '
                    f'(multiplier {capital_decision.get("raw_capital_multiplier",0):.3f}×)</div>',
                    unsafe_allow_html=True)

"""decision/decision_renderer.py — Renders decision journal and override analysis."""
from __future__ import annotations
import streamlit as st

def render_decision_journal(decisions: list[dict]) -> None:
    st.markdown("### 📓 Decision Journal")
    if not decisions: st.info("No recorded operator decisions yet."); return
    import pandas as pd
    rows=[{"ID":d.get("decision_id","")[:8],"Type":d.get("decision_type","?"),
           "Actor":d.get("actor","?"),"Env":d.get("environment","?"),
           "Agreement":((d.get("rationale") or {}).get("agreement_mode","?")),
           "Reason":((d.get("rationale") or {}).get("primary_reason_code","?")),
           "Time":d.get("timestamp_utc","")[:16]} for d in decisions[-25:]]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

def render_override_analysis(analysis: dict) -> None:
    st.markdown("### 🔄 Override Analysis")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**Agreement Modes**"); st.write(analysis.get("agreement_modes",{}))
    with c2:
        st.markdown("**Primary Reasons**"); st.write(analysis.get("primary_reason_counts",{}))
    ob=analysis.get("override_by_playbook",{})
    if ob: st.markdown("**Overrides by Playbook**"); st.write(ob)

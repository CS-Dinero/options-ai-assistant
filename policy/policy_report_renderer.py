"""policy/policy_report_renderer.py — Renders policy simulation diff in Streamlit."""
from __future__ import annotations
import streamlit as st

def render_policy_report(scenario_name: str, diff: dict) -> None:
    st.markdown(f"### 🧪 Policy Sim: **{scenario_name}**")
    movers=diff.get("queue_movers",[]); removed=diff.get("queue_removed",[])
    added=diff.get("queue_added",[]); changes=diff.get("commitment_changes",[])
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Queue Movers",len(movers)); c2.metric("Removed",len(removed))
    c3.metric("Added",len(added)); c4.metric("Commitment Δ",len(changes))
    import pandas as pd
    if movers:
        st.markdown("**Queue Movers**")
        st.dataframe(pd.DataFrame(movers),use_container_width=True,hide_index=True)
    if changes:
        st.markdown("**Capital / Execution Changes**")
        st.dataframe(pd.DataFrame(changes),use_container_width=True,hide_index=True)
    if not movers and not changes: st.success("No material changes under this scenario.")

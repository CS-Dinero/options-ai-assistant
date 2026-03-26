"""diagnostics/diagnostics_renderer.py — Renders observability report in Streamlit cockpit."""
from __future__ import annotations
import streamlit as st

def render_diagnostics_report(report: dict) -> None:
    st.markdown("### 🔍 Diagnostics")
    gate=report.get("gate_failures",{}); blocks=report.get("block_reasons",{}).get("reason_counts",{})
    q=report.get("queue_compression",{}); slip=report.get("slippage_hotspots",{})
    drag=report.get("playbook_drag",{}).get("playbook_drag",[]); pressure=report.get("policy_pressure",{})
    top_block=max(blocks,key=blocks.get) if blocks else "none"
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Top Block",top_block); c2.metric("Surface Fails",gate.get("surface_fail_count",0))
    c3.metric("Timing Fails",gate.get("timing_fail_count",0))
    c4.metric("Queue Compressed",q.get("compressed_count",0))
    c5,c6,c7=st.columns(3)
    c5.metric("Capital Blocks",pressure.get("capital_blocks",0))
    c6.metric("Reduced Commits",pressure.get("reduced_commitment_count",0))
    c7.metric("Queue Bias Total",f'{pressure.get("total_queue_bias",0):+.1f}')
    if slip.get("worst_symbol") or slip.get("worst_window"):
        st.markdown("**Slippage Hotspots**")
        s1,s2,s3=st.columns(3)
        s1.metric("Worst Symbol",slip.get("worst_symbol","—"))
        s2.metric("Worst Window",slip.get("worst_window","—"))
        s3.metric("Worst Policy",slip.get("worst_policy","—"))
    if drag:
        with st.expander(f"Playbook Drag ({len(drag)} entries)"):
            import pandas as pd
            st.dataframe(pd.DataFrame(drag[:10]),use_container_width=True,hide_index=True)

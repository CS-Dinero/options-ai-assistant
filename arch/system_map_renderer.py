"""arch/system_map_renderer.py — Renders the living architecture map."""
from __future__ import annotations
import streamlit as st

LAYER_COLORS={"DECISION":"#2563eb","INTELLIGENCE":"#7c3aed","GOVERNANCE":"#dc2626",
               "OPERATIONS":"#059669","HUMAN_SUPERVISION":"#d97706","EXECUTION_WORKFLOW":"#0891b2",
               "ADAPTATION":"#16a34a","ARCHITECTURE":"#6b7280"}

def render_system_map(system_map: dict) -> None:
    st.markdown("### 🗺 System Architecture Map")
    layers=system_map.get("layers",{}); components=system_map.get("components",{})

    # Compact component table grouped by layer
    import pandas as pd
    rows=[{"Layer":m.get("layer","?"),"Component":cid,"Kind":m.get("kind","?"),
           "Deps":len(m.get("dependencies",[])),
           "Pruning":m.get("pruning_state",{}).get("recommendation","—") if m.get("pruning_state") else "—",
           "Description":m.get("description","")[:60]}
          for cid,m in sorted(components.items(),key=lambda x: x[1].get("layer",""))]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

    with st.expander("Decision Flow"):
        st.caption(" → ".join(system_map.get("decision_flow",[])))
    with st.expander("Policy Flow"):
        st.caption(" → ".join(system_map.get("policy_flow",[])))
    with st.expander("Data Flows"):
        for f in system_map.get("dataflows",[]): st.caption(f"  {f['source']} → {f['target']}: {f['data']}")

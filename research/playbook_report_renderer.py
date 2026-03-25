"""research/playbook_report_renderer.py — Renders research results in Streamlit."""
from __future__ import annotations
import streamlit as st

def render_playbook_report(research_package: dict) -> None:
    st.markdown("### 🔬 Playbook Research")
    st.caption(f"Dataset: {research_package.get('dataset_count',0)} total | "
               f"{research_package.get('filtered_count',0)} filtered")
    stats=research_package.get("stats",{}).get("by_playbook",{})
    if not stats: st.info("No playbook research data yet — log and evaluate transitions first."); return
    import pandas as pd
    from playbooks.playbook_registry import PLAYBOOKS
    rows=[{"Code":c,"Name":PLAYBOOKS.get(c,{}).get("name",c),"N":v["count"],
           "Success%":f'{100*v["success_rate"]:.0f}%',"Outcome":f'{v["avg_outcome_score"]:.1f}',
           "Credit":f'${v["avg_transition_credit"]:.2f}',"Basis↓":f'${v["avg_basis_reduction"]:.2f}',
           "Fill":f'{v["avg_fill_score"]:.1f}',"Slip$":f'{v["avg_slippage_dollars"]:+.3f}',
           "Path":f'{v["avg_path_score"]:.1f}'} for c,v in stats.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

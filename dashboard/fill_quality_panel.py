"""dashboard/fill_quality_panel.py — Fill quality feedback panel."""
from __future__ import annotations
import streamlit as st

def render_fill_quality_panel(slippage_model: dict) -> None:
    st.markdown("### 📈 Fill Quality")
    if not slippage_model: st.info("No fill data yet."); return
    import pandas as pd
    for label, key in [("By Symbol","by_symbol"),("By Window","by_window"),("By Policy","by_policy")]:
        data=slippage_model.get(key,{})
        if data:
            st.markdown(f"**{label}**")
            st.dataframe(pd.DataFrame([{"Key":k,"Count":v["count"],
                "Avg Slip $":f'${v["avg_slippage_dollars"]:+.3f}',
                "Avg Fill":f'{v["avg_fill_score"]:.1f}'} for k,v in data.items()]),
                use_container_width=True, hide_index=True)

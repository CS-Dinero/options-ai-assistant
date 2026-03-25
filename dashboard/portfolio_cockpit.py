"""dashboard/portfolio_cockpit.py — Book-level posture panel."""
from __future__ import annotations
import streamlit as st

def render_portfolio_cockpit(portfolio_state: dict, exposure_metrics: dict) -> None:
    st.markdown("### 📊 Portfolio Posture")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Campaign Basis", f'${portfolio_state.get("total_campaign_basis",0):,.2f}')
    c2.metric("Unrealized PnL", f'${portfolio_state.get("total_unrealized_pnl",0):,.2f}')
    c3.metric("Bullish",  f'{100*exposure_metrics.get("bullish_ratio",0):.1f}%')
    c4.metric("Bearish",  f'{100*exposure_metrics.get("bearish_ratio",0):.1f}%')
    c5,c6,c7=st.columns(3)
    c5.metric("Top Symbol",   exposure_metrics.get("top_symbol","—"))
    c6.metric("Top Sym %",    f'{100*exposure_metrics.get("top_symbol_ratio",0):.1f}%')
    c7.metric("Top Structure",exposure_metrics.get("top_structure","—"))
    sym_b=portfolio_state.get("symbol_basis",{})
    if sym_b:
        with st.expander("Symbol basis detail"):
            import pandas as pd
            st.dataframe(pd.DataFrame([{"Symbol":k,"Basis":f'${v:.2f}'} for k,v in sym_b.items()]),
                         use_container_width=True,hide_index=True)

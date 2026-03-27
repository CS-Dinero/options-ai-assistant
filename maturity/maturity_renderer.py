"""maturity/maturity_renderer.py — Renders capability maturity scorecard."""
from __future__ import annotations
import streamlit as st

LEVEL_COLORS={"PROTOTYPE":"#ef4444","USABLE":"#f59e0b","STABLE":"#2563eb","GOVERNED":"#16a34a","SCALABLE":"#22c55e"}

def render_maturity_scorecard(results: dict) -> None:
    st.markdown("### 📊 Capability Maturity Scorecard")
    if not results: st.info("No maturity data yet."); return
    import pandas as pd
    rows=[{"Capability":cap,"Level":v.get("level","?"),"Score":f'{v.get("score",0):.1f}',
           "ROI":f'{v.get("signals",{}).get("avg_roi",0):.1f}',
           "Stability":f'{v.get("signals",{}).get("stability_score",0):.1f}',
           "Overrides":f'{v.get("signals",{}).get("override_rate",0)*100:.1f}%',
           "Layer":v.get("layer","?")} for cap,v in results.items()]
    df=pd.DataFrame(rows).sort_values("Score",ascending=False)
    st.dataframe(df,use_container_width=True,hide_index=True)
    sm=sum(1 for r in results.values() if r.get("level") in ("SCALABLE","GOVERNED"))
    st.caption(f"✅ {sm}/{len(results)} capabilities at GOVERNED or above — safe for capital reliance")

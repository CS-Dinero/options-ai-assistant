"""attribution/value_signal_engine.py — Measures positive contribution."""
from __future__ import annotations
from typing import Any

def _sf(row,k,d=0.0):
    try: return float(row.get(k,d))
    except: return d

def compute_value_signals(row: dict[str,Any]) -> dict[str,Any]:
    bb=_sf(row,"campaign_basis_before",_sf(row,"campaign_net_basis_before",0))
    ba=_sf(row,"campaign_basis_after",_sf(row,"campaign_net_basis_after",0))
    rb=_sf(row,"recovered_pct_before",0); ra=_sf(row,"recovered_pct_after",0)
    oc=_sf(row,"outcome_score",0); fs=_sf(row,"fill_score",_sf(row,"transition_latest_fill_score",0))
    sl=_sf(row,"slippage_dollars",_sf(row,"transition_latest_slippage_dollars",0))
    br=round(max(0,bb-ba),4); rg=round(max(0,ra-rb),4)
    vs=round(0.30*min(100,br*20)+0.20*min(100,rg*3)+0.30*oc+0.15*fs+0.05*max(0,100+sl*100),2)
    return {"basis_reduction":br,"recovered_gain":rg,"outcome_score":oc,
            "fill_score":fs,"slippage_dollars":sl,"value_score":vs}

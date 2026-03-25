"""
engines/vertical_width_optimizer.py
Width-grid optimizer for vertical credit spread conversions.
Tests multiple spread widths per symbol rather than assuming one fixed width.

search_vertical_width_candidates() → ranked list of REPLACE_LONG credit spread candidates
"""
from __future__ import annotations
from typing import Any

WIDTH_GRID: dict = {
    "SPY":  [2.0,3.0,5.0,10.0],
    "QQQ":  [2.0,3.0,5.0,10.0],
    "IWM":  [2.0,3.0,5.0],
    "AAPL": [2.5,5.0,10.0],
    "MSFT": [2.5,5.0,10.0],
    "TSLA": [5.0,10.0,20.0],
    "NVDA": [5.0,10.0,15.0],
    "AMD":  [2.5,5.0,10.0],
}
DEFAULT_WIDTH_GRID = [5.0]

def _sf(v,d=0.0):
    try: return float(v) if v not in (None,"","—") else d
    except: return d

def _safe_mid(c):
    m=_sf(c.get("mid")); return m if m>0 else round((_sf(c.get("bid"))+_sf(c.get("ask")))/2,4)

def _ba_pct(c):
    m=_safe_mid(c); return 1.0 if m<=0 else (_sf(c.get("ask"))-_sf(c.get("bid")))/m

def _close_long(leg):  return _sf(leg.get("bid")) or _safe_mid(leg)*0.95
def _close_short(leg): return _sf(leg.get("ask")) or _safe_mid(leg)*1.05
def _open_short(leg):  return _sf(leg.get("bid")) or _safe_mid(leg)*0.95
def _open_long(leg):   return _sf(leg.get("ask")) or _safe_mid(leg)*1.05

def _trans_credit(cur_long, cur_short, new_long, new_short):
    return round(_close_long(cur_long)-_close_short(cur_short)-_open_long(new_long)+_open_short(new_short), 4)

def _width_eff(credit, width):
    if width<=0: return 0.0
    return max(0.0, min(100.0, (credit/width)*200.0))

def _credit_score(credit, min_c):
    if min_c<=0: return 100.0
    if credit<=0: return 0.0
    return max(0.0, min(100.0, (credit/min_c)*100.0))

def _liq_score(ns, nl, max_ba):
    s = max(0.0,100*(1-_ba_pct(ns)/max_ba)) if max_ba>0 else 0.0
    l = max(0.0,100*(1-_ba_pct(nl)/max_ba)) if max_ba>0 else 0.0
    return round((s+l)/2,2)

def _short_quality(ns):
    da=abs(_sf(ns.get("delta"))); dte=int(_sf(ns.get("dte"))); m=_safe_mid(ns)
    s=0.0
    if 0.18<=da<=0.35: s+=45
    elif 0.10<=da<=0.42: s+=30
    if 7<=dte<=21: s+=30
    elif 5<=dte<=28: s+=20
    if m>=0.60: s+=25
    elif m>=0.35: s+=15
    return round(min(100,s),2)

def _assign_safety(ns, spot):
    opt=str(ns.get("option_type","")).lower(); k=_sf(ns.get("strike")); dte=int(_sf(ns.get("dte")))
    itm=max(0.0,(spot-k)/spot) if opt=="call" and spot>0 else max(0.0,(k-spot)/k) if opt=="put" and k>0 else 0.0
    s=100.0
    if itm>0.01: s-=25
    if itm>0.03: s-=35
    if dte<=7: s-=15
    if dte<=3: s-=15
    return round(max(0,s),2)

def _find_long_for_width(contracts, opt_type, short_k, width, direction, exp, max_ba):
    best,bd=None,1e9
    for c in contracts:
        if str(c.get("option_type","")).lower()!=opt_type: continue
        exp_c=str(c.get("expiry") or c.get("expiration",""))
        if exp_c!=exp: continue
        if _ba_pct(c)>max_ba: continue
        k=_sf(c.get("strike"))
        if direction=="below" and k>=short_k: continue
        if direction=="above" and k<=short_k: continue
        diff=abs(abs(short_k-k)-width)
        if diff<bd: best,bd=c,diff
    return best

def search_vertical_width_candidates(
    current_position: dict[str, Any],
    chain_bundle: dict[str, list[dict]],
    market_context: dict[str, Any],
    max_ba_pct: float,
    min_credit: float,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    symbol    = str(current_position.get("symbol","")).upper()
    cur_long  = current_position.get("long_leg",{})
    cur_short = current_position.get("short_leg",{})
    cur_type  = str(cur_short.get("option_type","")).lower()
    spot      = _sf(market_context.get("spot") or market_context.get("spot_price"))
    widths    = WIDTH_GRID.get(symbol, DEFAULT_WIDTH_GRID)
    key       = "puts" if cur_type=="put" else "calls"
    action    = "CONVERT_TO_BULL_PUT_SPREAD" if cur_type=="put" else "CONVERT_TO_BEAR_CALL_SPREAD"
    direction = "below" if cur_type=="put" else "above"
    out=[]

    for ns in chain_bundle.get(key,[]):
        da=abs(_sf(ns.get("delta"))); dte=int(_sf(ns.get("dte")))
        if not (0.18<=da<=0.35): continue
        if not (7<=dte<=21): continue
        if _ba_pct(ns)>max_ba_pct: continue
        sk  = _sf(ns.get("strike"))
        exp = str(ns.get("expiry") or ns.get("expiration",""))
        for w in widths:
            nl = _find_long_for_width(chain_bundle.get(key,[]), cur_type, sk, w, direction, exp, max_ba_pct)
            if nl is None: continue
            credit   = _trans_credit(cur_long, cur_short, nl, ns)
            liq      = _liq_score(ns, nl, max_ba_pct)
            sq       = _short_quality(ns)
            asn      = _assign_safety(ns, spot)
            cs       = _credit_score(credit, min_credit)
            we       = _width_eff(credit, w)
            vws      = round(0.30*cs + 0.25*we + 0.20*liq + 0.15*sq + 0.10*asn, 2)
            actual_w = abs(sk - _sf(nl.get("strike")))
            out.append({
                "action": action,
                "type":   "bull_put_spread" if cur_type=="put" else "bear_call_spread",
                "rebuild_class": "REPLACE_LONG",
                "long_leg": nl, "short_leg": ns,
                "target_width": w, "actual_width": actual_w,
                "transition_net_credit":      credit,
                "current_risk_basis":         actual_w,
                "expected_next_cycle_credit": round(_safe_mid(ns)*0.60, 4),
                "structure_score":            sq,
                "assignment_risk_score":      round(100-asn, 2),
                "liquidity_score":            liq,
                "search_rank_score":          vws,
                "search_notes": [f"width={w} actual={actual_w:.1f} credit={credit:.2f}"],
            })
    return sorted(out, key=lambda x: x["search_rank_score"], reverse=True)[:top_n]

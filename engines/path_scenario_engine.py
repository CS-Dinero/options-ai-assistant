"""
engines/path_scenario_engine.py
Generates a small set of realistic forward paths for scenario-based scoring.
Directional scenarios are inverted for bearish structures.
"""
from __future__ import annotations
from typing import Any

SCENARIO_LIBRARY = {
    "FLAT":           {"spot_move_pct":  0.000, "iv_shift": -0.010, "gamma_regime": "positive", "label": "Flat / pinned"},
    "FAVORABLE_SMALL":{"spot_move_pct":  0.015, "iv_shift": -0.005, "gamma_regime": "neutral",  "label": "Modest favorable move"},
    "ADVERSE_SMALL":  {"spot_move_pct": -0.015, "iv_shift":  0.010, "gamma_regime": "neutral",  "label": "Modest adverse move"},
    "TREND_EXTENSION":{"spot_move_pct":  0.030, "iv_shift":  0.005, "gamma_regime": "negative", "label": "Trend extension"},
    "MEAN_REVERT_PIN":{"spot_move_pct": -0.005, "iv_shift": -0.015, "gamma_regime": "positive", "label": "Mean reversion / pin"},
}

def _infer_side(candidate: dict) -> str:
    action = str(candidate.get("action",""))
    if "CALL" in action or "BULL" in action: return "BULLISH"
    if "PUT"  in action or "BEAR" in action: return "BEARISH"
    opt = str((candidate.get("short_leg") or {}).get("option_type","")).lower()
    if opt=="call": return "BULLISH"
    if opt=="put":  return "BEARISH"
    return "NEUTRAL"

def generate_path_scenarios(
    current_position:    dict[str, Any],
    candidate_structure: dict[str, Any],
    market_context:      dict[str, Any],
) -> list[dict[str, Any]]:
    spot = float(market_context.get("spot") or market_context.get("spot_price",100))
    side = _infer_side(candidate_structure)
    out  = []
    for name, s in SCENARIO_LIBRARY.items():
        mp = float(s["spot_move_pct"])
        if side == "BEARISH":
            scenario_spot = spot*(1-abs(mp)) if name in ("FAVORABLE_SMALL","TREND_EXTENSION") else spot*(1+abs(mp))
        else:
            scenario_spot = spot*(1+mp)
        out.append({
            "scenario_name":  name,
            "label":          s["label"],
            "spot_now":       spot,
            "spot_scenario":  round(scenario_spot,2),
            "spot_move_pct":  round(scenario_spot/spot-1,4) if spot>0 else 0.0,
            "iv_shift":       float(s["iv_shift"]),
            "gamma_regime":   s["gamma_regime"],
            "directional_side": side,
        })
    return out

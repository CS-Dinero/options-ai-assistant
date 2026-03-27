"""risk/risk_envelope_registry.py — Capital posture band definitions."""
RISK_ENVELOPE_REGISTRY: dict = {
    "LOCKDOWN":  {"description":"Only urgent de-risking. Minimal new risk.",
                  "base_size_multiplier":0.25,"max_symbol_exposure":0.15,"max_new_risk_per_action":0.25},
    "DEFENSIVE": {"description":"Reduced sizing and tighter limits.",
                  "base_size_multiplier":0.60,"max_symbol_exposure":0.20,"max_new_risk_per_action":0.50},
    "NORMAL":    {"description":"Standard operating capital posture.",
                  "base_size_multiplier":1.00,"max_symbol_exposure":0.30,"max_new_risk_per_action":1.00},
    "OFFENSIVE": {"description":"Expanded but bounded sizing when conditions are strong.",
                  "base_size_multiplier":1.15,"max_symbol_exposure":0.35,"max_new_risk_per_action":1.15},
}

def get_envelope(envelope: str) -> dict:
    return RISK_ENVELOPE_REGISTRY.get(str(envelope).upper(), RISK_ENVELOPE_REGISTRY["NORMAL"])

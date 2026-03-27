"""maturity/maturity_registry.py — Maturity level definitions."""
MATURITY_REGISTRY: dict = {
    "PROTOTYPE": {"score_min":0,  "description":"Experimental, not safe for capital reliance."},
    "USABLE":    {"score_min":30, "description":"Functional but requires supervision."},
    "STABLE":    {"score_min":50, "description":"Reliable under normal conditions."},
    "GOVERNED":  {"score_min":70, "description":"Well-controlled with review and validation."},
    "SCALABLE":  {"score_min":85, "description":"Consistent, efficient, and safe to scale."},
}

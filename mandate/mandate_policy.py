"""mandate/mandate_policy.py — Per-mandate scoring weight biases."""
from __future__ import annotations

MANDATE_POLICY: dict = {
    "BASIS_RECOVERY": {
        "queue_bias":   {"campaign_improvement_score":1.20,"recycling_score":1.15,"fill_score":0.95,
                         "allocator_score":1.00,"timing_score":1.00,"surface_score":1.00},
        "capital_bias": {"size_multiplier":1.05,"promoted_bonus":1.05},
    },
    "CAPITAL_PRESERVATION": {
        "queue_bias":   {"campaign_improvement_score":0.95,"recycling_score":1.20,"fill_score":1.05,
                         "allocator_score":1.15,"timing_score":1.05,"surface_score":1.05},
        "capital_bias": {"size_multiplier":0.80,"promoted_bonus":1.00},
    },
    "EXECUTION_QUALITY": {
        "queue_bias":   {"campaign_improvement_score":0.95,"recycling_score":0.95,"fill_score":1.25,
                         "allocator_score":1.00,"timing_score":1.15,"surface_score":1.20},
        "capital_bias": {"size_multiplier":0.90,"promoted_bonus":1.00},
    },
    "QUEUE_HEALTH": {
        "queue_bias":   {"campaign_improvement_score":1.00,"recycling_score":1.00,"fill_score":1.00,
                         "allocator_score":0.95,"timing_score":0.95,"surface_score":0.95},
        "capital_bias": {"size_multiplier":1.00,"promoted_bonus":1.00},
    },
    "PLAYBOOK_PROMOTION_UTILIZATION": {
        "queue_bias":   {"campaign_improvement_score":1.00,"recycling_score":1.00,"fill_score":1.00,
                         "allocator_score":1.00,"timing_score":1.00,"surface_score":1.00},
        "capital_bias": {"size_multiplier":1.05,"promoted_bonus":1.15},
    },
    "RISK_CONCENTRATION_REDUCTION": {
        "queue_bias":   {"campaign_improvement_score":0.95,"recycling_score":1.00,"fill_score":1.00,
                         "allocator_score":1.25,"timing_score":1.00,"surface_score":1.00},
        "capital_bias": {"size_multiplier":0.85,"promoted_bonus":1.00},
    },
    "POLICY_STABILITY": {
        "queue_bias":   {"campaign_improvement_score":1.00,"recycling_score":1.00,"fill_score":1.05,
                         "allocator_score":1.05,"timing_score":1.00,"surface_score":1.00},
        "capital_bias": {"size_multiplier":0.90,"promoted_bonus":1.00},
    },
}

def get_mandate_policy(mandate: str) -> dict:
    return MANDATE_POLICY.get(str(mandate), MANDATE_POLICY["BASIS_RECOVERY"])

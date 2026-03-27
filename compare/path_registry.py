"""compare/path_registry.py — Forward-plan path classes."""
PATH_REGISTRY: dict = {
    "CONTINUE_HARVEST": {"description":"Continue harvesting the current structure without major simplification."},
    "ROLL_SAME_SIDE":   {"description":"Roll the short same-side and preserve the current campaign shape."},
    "COLLAPSE_TO_SPREAD":{"description":"Simplify into a defined-risk spread."},
    "BANK_AND_REDUCE":  {"description":"Reduce exposure and lock in campaign progress."},
    "DEFER_AND_WAIT":   {"description":"Wait for stronger execution conditions before acting."},
}

"""doctrine/doctrine_registry.py — Constitutional layer object definitions."""
DOCTRINE_REGISTRY: dict = {
    "OPERATING_CHARTER":         {"description":"Top-level governing doctrine for platform behavior."},
    "DOCTRINE_PRINCIPLE":        {"description":"Durable principle that outlasts local policy changes."},
    "DOCTRINE_CONSTRAINT":       {"description":"Operationalized rule derived from doctrine."},
    "TRADEOFF_RULE":             {"description":"Explicit ordering of acceptable tradeoffs."},
    "DOCTRINE_EXCEPTION_REQUEST":{"description":"Formal request to violate or suspend a doctrine rule."},
}

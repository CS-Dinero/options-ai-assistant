"""doctrine/principle_catalog.py — Durable operating principles. Few, load-bearing, stable."""
PRINCIPLE_CATALOG: dict = {
    "CAPITAL_PRESERVATION_FIRST":              {"description":"The platform must not pursue higher throughput by tolerating avoidable capital damage.","priority":100},
    "LIVE_SAFETY_OVER_SPEED":                  {"description":"LIVE behavior must remain slower and safer rather than faster and less governed.","priority":95},
    "HUMAN_ACCOUNTABILITY_FOR_LIVE_CHANGES":   {"description":"Material live changes require explicit human responsibility.","priority":94},
    "GOVERNANCE_OVER_CONVENIENCE":             {"description":"The platform must not simplify away necessary review, approval, or traceability.","priority":92},
    "REVERSIBILITY_FOR_HIGH_BLAST_RADIUS":     {"description":"Broad structural or live changes must remain reversible.","priority":90},
    "EXECUTION_INTEGRITY_OVER_QUEUE_VOLUME":   {"description":"The platform must not expand opportunity count by degrading execution discipline.","priority":88},
    "EVIDENCE_OVER_NOVELTY":                   {"description":"New ideas must earn influence through evidence, not attractiveness.","priority":84},
    "TRANSPARENCY_OVER_HIDDEN_OPTIMIZATION":   {"description":"The system must explain meaningful tradeoffs and not hide them inside opaque scoring.","priority":80},
}
DEFAULT_TRADEOFF_ORDER = ["CAPITAL_PRESERVATION_FIRST","LIVE_SAFETY_OVER_SPEED",
                           "HUMAN_ACCOUNTABILITY_FOR_LIVE_CHANGES","GOVERNANCE_OVER_CONVENIENCE",
                           "REVERSIBILITY_FOR_HIGH_BLAST_RADIUS","EXECUTION_INTEGRITY_OVER_QUEUE_VOLUME",
                           "EVIDENCE_OVER_NOVELTY","TRANSPARENCY_OVER_HIDDEN_OPTIMIZATION"]

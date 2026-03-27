"""knowledge/knowledge_schema.py — Canonical knowledge record key definitions."""
KNOWLEDGE_SCHEMA_KEYS: dict = {
    "required":["knowledge_id","environment","knowledge_type","status","confidence",
                "source_family","source_object_ids","subject_type","subject_id",
                "summary","details","tags","created_utc"]
}
CONFIDENCE_LEVELS = ["LOW","MEDIUM","HIGH"]
STATUS_LEVELS     = ["ACTIVE","UNDER_REVIEW","ARCHIVED"]

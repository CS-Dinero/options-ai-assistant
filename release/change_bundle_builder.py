"""release/change_bundle_builder.py — Groups related changes into one coherent release bundle."""
from __future__ import annotations
from typing import Any

def build_change_bundle(bundle_type: str, title: str, rationale: str,
                         included_changes: list[dict[str,Any]]) -> dict[str,Any]:
    return {"bundle_type":bundle_type,"title":title,"rationale":rationale,"included_changes":included_changes}

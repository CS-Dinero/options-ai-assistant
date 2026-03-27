"""maturity/maturity_report_builder.py — Builds capability maturity scorecard."""
from __future__ import annotations
from typing import Any

def build_maturity_report(results: dict[str,Any]) -> dict[str,Any]:
    return {"report_type":"MATURITY_SCORECARD","capabilities":results,
            "summary":{"scalable_count":sum(1 for r in results.values() if r.get("level")=="SCALABLE"),
                       "governed_count":sum(1 for r in results.values() if r.get("level")=="GOVERNED"),
                       "stable_count":sum(1 for r in results.values() if r.get("level")=="STABLE"),
                       "weak_count":sum(1 for r in results.values() if r.get("level") in("PROTOTYPE","USABLE"))}}

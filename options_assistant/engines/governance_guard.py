"""
engines/governance_guard.py
Policy constraints that prevent config_patcher from setting parameters
outside safe operating bounds.

DEFAULT_GOVERNANCE_RULES define hard min/max floors and ceilings.
evaluate_patch_payload() runs every suggestion through the rules and
returns approved/rejected lists with structured GuardDecision records.

No suggestions are blocked silently — every decision has a status and reason.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class GuardRule:
    parameter:      str
    min_value:      Optional[float] = None
    max_value:      Optional[float] = None
    allowed_values: Optional[list]  = None
    description:    str             = ""


@dataclass
class GuardDecision:
    parameter:       str
    current_value:   Any
    requested_value: Any
    allowed:         bool
    status:          str   # APPROVED | NO_RULE | REJECTED_BELOW_MIN | REJECTED_ABOVE_MAX | REJECTED_ALLOWED_VALUES
    reason:          str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────
# DEFAULT POLICY
# ─────────────────────────────────────────────

DEFAULT_GOVERNANCE_RULES: dict[str, GuardRule] = {
    "filters.credit_score_threshold": GuardRule(
        parameter="filters.credit_score_threshold",
        min_value=68.0, max_value=90.0,
        description="Keep credit threshold in conservative quality band [68–90].",
    ),
    "filters.calendar_score_threshold": GuardRule(
        parameter="filters.calendar_score_threshold",
        min_value=68.0, max_value=88.0,
        description="Keep calendar threshold in controlled quality band [68–88].",
    ),
    "risk.reserve_for_calendars_pct": GuardRule(
        parameter="risk.reserve_for_calendars_pct",
        min_value=0.10, max_value=0.35,
        description="Prevent over-allocation to calendars [10–35%].",
    ),
    "risk.max_trades_per_symbol": GuardRule(
        parameter="risk.max_trades_per_symbol",
        min_value=1.0, max_value=3.0,
        description="Limit symbol concentration [1–3 trades].",
    ),
    "credit_spreads.short_delta_min": GuardRule(
        parameter="credit_spreads.short_delta_min",
        min_value=0.10, max_value=0.20,
        description="Short delta floor within defined-risk norms [0.10–0.20].",
    ),
    "credit_spreads.short_delta_max": GuardRule(
        parameter="credit_spreads.short_delta_max",
        min_value=0.16, max_value=0.30,
        description="Short delta ceiling within defined-risk norms [0.16–0.30].",
    ),
    "risk.max_total_portfolio_risk_pct": GuardRule(
        parameter="risk.max_total_portfolio_risk_pct",
        min_value=0.01, max_value=0.05,
        description="Portfolio risk cap must stay in [1–5%].",
    ),
    "risk.max_symbol_risk_pct": GuardRule(
        parameter="risk.max_symbol_risk_pct",
        min_value=0.005, max_value=0.03,
        description="Per-symbol risk cap must stay in [0.5–3%].",
    ),
    "risk.allocation_min_trade_score": GuardRule(
        parameter="risk.allocation_min_trade_score",
        min_value=65.0, max_value=88.0,
        description="Allocation gate score must stay in [65–88].",
    ),
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _deep_get(cfg: dict[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _sf(v: Any) -> Optional[float]:
    try:
        return float(v) if v not in (None, "", "—") else None
    except Exception:
        return None


# ─────────────────────────────────────────────
# CORE VALIDATOR
# ─────────────────────────────────────────────

def validate_parameter_change(
    *,
    parameter:       str,
    current_value:   Any,
    requested_value: Any,
    rules:           dict[str, GuardRule] | None = None,
) -> GuardDecision:
    active = rules or DEFAULT_GOVERNANCE_RULES
    rule   = active.get(parameter)

    if rule is None:
        return GuardDecision(parameter, current_value, requested_value,
                             True, "NO_RULE",
                             "No governance rule — allowed by default.")

    if rule.allowed_values is not None and requested_value not in rule.allowed_values:
        return GuardDecision(parameter, current_value, requested_value,
                             False, "REJECTED_ALLOWED_VALUES",
                             f"Must be one of {rule.allowed_values}.")

    num = _sf(requested_value)
    if num is not None:
        if rule.min_value is not None and num < rule.min_value:
            return GuardDecision(parameter, current_value, requested_value,
                                 False, "REJECTED_BELOW_MIN",
                                 f"{requested_value} < minimum {rule.min_value}. {rule.description}")
        if rule.max_value is not None and num > rule.max_value:
            return GuardDecision(parameter, current_value, requested_value,
                                 False, "REJECTED_ABOVE_MAX",
                                 f"{requested_value} > maximum {rule.max_value}. {rule.description}")

    return GuardDecision(parameter, current_value, requested_value,
                         True, "APPROVED",
                         rule.description or "Approved by governance guard.")


# ─────────────────────────────────────────────
# BATCH EVALUATOR
# ─────────────────────────────────────────────

def evaluate_patch_payload(
    *,
    config:          dict[str, Any],
    tuning_payload:  dict[str, Any],
    rules:           dict[str, GuardRule] | None = None,
) -> dict[str, Any]:
    decisions = []
    for s in tuning_payload.get("suggestions", []):
        param = s.get("parameter")
        if not param:
            continue
        d = validate_parameter_change(
            parameter=param,
            current_value=_deep_get(config, param),
            requested_value=s.get("suggested_value"),
            rules=rules,
        )
        row = d.to_dict()
        row["confidence"] = float(s.get("confidence", 0.0))
        row["direction"]  = str(s.get("direction", ""))
        row["rationale"]  = str(s.get("rationale", ""))
        row["evidence"]   = s.get("evidence", {})
        decisions.append(row)

    approved = [x for x in decisions if x["allowed"]]
    rejected = [x for x in decisions if not x["allowed"]]
    return {"approved_count": len(approved), "rejected_count": len(rejected),
            "approved": approved, "rejected": rejected, "all": decisions}


# ─────────────────────────────────────────────
# POLICY SUMMARY
# ─────────────────────────────────────────────

def build_governance_policy_summary(
    rules: dict[str, GuardRule] | None = None,
) -> list[dict[str, Any]]:
    active = rules or DEFAULT_GOVERNANCE_RULES
    return [{"parameter": r.parameter, "min": r.min_value, "max": r.max_value,
             "allowed_values": r.allowed_values, "description": r.description}
            for r in active.values()]

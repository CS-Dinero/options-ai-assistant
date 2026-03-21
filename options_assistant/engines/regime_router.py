"""
engines/regime_router.py
Regime-aware routing layer — sits between context_builder and strategy selection.

Classifies the current market environment into a RegimeDecision that carries:
  - which strategies are allowed (primary / secondary)
  - dynamic score thresholds (tighter in mixed, looser in premium_selling)
  - position size multiplier (reduce in uncertain regimes)
  - rationale + UI labels for dashboard display

Maps to v15b VGA environments:
  premium_selling      → PREMIUM SELLING     (credit spreads first)
  neutral_time_spreads → NEUTRAL TIME SPREADS (calendars first)
  cautious_directional → MIXED               (reduce size)
  trend_directional    → ACCELERATION RISK   (stand down or directional)
  mixed                → MIXED               (selective only)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Literal


RegimeName = Literal[
    "premium_selling",
    "neutral_time_spreads",
    "cautious_directional",
    "trend_directional",
    "mixed",
    "no_trade",
]


@dataclass
class RegimeDecision:
    regime:               RegimeName
    primary_strategies:   list[str]
    secondary_strategies: list[str]
    trade_bias:           str
    confidence:           float
    rationale:            str
    ui_label:             str
    ui_subtitle:          str
    # Routing directives
    credit_threshold:     float = 75.0
    calendar_threshold:   float = 72.0
    size_multiplier:      float = 1.0
    allowed_strategies:   list[str] = field(default_factory=list)
    notes:                list[str] = field(default_factory=list)

    def strategy_allowed(self, strategy_type: str) -> bool:
        if not self.allowed_strategies:
            return True
        return strategy_type in self.allowed_strategies

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────
# REGIME BUILDERS
# ─────────────────────────────────────────────

def _premium_selling() -> RegimeDecision:
    return RegimeDecision(
        regime="premium_selling",
        primary_strategies=["bull_put", "bear_call"],
        secondary_strategies=["calendar", "diagonal"],
        trade_bias="NEUTRAL_TO_RANGE",
        confidence=0.88,
        rationale=(
            "Positive gamma + elevated IV + flat/contango term structure. "
            "Dealer pinning is dominant — sell premium outside EM boundaries."
        ),
        ui_label="PREMIUM SELLING",
        ui_subtitle="Credit spreads preferred · Calendars secondary in ±0.5 EM zone",
        credit_threshold=75.0,
        calendar_threshold=74.0,
        size_multiplier=1.0,
        allowed_strategies=["bull_put", "bear_call", "calendar", "diagonal", "double_diagonal"],
        notes=[
            "Deploy bull put below lower EM and bear call above upper EM.",
            "Calendars allowed only in the ±0.5 EM pin zone.",
            "Delta targets: 0.15–0.20 on short legs.",
        ],
    )


def _neutral_time_spreads() -> RegimeDecision:
    return RegimeDecision(
        regime="neutral_time_spreads",
        primary_strategies=["calendar", "diagonal"],
        secondary_strategies=["bull_put", "bear_call"],
        trade_bias="NEUTRAL_PINNING",
        confidence=0.80,
        rationale=(
            "Positive gamma with supportive term structure. "
            "Price compression favors time-spread theta capture over directional premium."
        ),
        ui_label="NEUTRAL TIME SPREADS",
        ui_subtitle="Calendars preferred · Credit spreads secondary",
        credit_threshold=78.0,    # tighter — credit spreads are secondary
        calendar_threshold=70.0,  # looser  — calendars are primary
        size_multiplier=0.90,
        allowed_strategies=["calendar", "diagonal", "double_diagonal", "bull_put", "bear_call"],
        notes=[
            "Enter ATM calendar short 7–10 DTE, long 45–60 DTE.",
            "Convert to diagonal if price drifts ≥0.35 EM from center.",
            "Reduce credit spread size — environment favors time spreads.",
        ],
    )


def _cautious_directional() -> RegimeDecision:
    return RegimeDecision(
        regime="cautious_directional",
        primary_strategies=["bull_call_debit", "bear_put_debit"],
        secondary_strategies=["bull_put", "bear_call"],
        trade_bias="SMALL_DIRECTIONAL",
        confidence=0.68,
        rationale=(
            "Gamma near flip level or uncertain regime. "
            "Small debit spreads with defined risk are preferred over full premium deployment."
        ),
        ui_label="CAUTIOUS DIRECTIONAL",
        ui_subtitle="Small debit spreads only · Reduce position size",
        credit_threshold=82.0,    # very tight — credit spreads need strong setup
        calendar_threshold=90.0,  # calendars not preferred here
        size_multiplier=0.50,
        allowed_strategies=["bull_call_debit", "bear_put_debit", "bull_put", "bear_call"],
        notes=[
            "Use half normal position size.",
            "Avoid ATM calendars — gamma instability works against time spreads.",
            "Only take credit spreads with score ≥82.",
        ],
    )


def _trend_directional() -> RegimeDecision:
    return RegimeDecision(
        regime="trend_directional",
        primary_strategies=["bull_call_debit", "bear_put_debit", "diagonal"],
        secondary_strategies=[],
        trade_bias="DIRECTIONAL",
        confidence=0.75,
        rationale=(
            "Negative gamma — dealer hedging amplifies price moves. "
            "Directional debit spreads and diagonals are preferred; avoid premium selling."
        ),
        ui_label="TREND DIRECTIONAL",
        ui_subtitle="Debit spreads + diagonals · Avoid credit spreads",
        credit_threshold=95.0,    # effectively blocked
        calendar_threshold=98.0,  # effectively blocked
        size_multiplier=0.75,
        allowed_strategies=["bull_call_debit", "bear_put_debit", "diagonal"],
        notes=[
            "Negative gamma = acceleration risk for short premium.",
            "No calendars — gamma instability destroys theta edge.",
            "Use directional debit spreads aligned with trend.",
        ],
    )


def _mixed() -> RegimeDecision:
    return RegimeDecision(
        regime="mixed",
        primary_strategies=["bull_put", "bear_call"],
        secondary_strategies=[],
        trade_bias="SELECTIVE",
        confidence=0.58,
        rationale=(
            "Mixed signals — some conditions present but not clean enough for full deployment. "
            "Only take highest-conviction setups with reduced size."
        ),
        ui_label="MIXED / UNCLEAR",
        ui_subtitle="Strongest setups only · Half size",
        credit_threshold=82.0,
        calendar_threshold=88.0,
        size_multiplier=0.50,
        allowed_strategies=["bull_put", "bear_call"],
        notes=[
            "Score threshold raised — only STRONG trades qualify.",
            "Reduce to half normal position size.",
            "No calendars until environment clarifies.",
        ],
    )


def _no_trade() -> RegimeDecision:
    return RegimeDecision(
        regime="no_trade",
        primary_strategies=[],
        secondary_strategies=[],
        trade_bias="NONE",
        confidence=0.90,
        rationale="Environment falls outside Phase 1 playbook. Stand down.",
        ui_label="NO TRADE",
        ui_subtitle="Stand down until conditions improve",
        credit_threshold=100.0,
        calendar_threshold=100.0,
        size_multiplier=0.0,
        allowed_strategies=[],
        notes=["No trades should be taken in this environment."],
    )


# ─────────────────────────────────────────────
# CLASSIFIER
# ─────────────────────────────────────────────

def classify_regime(derived: dict[str, Any]) -> RegimeDecision:
    """
    Classify the current regime from the v15b derived context dict.

    Input is the output of engines/context_builder.build_derived() —
    uses vga_environment as primary signal, with gamma_regime as safety override.
    """
    vga         = str(derived.get("vga_environment", "mixed")).lower()
    gamma_r     = str(derived.get("gamma_regime", "neutral")).lower()
    em          = float(derived.get("expected_move", 0))

    # Spot may live in market dict or be reconstructed from EM boundaries
    spot = float(derived.get("spot_price") or derived.get("spot") or 0)
    if spot <= 0:
        upper = float(derived.get("upper_em", 0))
        lower = float(derived.get("lower_em", 0))
        if upper > 0 and lower > 0:
            spot = (upper + lower) / 2

    # Safety gate — incomplete context = no trade
    if spot <= 0 or em <= 0:
        return _no_trade()

    # Route by VGA environment
    if vga == "premium_selling":
        return _premium_selling()

    if vga == "neutral_time_spreads":
        # Check if price is truly near center — if not, fall back to premium_selling
        center_dist = 0.0
        upper = float(derived.get("upper_em", 0))
        lower = float(derived.get("lower_em", 0))
        if upper > 0 and lower > 0 and em > 0:
            center = (upper + lower) / 2
            center_dist = abs(spot - center) / em
        if center_dist > 0.60:
            return _premium_selling()
        return _neutral_time_spreads()

    if vga == "cautious_directional":
        return _cautious_directional()

    if vga == "trend_directional":
        return _trend_directional()

    # Mixed / unknown — safety check gamma
    if gamma_r == "negative":
        return _trend_directional()

    return _mixed()


# ─────────────────────────────────────────────
# ROUTING HELPERS
# ─────────────────────────────────────────────

def adjust_score_for_regime(
    base_score:    float,
    strategy_type: str,
    regime:        RegimeDecision,
) -> float:
    """
    Regime-aware score nudge. Boosts primary strategies, penalizes disallowed ones.
    Keeps the adjustment small — the core scorer already handles regime factors.
    """
    score = base_score

    if strategy_type in regime.primary_strategies:
        score += 4.0
    elif strategy_type in regime.secondary_strategies:
        score += 1.0
    elif not regime.strategy_allowed(strategy_type):
        score -= 30.0   # effectively filtered out at threshold

    # Apply size multiplier as a score drag in mixed/cautious envs
    if regime.size_multiplier < 1.0:
        score -= (1.0 - regime.size_multiplier) * 8.0

    return max(0.0, min(round(score, 2), 100.0))

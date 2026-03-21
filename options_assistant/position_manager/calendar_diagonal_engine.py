"""
position_manager/calendar_diagonal_engine.py
Manages the full lifecycle of calendar → diagonal structures.

Lifecycle:
  ENTER_CALENDAR → HOLD → ROLL_SHORT → CONVERT_TO_DIAGONAL
  → ROLL_DIAGONAL_SHORT → EXIT_LONG_WINDOW / EXIT_STRUCTURE_BREAK / EXIT_ENVIRONMENT

Entry rules (EGPE v1.0):
  - Gamma = POSITIVE
  - IV = ELEVATED
  - Strike within ±0.5 EM of spot (pin zone)
  - Short 7–10 DTE, Long 45–60 DTE

Management rules:
  - Convert to diagonal when price drifts 0.35–1.0 EM from center
  - Roll short when ≤ 5 DTE remains on short leg
  - Exit long when long leg enters 35–28 DTE window
  - Exit immediately on environment breakdown
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Literal, Optional


# ─────────────────────────────────────────────
# TYPES
# ─────────────────────────────────────────────

EngineAction = Literal[
    "ENTER_CALENDAR",
    "HOLD",
    "ROLL_SHORT",
    "CONVERT_TO_DIAGONAL",
    "ROLL_DIAGONAL_SHORT",
    "EXIT_LONG_WINDOW",
    "EXIT_STRUCTURE_BREAK",
    "EXIT_ENVIRONMENT",
    "NO_ACTION",
]

StructureType   = Literal["calendar", "diagonal"]
OptionSide      = Literal["call", "put"]
UrgencyLevel    = Literal["LOW", "MEDIUM", "HIGH"]


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class CalDiagConfig:
    # Entry DTE windows
    short_dte_min:   int   = 7
    short_dte_max:   int   = 10
    long_dte_min:    int   = 45
    long_dte_max:    int   = 60

    # Long-leg exit band (days remaining on long leg)
    long_exit_dte_high: int = 35
    long_exit_dte_low:  int = 28

    # Price drift thresholds (as fraction of expected move)
    convert_em_frac_low:  float = 0.35   # start of conversion window
    convert_em_frac_high: float = 1.00   # structure break level
    structure_break_frac: float = 1.00

    # Roll triggers
    short_roll_dte:    int = 5
    diagonal_roll_dte: int = 5

    # Risk/pricing
    max_debit_pct_of_underlying: float = 0.06
    target_profit_pct:           float = 0.20
    stop_loss_pct:               float = 0.25

    # Scoring biases
    env_premium_selling_bonus:      float = 10.0
    env_neutral_time_spreads_bonus: float = 18.0
    pin_zone_bonus:                 float = 14.0
    dte_match_bonus:                float = 8.0


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class CalDiagCandidate:
    symbol:              str
    structure_type:      StructureType
    option_side:         OptionSide
    long_strike:         float
    short_strike:        float
    long_dte:            int
    short_dte:           int
    entry_debit:         float
    score:               float
    rationale:           str
    target_profit_value: float
    stop_loss_value:     float


@dataclass
class OpenCalDiagPosition:
    """Represents a live calendar or diagonal position being managed."""
    symbol:            str
    structure_type:    StructureType
    option_side:       OptionSide
    long_strike:       float
    short_strike:      float
    long_dte:          int
    short_dte:         int
    entry_debit:       float
    current_value:     float
    spot:              float
    expected_move:     float
    vga_environment:   str
    gamma_regime:      str     = "unknown"
    iv_regime:         str     = "unknown"
    regime_confidence: float   = 0.0
    notes:             str     = ""


@dataclass
class CalDiagDecision:
    symbol:            str
    action:            EngineAction
    structure_type:    StructureType
    option_side:       str
    urgency:           UrgencyLevel
    rationale:         str
    spot:              float
    expected_move:     float
    long_strike:       float
    short_strike:      float
    long_dte:          int
    short_dte:         int
    target_profit_value:    Optional[float] = None
    stop_loss_value:        Optional[float] = None
    target_short_strike:    Optional[float] = None
    target_long_strike:     Optional[float] = None
    target_short_dte:       Optional[int]   = None
    target_long_dte:        Optional[int]   = None
    notes:                  str             = ""


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _em_frac(spot: float, strike: float, em: float) -> float:
    if em <= 0:
        return 0.0
    return abs(spot - strike) / em


def _in_pin_zone(spot: float, strike: float, em: float) -> bool:
    return _em_frac(spot, strike, em) <= 0.50


def _round_strike(strike: float, step: float = 1.0) -> float:
    return round(round(strike / step) * step, 2) if step > 0 else round(strike, 2)


def _env_allows(vga: str) -> bool:
    return vga in ("premium_selling", "neutral_time_spreads", "mixed")


def _env_is_bad(vga: str) -> bool:
    return vga in ("trend_directional", "cautious_directional")


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def score_calendar_entry(
    *,
    spot:           float,
    strike:         float,
    expected_move:  float,
    vga:            str,
    long_dte:       int,
    short_dte:      int,
    debit:          float,
    iv_regime:      str = "",
    term_structure: str = "",
    cfg:            CalDiagConfig | None = None,
) -> float:
    cfg   = cfg or CalDiagConfig()
    score = 50.0

    # Environment bonus
    if vga == "neutral_time_spreads":
        score += cfg.env_neutral_time_spreads_bonus
    elif vga == "premium_selling":
        score += cfg.env_premium_selling_bonus
    elif _env_is_bad(vga):
        score -= 25.0

    # Pin zone bonus
    frac = _em_frac(spot, strike, expected_move)
    if frac <= 0.15:
        score += cfg.pin_zone_bonus
    elif frac <= 0.35:
        score += cfg.pin_zone_bonus * 0.5
    elif frac > 0.60:
        score -= 12.0

    # DTE match
    if cfg.short_dte_min <= short_dte <= cfg.short_dte_max:
        score += 6.0
    else:
        score -= 6.0
    if cfg.long_dte_min <= long_dte <= cfg.long_dte_max:
        score += cfg.dte_match_bonus
    else:
        score -= cfg.dte_match_bonus

    # Debit reasonableness
    if spot > 0:
        debit_pct = debit / spot
        score += 8.0 if debit_pct <= cfg.max_debit_pct_of_underlying else -16.0

    # Term structure / IV bonus
    if str(iv_regime).lower() in ("elevated", "rich"):
        score += 4.0
    if str(term_structure).lower() in ("flat", "contango"):
        score += 3.0

    return max(0.0, min(round(score, 2), 100.0))


# ─────────────────────────────────────────────
# ENTRY BUILDER
# ─────────────────────────────────────────────

def build_calendar_candidate(
    *,
    symbol:         str,
    spot:           float,
    strike:         float,
    short_dte:      int,
    long_dte:       int,
    debit:          float,
    bias:           str,
    expected_move:  float,
    vga:            str,
    iv_regime:      str  = "",
    term_structure: str  = "",
    cfg:            CalDiagConfig | None = None,
) -> CalDiagCandidate:
    cfg        = cfg or CalDiagConfig()
    option_side: OptionSide = "put" if str(bias).upper() in ("BEARISH", "DOWN") else "call"

    score = score_calendar_entry(
        spot=spot, strike=strike, expected_move=expected_move,
        vga=vga, long_dte=long_dte, short_dte=short_dte, debit=debit,
        iv_regime=iv_regime, term_structure=term_structure, cfg=cfg,
    )

    return CalDiagCandidate(
        symbol=symbol,
        structure_type="calendar",
        option_side=option_side,
        long_strike=strike,
        short_strike=strike,
        long_dte=long_dte,
        short_dte=short_dte,
        entry_debit=round(debit, 4),
        score=score,
        rationale=(
            f"ATM {option_side} calendar at ${strike:.0f} | "
            f"short {short_dte}DTE long {long_dte}DTE | {vga}"
        ),
        target_profit_value=round(debit * (1.0 + cfg.target_profit_pct), 4),
        stop_loss_value=round(debit * (1.0 - cfg.stop_loss_pct), 4),
    )


# ─────────────────────────────────────────────
# POSITION EVALUATOR
# ─────────────────────────────────────────────

def evaluate_position(
    pos: OpenCalDiagPosition,
    cfg: CalDiagConfig | None = None,
) -> CalDiagDecision:
    """
    Core lifecycle decision engine.
    Evaluates a live position and returns the recommended action.
    """
    cfg    = cfg or CalDiagConfig()
    tp     = round(pos.entry_debit * (1.0 + cfg.target_profit_pct), 4)
    sl     = round(pos.entry_debit * (1.0 - cfg.stop_loss_pct), 4)
    frac   = _em_frac(pos.spot, pos.long_strike, pos.expected_move)

    def _decision(action: EngineAction, urgency: UrgencyLevel, rationale: str,
                  **kwargs) -> CalDiagDecision:
        return CalDiagDecision(
            symbol=pos.symbol, action=action,
            structure_type=pos.structure_type, option_side=pos.option_side,
            urgency=urgency, rationale=rationale,
            spot=pos.spot, expected_move=pos.expected_move,
            long_strike=pos.long_strike, short_strike=pos.short_strike,
            long_dte=pos.long_dte, short_dte=pos.short_dte,
            target_profit_value=tp, stop_loss_value=sl,
            **kwargs,
        )

    # 1. Bad environment — exit first
    if _env_is_bad(pos.vga_environment):
        return _decision("EXIT_ENVIRONMENT", "HIGH",
            "VGA environment no longer supports time spreads. "
            "Close or materially reduce exposure.")

    # 2. Long leg in exit window — always exit
    if pos.long_dte <= cfg.long_exit_dte_high:
        return _decision("EXIT_LONG_WINDOW", "HIGH",
            f"Long leg at {pos.long_dte} DTE is in the 35–28 DTE exit window. "
            "Exit or rebuild fresh.",
            target_short_dte=cfg.short_dte_max,
            target_long_dte=cfg.long_dte_max)

    # 3. Structure break — price too far from center
    if frac >= cfg.structure_break_frac:
        return _decision("EXIT_STRUCTURE_BREAK", "HIGH",
            f"Price has moved {frac:.1%} of EM from center strike. "
            "Calendar center is broken — do not hold.")

    # 4. Calendar: convert to diagonal when drift is meaningful
    if (pos.structure_type == "calendar"
            and cfg.convert_em_frac_low <= frac < cfg.convert_em_frac_high):
        offset = pos.expected_move * 0.35
        if pos.option_side == "call":
            tgt = _round_strike(
                pos.long_strike + offset if pos.spot > pos.long_strike else pos.long_strike
            )
        else:
            tgt = _round_strike(
                pos.long_strike - offset if pos.spot < pos.long_strike else pos.long_strike
            )
        return _decision("CONVERT_TO_DIAGONAL", "MEDIUM",
            f"Price drifted {frac:.1%} of EM from center. "
            "Move short strike directionally while keeping long anchor.",
            target_short_strike=tgt,
            target_long_strike=pos.long_strike,
            target_short_dte=cfg.short_dte_max,
            target_long_dte=pos.long_dte)

    # 5. Calendar: roll short leg near expiry
    if (pos.structure_type == "calendar"
            and pos.short_dte <= cfg.short_roll_dte):
        return _decision("ROLL_SHORT", "MEDIUM",
            f"Short leg at {pos.short_dte} DTE — re-sell at same strike.",
            target_short_strike=pos.short_strike,
            target_long_strike=pos.long_strike,
            target_short_dte=cfg.short_dte_max,
            target_long_dte=pos.long_dte)

    # 6. Diagonal: roll short leg near expiry
    if (pos.structure_type == "diagonal"
            and pos.short_dte <= cfg.diagonal_roll_dte):
        offset = pos.expected_move * 0.25
        if pos.option_side == "call":
            tgt = _round_strike(pos.spot + offset * 0.5
                                if pos.spot >= pos.short_strike else pos.short_strike)
        else:
            tgt = _round_strike(pos.spot - offset * 0.5
                                if pos.spot <= pos.short_strike else pos.short_strike)
        return _decision("ROLL_DIAGONAL_SHORT", "MEDIUM",
            f"Diagonal short at {pos.short_dte} DTE. Reposition short near spot.",
            target_short_strike=tgt,
            target_long_strike=pos.long_strike,
            target_short_dte=cfg.short_dte_max,
            target_long_dte=pos.long_dte)

    # 7. Profit target reached
    if pos.current_value >= tp:
        return _decision("HOLD", "LOW",
            "Structure has reached profit target zone. "
            "Operator may harvest or continue holding.",
            notes="Consider partial exit here.")

    # 8. Hold — everything looks fine
    return _decision("HOLD", "LOW",
        "Structure is in valid management window. "
        "Continue monitoring theta, drift, and long-leg decay.")


def candidate_to_dict(c: CalDiagCandidate) -> dict[str, Any]:
    return asdict(c)


def decision_to_dict(d: CalDiagDecision) -> dict[str, Any]:
    return asdict(d)

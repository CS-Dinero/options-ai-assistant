"""engine/assignment_guard.py — Assignment risk detection, flip detector, contract scale gate.

Three additions to the roll advisor that prevent the assignment scenario:
1. ASSIGNMENT RISK FLAG  — alerts when short DTE ≤ 2 and delta > 0.85
2. FLIP DETECTOR         — identifies when opposite-side flip beats rolling
3. CONTRACT SCALE GATE   — enforces Golden Harvest rule before allowing scale
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

# ── Thresholds ────────────────────────────────────────────────────────────────
ASSIGNMENT_DTE_TRIGGER  = 2      # DTE at which assignment risk becomes real
ASSIGNMENT_DELTA_TRIGGER= 0.85   # absolute delta above which assignment likely
FLIP_ATR_MULTIPLIER     = 2.0    # move > 2x ATR signals flip opportunity
MIN_FLIP_PREMIUM        = 0.50   # minimum opposite-side premium to consider flip
MIN_SCALE_CREDIT_RATIO  = 1.50   # roll credit must be 1.5x extra collateral cost


@dataclass
class AssignmentRisk:
    """Result of assignment risk check."""
    symbol: str
    short_strike: float
    short_expiry: str
    short_dte: int
    short_delta: float
    spot_price: float

    at_risk: bool
    urgency: str          # "CRITICAL" | "WARNING" | "MONITOR" | "SAFE"
    action_required: str
    hours_to_act: float
    intrinsic_value: float
    time_value_remaining: float

    recommendation: str


@dataclass
class FlipOpportunity:
    """Result of flip detector."""
    symbol: str
    current_side: str      # "PUT" | "CALL"
    flip_to_side: str
    spot_price: float
    atr: float
    move_vs_atr: float     # how many ATR the move was

    flip_viable: bool
    opposite_premium: float
    flip_strike: float
    flip_expiry: str
    flip_credit_est: float

    reason: str


@dataclass
class ScaleDecision:
    """Result of contract scale gate."""
    current_contracts: int
    proposed_contracts: int
    contracts_to_add: int

    roll_credit_per_contract: float
    extra_collateral_per_contract: float
    roll_credit_total: float
    extra_collateral_total: float

    golden_harvest_active: bool
    excess_harvest: float
    account_in_deficit: bool

    approved: bool
    safe_contracts: int    # approved scale level
    reason: str


# ── 1. ASSIGNMENT RISK FLAG ───────────────────────────────────────────────────
def check_assignment_risk(
    symbol: str,
    short_strike: float,
    short_expiry: str,
    short_dte: int,
    short_delta: float,    # absolute value
    short_mid: float,
    spot_price: float,
    option_type: str = "PUT",
) -> AssignmentRisk:
    """
    Flags assignment risk based on DTE and delta.
    Returns urgency level and time-to-act estimate.
    """
    ot = option_type.upper()
    if ot == "PUT":
        intrinsic = max(0.0, short_strike - spot_price)
    else:
        intrinsic = max(0.0, spot_price - short_strike)

    time_value = max(0.0, short_mid - intrinsic)
    abs_delta  = abs(short_delta)

    # Urgency classification
    if short_dte == 0:
        urgency = "CRITICAL"
        action  = "ASSIGNMENT GUARANTEED — close NOW or assignment happens at 4pm"
        hours   = 0.0
    elif short_dte == 1 and abs_delta >= ASSIGNMENT_DELTA_TRIGGER:
        urgency = "CRITICAL"
        action  = "Roll TODAY before market close — 1 DTE deep ITM = assignment risk"
        hours   = 6.5
    elif short_dte <= ASSIGNMENT_DTE_TRIGGER and abs_delta >= ASSIGNMENT_DELTA_TRIGGER:
        urgency = "WARNING"
        action  = "Roll within 24 hours — DTE and delta both at threshold"
        hours   = 24.0
    elif short_dte <= 5 and abs_delta >= 0.75:
        urgency = "MONITOR"
        action  = "Plan roll for tomorrow morning — approaching risk zone"
        hours   = 48.0
    else:
        urgency = "SAFE"
        action  = "No action needed — within safe parameters"
        hours   = short_dte * 24.0

    at_risk = urgency in ("CRITICAL", "WARNING")

    rec_parts = [f"{urgency}: {action}"]
    if at_risk:
        rec_parts.append(
            f"Short {short_strike}{ot[0]} has ${intrinsic:.2f} intrinsic, "
            f"${time_value:.2f} time value. "
            f"Roll same-strike to next expiry for net credit of ~${time_value*1.5:.2f}/contract."
        )
    if short_dte <= 1:
        rec_parts.append(
            "ALERT: Set calendar reminder for EVERY short expiry date minus 2 days."
        )

    return AssignmentRisk(
        symbol=symbol, short_strike=short_strike, short_expiry=short_expiry,
        short_dte=short_dte, short_delta=abs_delta, spot_price=spot_price,
        at_risk=at_risk, urgency=urgency, action_required=action,
        hours_to_act=hours, intrinsic_value=round(intrinsic, 4),
        time_value_remaining=round(time_value, 4),
        recommendation=" | ".join(rec_parts),
    )


# ── 2. FLIP DETECTOR ─────────────────────────────────────────────────────────
def detect_flip_opportunity(
    symbol: str,
    current_side: str,          # "PUT" | "CALL"
    spot_price: float,
    atr: float,                 # 14-day ATR
    move_today: float,          # price change today (signed)
    opposite_strike: float,     # proposed flip strike
    opposite_expiry: str,
    opposite_mid: float,        # premium available on flip side
    current_roll_credit: float, # what rolling same-side would collect
) -> FlipOpportunity:
    """
    Detects when a flip to the opposite side beats rolling.
    Triggered when underlying moves > 2x ATR against the short.
    """
    flip_to = "CALL" if current_side.upper() == "PUT" else "PUT"
    move_vs_atr = abs(move_today) / max(0.01, atr)
    flip_viable = (
        move_vs_atr >= FLIP_ATR_MULTIPLIER
        and opposite_mid >= MIN_FLIP_PREMIUM
        and opposite_mid > current_roll_credit * 0.80  # flip pays at least 80% of roll
    )

    if flip_viable:
        reason = (
            f"Underlying moved {move_vs_atr:.1f}x ATR — momentum favors {flip_to} side. "
            f"Flip credit ${opposite_mid:.2f} vs roll credit ${current_roll_credit:.2f}. "
            f"Close {current_side} position, open {flip_to} diagonal at {opposite_strike}."
        )
    elif move_vs_atr >= FLIP_ATR_MULTIPLIER:
        reason = (
            f"Move is {move_vs_atr:.1f}x ATR but opposite premium "
            f"(${opposite_mid:.2f}) is too thin to justify flip. Continue rolling."
        )
    else:
        reason = (
            f"Move is only {move_vs_atr:.1f}x ATR — not enough momentum for flip. "
            f"Roll same-side."
        )

    return FlipOpportunity(
        symbol=symbol, current_side=current_side.upper(), flip_to_side=flip_to,
        spot_price=spot_price, atr=atr, move_vs_atr=round(move_vs_atr, 2),
        flip_viable=flip_viable, opposite_premium=opposite_mid,
        flip_strike=opposite_strike, flip_expiry=opposite_expiry,
        flip_credit_est=opposite_mid,
        reason=reason,
    )


# ── 3. CONTRACT SCALE GATE ────────────────────────────────────────────────────
def check_contract_scale(
    current_contracts: int,
    proposed_contracts: int,
    roll_credit_per_contract: float,    # net credit from rolling
    spread_width: float,                # strike width of the spread
    entry_debit: float,                 # original campaign entry cost
    total_credits_collected: float,     # total credits so far
    total_costs_paid: float,            # total roll/close costs so far
    account_cash: float,                # available cash/BP
    safety_factor: float = 0.60,
) -> ScaleDecision:
    """
    Enforces Golden Harvest rule before allowing contract increase.
    Only approves scale when campaign excess funds the new contracts.
    """
    contracts_to_add = proposed_contracts - current_contracts
    if contracts_to_add <= 0:
        return ScaleDecision(
            current_contracts=current_contracts,
            proposed_contracts=proposed_contracts,
            contracts_to_add=0,
            roll_credit_per_contract=roll_credit_per_contract,
            extra_collateral_per_contract=0,
            roll_credit_total=0,
            extra_collateral_total=0,
            golden_harvest_active=False,
            excess_harvest=0,
            account_in_deficit=False,
            approved=True,
            safe_contracts=current_contracts,
            reason="No scale requested — maintaining current size",
        )

    # Campaign state
    net_basis = round(entry_debit - total_credits_collected + total_costs_paid, 4)
    excess     = round(max(0.0, -net_basis), 4)
    golden     = net_basis < 0
    in_deficit = account_cash < 0

    # Cost of adding contracts
    collateral_per = spread_width * 100          # per new contract
    extra_collateral= collateral_per * contracts_to_add
    roll_credit_total = roll_credit_per_contract * current_contracts * 100

    # Scale approval logic
    credit_covers_collateral = roll_credit_total >= extra_collateral * MIN_SCALE_CREDIT_RATIO
    excess_covers_scale      = excess * current_contracts * 100 >= extra_collateral

    approved = (
        golden
        and not in_deficit
        and (credit_covers_collateral or excess_covers_scale)
    )

    # Safe contract count (60% of math-allowed)
    import math
    if golden:
        math_allowed  = math.floor(current_contracts + excess / max(0.001, entry_debit))
        safe_contracts= max(current_contracts, math.floor(math_allowed * safety_factor))
    else:
        safe_contracts = current_contracts

    if approved:
        reason = (
            f"APPROVED — Golden Harvest active (excess ${excess:.2f}/contract). "
            f"Roll credit ${roll_credit_total:.0f} covers collateral ${extra_collateral:.0f}. "
            f"Safe scale: {safe_contracts} contracts (60% rule)."
        )
    elif not golden:
        reason = (
            f"BLOCKED — Campaign basis ${net_basis:.2f} not yet negative. "
            f"Recover ${abs(net_basis):.2f} more before scaling. "
            f"Keep current {current_contracts} contracts."
        )
    elif in_deficit:
        reason = (
            f"BLOCKED — Account in cash deficit. "
            f"Clear margin before adding contracts."
        )
    else:
        reason = (
            f"BLOCKED — Roll credit ${roll_credit_total:.0f} insufficient to fund "
            f"${extra_collateral:.0f} extra collateral. "
            f"Need {MIN_SCALE_CREDIT_RATIO}x coverage."
        )

    return ScaleDecision(
        current_contracts=current_contracts,
        proposed_contracts=proposed_contracts,
        contracts_to_add=contracts_to_add,
        roll_credit_per_contract=roll_credit_per_contract,
        extra_collateral_per_contract=collateral_per,
        roll_credit_total=round(roll_credit_total, 2),
        extra_collateral_total=round(extra_collateral, 2),
        golden_harvest_active=golden,
        excess_harvest=excess,
        account_in_deficit=in_deficit,
        approved=approved,
        safe_contracts=safe_contracts,
        reason=reason,
    )


# ── Combined rescue check ─────────────────────────────────────────────────────
def full_rescue_check(
    symbol: str,
    option_type: str,
    short_strike: float,
    short_expiry: str,
    short_dte: int,
    short_delta: float,
    short_mid: float,
    spot_price: float,
    atr: float,
    move_today: float,
    opposite_strike: float,
    opposite_expiry: str,
    opposite_mid: float,
    roll_credit_per_contract: float,
    current_contracts: int,
    proposed_contracts: int,
    spread_width: float,
    entry_debit: float,
    total_credits: float,
    total_costs: float,
    account_cash: float,
) -> dict[str, Any]:
    """Single call that runs all three checks and returns a unified rescue plan."""
    assignment = check_assignment_risk(
        symbol, short_strike, short_expiry, short_dte,
        short_delta, short_mid, spot_price, option_type)

    flip = detect_flip_opportunity(
        symbol, option_type, spot_price, atr, move_today,
        opposite_strike, opposite_expiry, opposite_mid, roll_credit_per_contract)

    scale = check_contract_scale(
        current_contracts, proposed_contracts, roll_credit_per_contract,
        spread_width, entry_debit, total_credits, total_costs, account_cash)

    # Unified action priority
    if assignment.urgency == "CRITICAL":
        primary_action = "ROLL_NOW"
    elif flip.flip_viable and not assignment.at_risk:
        primary_action = "FLIP"
    elif scale.approved and not assignment.at_risk:
        primary_action = "SCALE_AND_ROLL"
    elif assignment.at_risk:
        primary_action = "ROLL_SAME_STRIKE"
    else:
        primary_action = "HOLD"

    return {
        "symbol": symbol,
        "primary_action": primary_action,
        "assignment_risk": {
            "urgency": assignment.urgency,
            "at_risk": assignment.at_risk,
            "hours_to_act": assignment.hours_to_act,
            "intrinsic": assignment.intrinsic_value,
            "time_value": assignment.time_value_remaining,
            "recommendation": assignment.recommendation,
        },
        "flip_opportunity": {
            "viable": flip.flip_viable,
            "flip_to": flip.flip_to_side,
            "move_vs_atr": flip.move_vs_atr,
            "flip_credit": flip.flip_credit_est,
            "reason": flip.reason,
        },
        "scale_gate": {
            "approved": scale.approved,
            "safe_contracts": scale.safe_contracts,
            "golden_harvest": scale.golden_harvest_active,
            "reason": scale.reason,
        },
    }

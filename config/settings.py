"""
config/settings.py
All strategy and risk constants in one place.
Change these to tune system behavior without touching logic files.
"""

DEFAULT_SYMBOL       = "SPY"
DEFAULT_SPREAD_WIDTH = 5
DEFAULT_SHORT_DTE    = 7
DEFAULT_LONG_DTE     = 60

# Credit spread rules
CREDIT_DELTA_MIN         = 0.15  # EGPE v1.0: tightened from 0.10
CREDIT_DELTA_MAX         = 0.20
CREDIT_TARGET_PERCENT    = 0.50
CREDIT_STOP_MULTIPLIER   = 2.0

# Time-based exit (EGPE v1.0 rule: close at 3-5 DTE remaining)
TIME_EXIT_DTE            = 5

# Debit spread rules
DEBIT_TARGET_CAPTURE     = 0.50
DEBIT_STOP_PERCENT       = 0.50

# Calendar rules
CALENDAR_TARGET_MULTIPLIER  = 1.25
CALENDAR_STOP_PERCENT       = 0.35
CALENDAR_THETA_RATIO_MIN    = 1.5
CALENDAR_IV_REGIMES_OK      = ("cheap", "moderate")
CALENDAR_TERM_STRUCTURES_OK = ("contango",)

# Diagonal rules
DIAGONAL_TARGET_MULTIPLIER       = 1.35
DIAGONAL_STOP_PERCENT            = 0.35
DIAGONAL_LONG_DELTA_MIN          = 0.70
DIAGONAL_LONG_DELTA_MAX          = 0.85
DIAGONAL_SHORT_DELTA_MIN         = 0.20
DIAGONAL_SHORT_DELTA_MAX         = 0.35
DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH  = 1.00  # LEAPS: only reject if debit >= full width (wrong pricing)
MIN_LONG_LEG_OPEN_INTEREST       = 500
MAX_BID_ASK_SPREAD_PCT           = 0.08

# IV Rank thresholds
IV_RANK_CALENDAR_MAX  = 0.40
IV_RANK_DIAGONAL_MAX  = 0.55
IV_RANK_CREDIT_MIN    = 0.30

# Scoring weights - must sum to 100
SCORE_WEIGHTS = {
    "iv_regime":    20,
    "gamma_regime": 20,
    "em_placement": 20,
    "skew":         15,
    "term_struct":  15,
    "atr_regime":   10,
}

SCORE_STRONG    = 80
SCORE_TRADABLE  = 65

REQUIRED_CANDIDATE_FIELDS = [
    "strategy_type", "direction", "symbol",
    "short_expiration", "long_expiration",
    "long_strike", "short_strike", "hedge_strike", "width",
    "entry_debit_credit", "max_profit", "max_loss",
    "target_exit_value", "stop_value",
    "prob_itm_proxy", "prob_touch_proxy",
    "contracts", "confidence_score", "notes",
]

# LEAPS diagonal extrinsic filter
# Rejects long legs where > MAX_LONG_EXTRINSIC_RATIO of premium is time value.
# Professional range: 0.30-0.40 (60-70% must be intrinsic value)
MAX_LONG_EXTRINSIC_RATIO = 0.40

# Gamma trap proximity for calendar targeting
# Calendar uses gamma trap strike only when trap is within this % of EM from spot
GAMMA_TRAP_PROXIMITY_PCT = 0.50

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
CREDIT_DELTA_MIN         = 0.10
CREDIT_DELTA_MAX         = 0.20
CREDIT_TARGET_PERCENT    = 0.50    # take profit at 50% of credit
CREDIT_STOP_MULTIPLIER   = 2.0     # stop at 2x credit received

# Debit spread rules
DEBIT_TARGET_CAPTURE     = 0.50    # capture 50% of max profit
DEBIT_STOP_PERCENT       = 0.50    # stop at 50% of debit paid

# Calendar rules
CALENDAR_TARGET_MULTIPLIER = 1.25
CALENDAR_STOP_PERCENT      = 0.35

# Diagonal rules
DIAGONAL_TARGET_MULTIPLIER = 1.35
DIAGONAL_STOP_PERCENT      = 0.35

# Scoring weights — must sum to 100
SCORE_WEIGHTS = {
    "iv_regime":    20,
    "gamma_regime": 20,
    "em_placement": 20,
    "skew":         15,
    "term_struct":  15,
    "atr_regime":   10,
}

# Score thresholds
SCORE_STRONG    = 80
SCORE_TRADABLE  = 65

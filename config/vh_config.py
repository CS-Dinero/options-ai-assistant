"""
config/vh_config.py
Volatility Harvest configuration constants.

Centralized thresholds for harvest triggers, flip logic, and walk-limit execution.
All values can be tuned here without touching core engine modules.
"""
from __future__ import annotations

# ── Harvest credit thresholds ─────────────────────────────────────────────────
GOLD_HARVEST_MIN_CREDIT: float = 5.00    # roll credit >= this → Gold badge
MIN_ROLL_NET_CREDIT:     float = 1.00    # roll credit >= this → Green badge; below → WAIT
HARVEST_WAIT_LABEL:      str   = "WAIT"  # returned when no roll is creditworthy

# ── Delta / assignment risk ───────────────────────────────────────────────────
DELTA_REDLINE:           float = 0.70    # short delta >= this → redline alert
INTRINSIC_TRAP_DELTA:    float = 0.75    # deep ITM threshold → assignment risk

# ── Vega / theta ──────────────────────────────────────────────────────────────
VEGA_SPIKE_MULTIPLIER:   float = 1.25    # current vega >= entry_vega * this → spike
THETA_STALL_RATIO:       float = 1.10    # |current_theta / entry_theta| <= 1/this → stall

# ── Gamma trap proximity ──────────────────────────────────────────────────────
GAMMA_TRAP_BUFFER:       float = 0.02    # within 2% of spot → red badge / trap alert

# ── Sentiment pivot thresholds ────────────────────────────────────────────────
SENTIMENT_BULLISH_THRESHOLD: float =  0.35   # score >= this → consider call pivot
SENTIMENT_BEARISH_THRESHOLD: float = -0.35   # score <= this → consider put pivot

# ── Walk-limit execution ──────────────────────────────────────────────────────
WALK_LIMIT_STEP:     float = 0.02    # credit step per walk interval ($/contract)
WALK_LIMIT_INTERVAL: int   = 30      # seconds between walk steps
WALK_LIMIT_TIMEOUT:  int   = 180     # max seconds before abandoning

# ── Symbol-specific selector config ──────────────────────────────────────────
# Used by live_strike_selector.py to set per-symbol delta and width rules.
# Wider symbols (TSLA) need more protection width.
# Index ETFs (SPY/QQQ/IWM) are tighter and more liquid.

SYMBOL_SELECTOR_CONFIG: dict = {
    "TSLA": {"short_delta_min": 0.20, "short_delta_max": 0.35, "min_width": 10, "preferred_width": 15},
    "AAPL": {"short_delta_min": 0.18, "short_delta_max": 0.30, "min_width": 5,  "preferred_width": 10},
    "MSFT": {"short_delta_min": 0.18, "short_delta_max": 0.30, "min_width": 5,  "preferred_width": 10},
    "SPY":  {"short_delta_min": 0.15, "short_delta_max": 0.25, "min_width": 5,  "preferred_width": 5},
    "QQQ":  {"short_delta_min": 0.15, "short_delta_max": 0.25, "min_width": 5,  "preferred_width": 5},
    "IWM":  {"short_delta_min": 0.15, "short_delta_max": 0.25, "min_width": 5,  "preferred_width": 5},
    "NVDA": {"short_delta_min": 0.20, "short_delta_max": 0.35, "min_width": 10, "preferred_width": 15},
    "AMD":  {"short_delta_min": 0.20, "short_delta_max": 0.35, "min_width": 5,  "preferred_width": 10},
}

# Default config for any symbol not in the table above
DEFAULT_SELECTOR_CONFIG: dict = {
    "short_delta_min": 0.15, "short_delta_max": 0.30,
    "min_width": 5, "preferred_width": 10,
}

# Per-share credit unit (not total dollars)
MIN_OPEN_CREDIT_PER_SHARE: float = 1.00

# ── Badge labels ──────────────────────────────────────────────────────────────
BADGE_GOLD:   str = "GOLD"       # roll credit >= GOLD_HARVEST_MIN_CREDIT
BADGE_GREEN:  str = "GREEN"      # roll credit >= MIN_ROLL_NET_CREDIT
BADGE_RED:    str = "RED"        # gamma trap within GAMMA_TRAP_BUFFER
BADGE_BLUE:   str = "BLUE"       # flip recommended
BADGE_WAIT:   str = "WAIT"       # no creditworthy roll available
BADGE_NONE:   str = "—"
BADGE_PURPLE: str = "PURPLE"  # flip candidate + harvestable (Gold or Green)

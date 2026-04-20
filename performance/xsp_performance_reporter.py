"""performance/xsp_performance_reporter.py — Format XSP performance for dashboard."""
from __future__ import annotations
from performance.xsp_performance_models import XSPPerformanceSummary

def xsp_performance_summary_to_dict(s: XSPPerformanceSummary) -> dict:
    return {
        "total_trades":              s.total_trades,
        "spread_trades":             s.spread_trades,
        "diagonal_trades":           s.diagonal_trades,
        "win_rate":                  round(s.win_rate, 4),
        "avg_realized_pnl":          round(s.avg_realized_pnl, 4),
        "avg_return_on_risk":        round(s.avg_return_on_risk, 4),
        "total_realized_pnl":        round(s.total_realized_pnl, 4),
        "spread_win_rate":           round(s.spread_win_rate, 4),
        "avg_spread_profit_capture": round(s.avg_spread_profit_capture, 4),
        "spread_force_close_rate":   round(s.spread_force_close_rate, 4),
        "diagonal_win_rate":         round(s.diagonal_win_rate, 4),
        "avg_diagonal_harvest":      round(s.avg_diagonal_harvest, 4),
        "avg_roll_count":            round(s.avg_roll_count, 4),
        "roll_success_rate":         round(s.roll_success_rate, 4),
        "avg_flip_realized_value":   round(s.avg_flip_realized_value, 4),
        "diagonal_force_close_rate": round(s.diagonal_force_close_rate, 4),
    }

def render_xsp_performance_text(s: XSPPerformanceSummary) -> str:
    return "\n".join([
        "XSP PERFORMANCE SUMMARY",
        f"trades={s.total_trades} | spreads={s.spread_trades} | diagonals={s.diagonal_trades}",
        f"win_rate={s.win_rate:.2%} | avg_pnl=${s.avg_realized_pnl:.2f} | avg_ror={s.avg_return_on_risk:.2%} | total_pnl=${s.total_realized_pnl:.2f}",
        f"SPREADS  — win={s.spread_win_rate:.2%} | capture={s.avg_spread_profit_capture:.2%} | force_close={s.spread_force_close_rate:.2%}",
        f"DIAGONALS — win={s.diagonal_win_rate:.2%} | harvest=${s.avg_diagonal_harvest:.2f} | rolls={s.avg_roll_count:.2f} | roll_success={s.roll_success_rate:.2%} | flip=${s.avg_flip_realized_value:.2f} | force_close={s.diagonal_force_close_rate:.2%}",
    ])

# Convenience: render as streamlit-ready dict for st.metrics
def render_xsp_performance_metrics(s: XSPPerformanceSummary) -> dict:
    return {
        "header": {
            "Total Trades": s.total_trades,
            "Win Rate": f"{s.win_rate:.1%}",
            "Avg P&L": f"${s.avg_realized_pnl:.2f}",
            "Avg RoR": f"{s.avg_return_on_risk:.1%}",
        },
        "spreads": {
            "Win Rate": f"{s.spread_win_rate:.1%}",
            "Avg Capture": f"{s.avg_spread_profit_capture:.1%}",
            "Force Close Rate": f"{s.spread_force_close_rate:.1%}",
        },
        "diagonals": {
            "Win Rate": f"{s.diagonal_win_rate:.1%}",
            "Avg Harvest": f"${s.avg_diagonal_harvest:.2f}",
            "Avg Roll Count": f"{s.avg_roll_count:.1f}",
            "Roll Success": f"{s.roll_success_rate:.1%}",
            "Avg Flip Value": f"${s.avg_flip_realized_value:.2f}",
            "Force Close Rate": f"{s.diagonal_force_close_rate:.1%}",
        },
    }

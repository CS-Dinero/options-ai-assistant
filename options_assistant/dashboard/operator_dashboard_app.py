"""
Standalone operator console entry point.
Run: streamlit run dashboard/operator_dashboard_app.py
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.operator_dashboard import render_operator_dashboard

render_operator_dashboard()

from tests.environment_validation_suite import run_environment_validation_suite
"""tests/test_registry.py — Master suite registration."""
from tests.engine_validation_suite import run_engine_validation_suite
from tests.workflow_validation_suite import run_workflow_validation_suite
from tests.policy_validation_suite import run_policy_validation_suite
from tests.portfolio_validation_suite import run_portfolio_validation_suite
from tests.execution_validation_suite import run_execution_validation_suite
from tests.research_validation_suite import run_research_validation_suite
from tests.control_plane_validation_suite import run_control_plane_validation_suite

TEST_REGISTRY = [
    ("environment", run_environment_validation_suite),
    ("engine",        run_engine_validation_suite),
    ("workflow",      run_workflow_validation_suite),
    ("policy",        run_policy_validation_suite),
    ("portfolio",     run_portfolio_validation_suite),
    ("execution",     run_execution_validation_suite),
    ("research",      run_research_validation_suite),
    ("control_plane", run_control_plane_validation_suite),
]

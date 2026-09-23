"""Check all top-level and page imports to ensure zero ModuleNotFoundError."""

import sys

try:
    import ai_helper
    import app
    import pages.detail
    import pages.observability
    import pages.overview
    import utils.database
    import utils.db_models
    import utils.demo_mode
    import utils.health_engine
    import utils.repositories
    import utils.risk_engine
    import utils.schemas
    import utils.seed
    import utils.services
    import utils.validation
    import evaluation.metrics
    import evaluation.runner
    print("ALL IMPORTS SUCCESSFUL! Zero missing modules.")
except Exception as e:
    print(f"IMPORT ERROR DETECTED: {e}")
    sys.exit(1)

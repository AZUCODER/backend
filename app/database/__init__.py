"""
Enhanced database package for connection and session management.

This package provides improved database connection management, monitoring,
and transaction handling for the FastAPI application.
"""

from .connection import DatabaseManager, db_manager, get_db


# Import get_session from the main database module for backward compatibility
def get_session():
    """Backward compatibility wrapper for get_db"""
    return get_db()


from .monitoring import DatabaseMonitor, db_monitor, track_query_performance
from .transactions import TransactionManager, transactional

__all__ = [
    "DatabaseManager",
    "db_manager",
    "get_db",
    "get_session",
    "DatabaseMonitor",
    "db_monitor",
    "track_query_performance",
    "TransactionManager",
    "transactional",
]

"""
Health check endpoints for database monitoring and system status.

This module provides comprehensive health check endpoints for monitoring
database performance, connection status, and system metrics.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.dependencies import (
    get_db_health,
    get_db_pool_status,
    get_query_performance_metrics,
    get_db_performance_summary,
    get_db_health_check,
    require_role,
    get_current_active_user,
)
from app.models.user import UserRole
from app.database.monitoring import (
    get_slow_queries,
    db_monitor,
    reset_monitoring,
)

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Dict: Basic health status
    """
    return {
        "status": "healthy",
        "service": "FastAPI Backend",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@router.get("/health/database", response_model=Dict[str, Any])
async def database_health_check(
    db_health: Dict[str, Any] = Depends(get_db_health),
    pool_status: Dict[str, Any] = Depends(get_db_pool_status),
):
    """
    Database health check endpoint.

    Args:
        db_health: Database health status
        pool_status: Connection pool status

    Returns:
        Dict: Database health information
    """
    return {
        "database": {
            "healthy": db_health,
            "pool_status": pool_status,
        },
        "status": "healthy" if db_health else "unhealthy",
    }


@router.get("/health/database/detailed", response_model=Dict[str, Any])
async def detailed_database_health_check(
    health_check: Dict[str, Any] = Depends(get_db_health_check),
    _: Any = Depends(require_role(UserRole.ADMIN)),
):
    """
    Detailed database health check endpoint (Admin only).

    Args:
        health_check: Comprehensive health check results

    Returns:
        Dict: Detailed database health information
    """
    return {
        "database": health_check,
        "status": "healthy" if health_check.get("healthy", False) else "unhealthy",
    }


@router.get("/metrics/database", response_model=Dict[str, Any])
async def database_metrics(
    performance_summary: Dict[str, Any] = Depends(get_db_performance_summary),
    _: Any = Depends(require_role(UserRole.ADMIN)),
):
    """
    Database performance metrics endpoint (Admin only).

    Args:
        performance_summary: Database performance summary

    Returns:
        Dict: Database performance metrics
    """
    return {
        "performance": performance_summary,
        "slow_queries": get_slow_queries(10),
        "n_plus_one_alerts": db_monitor.get_n_plus_one_alerts(),
    }


@router.get("/metrics/database/queries", response_model=Dict[str, Any])
async def query_metrics(
    query_metrics: Dict[str, Any] = Depends(get_query_performance_metrics),
    _: Any = Depends(require_role(UserRole.ADMIN)),
):
    """
    Query performance metrics endpoint (Admin only).

    Args:
        query_metrics: Query performance metrics

    Returns:
        Dict: Query performance metrics
    """
    return {
        "query_metrics": query_metrics,
        "slow_functions": db_monitor.get_top_slow_functions(10),
    }


@router.get("/metrics/database/slow-queries", response_model=Dict[str, Any])
async def slow_queries_metrics(_: Any = Depends(require_role(UserRole.ADMIN))):
    """
    Slow queries metrics endpoint (Admin only).

    Returns:
        Dict: Slow queries information
    """
    return {
        "slow_queries": get_slow_queries(50),
        "top_slow_functions": db_monitor.get_top_slow_functions(10),
    }


@router.post("/metrics/database/reset", response_model=Dict[str, str])
async def reset_database_metrics(_: Any = Depends(require_role(UserRole.ADMIN))):
    """
    Reset database performance metrics (Admin only).

    Returns:
        Dict: Reset confirmation
    """
    reset_monitoring()
    return {"message": "Database metrics reset successfully"}


@router.get("/health/readiness", response_model=Dict[str, Any])
async def readiness_check(
    db_health: Dict[str, Any] = Depends(get_db_health),
):
    """
    Readiness check endpoint for Kubernetes/container orchestration.

    Args:
        db_health: Database health status

    Returns:
        Dict: Readiness status
    """
    if not db_health:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not ready"
        )

    return {"ready": True, "checks": {"database": db_health}}


@router.get("/health/liveness", response_model=Dict[str, Any])
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes/container orchestration.

    Returns:
        Dict: Liveness status
    """
    return {"alive": True, "timestamp": "2024-01-01T00:00:00Z"}


@router.get("/status", response_model=Dict[str, Any])
async def system_status(
    pool_status: Dict[str, Any] = Depends(get_db_pool_status),
    performance_summary: Dict[str, Any] = Depends(get_db_performance_summary),
    _: Any = Depends(require_role(UserRole.ADMIN)),
):
    """
    Comprehensive system status endpoint (Admin only).

    Args:
        pool_status: Database connection pool status
        performance_summary: Database performance summary

    Returns:
        Dict: System status information
    """
    return {
        "system": {
            "status": "operational",
            "version": "1.0.0",
            "uptime": "N/A",  # Could be calculated from startup time
        },
        "database": {
            "pool": pool_status,
            "performance": performance_summary,
        },
        "health_checks": {
            "database": pool_status.get("health_status", False),
        },
    }

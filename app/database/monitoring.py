"""
Database performance monitoring system.

This module provides comprehensive performance monitoring for database
operations including query timing, slow query detection, and metrics collection.
"""

import time
import logging
from typing import Callable, Any, Dict, List, Optional
from functools import wraps
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class QueryMetric:
    """Represents metrics for a specific query operation"""

    function_name: str
    total_calls: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    slow_queries: int = 0
    failed_queries: int = 0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    last_called: Optional[datetime] = None

    def add_execution(self, execution_time: float, failed: bool = False):
        """Add a new execution time to the metrics"""
        self.total_calls += 1
        self.last_called = datetime.utcnow()

        if failed:
            self.failed_queries += 1
            return

        self.total_time += execution_time
        self.avg_time = (
            self.total_time / (self.total_calls - self.failed_queries)
            if (self.total_calls - self.failed_queries) > 0
            else 0
        )
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.recent_times.append(execution_time)


class DatabaseMonitor:
    """
    Comprehensive database performance monitoring.

    Tracks query performance, identifies slow queries, and provides
    detailed metrics for database operations.
    """

    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_metrics: Dict[str, QueryMetric] = {}
        self.slow_queries: List[Dict[str, Any]] = []
        self.n_plus_one_detector = NPlusOneDetector()
        self._lock = asyncio.Lock()

    def track_query_performance(self, func: Callable) -> Callable:
        """
        Decorator to track query performance metrics.

        Args:
            func: Function to monitor

        Returns:
            Wrapped function with performance monitoring
        """

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            function_name = f"{func.__module__}.{func.__name__}"

            # Check for potential N+1 queries
            self.n_plus_one_detector.track_query(function_name)

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Update metrics
                await self._update_metrics(function_name, execution_time, False)

                # Check for slow queries
                if execution_time > self.slow_query_threshold:
                    await self._log_slow_query(
                        function_name, execution_time, args, kwargs
                    )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Update metrics for failed query
                await self._update_metrics(function_name, execution_time, True)

                logger.error(
                    f"Query failed: {function_name} after {execution_time:.2f}s - {e}"
                )
                raise

        return wrapper

    async def _update_metrics(
        self, function_name: str, execution_time: float, failed: bool
    ):
        """Update performance metrics for a function"""
        async with self._lock:
            if function_name not in self.query_metrics:
                self.query_metrics[function_name] = QueryMetric(
                    function_name=function_name
                )

            metric = self.query_metrics[function_name]
            metric.add_execution(execution_time, failed)

            if execution_time > self.slow_query_threshold and not failed:
                metric.slow_queries += 1

    async def _log_slow_query(
        self, function_name: str, execution_time: float, args: tuple, kwargs: dict
    ):
        """Log slow query for analysis"""
        slow_query_info = {
            "function_name": function_name,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys()) if kwargs else [],
        }

        async with self._lock:
            self.slow_queries.append(slow_query_info)

            # Keep only last 1000 slow queries
            if len(self.slow_queries) > 1000:
                self.slow_queries = self.slow_queries[-1000:]

        logger.warning(
            f"Slow query detected: {function_name} took {execution_time:.2f}s"
        )

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all query performance metrics"""
        return {
            name: {
                "function_name": metric.function_name,
                "total_calls": metric.total_calls,
                "total_time": metric.total_time,
                "avg_time": metric.avg_time,
                "min_time": metric.min_time if metric.min_time != float("inf") else 0,
                "max_time": metric.max_time,
                "slow_queries": metric.slow_queries,
                "failed_queries": metric.failed_queries,
                "success_rate": (
                    (metric.total_calls - metric.failed_queries)
                    / metric.total_calls
                    * 100
                    if metric.total_calls > 0
                    else 0
                ),
                "last_called": (
                    metric.last_called.isoformat() if metric.last_called else None
                ),
                "recent_avg": (
                    sum(metric.recent_times) / len(metric.recent_times)
                    if metric.recent_times
                    else 0
                ),
            }
            for name, metric in self.query_metrics.items()
        }

    def get_slow_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent slow queries"""
        return self.slow_queries[-limit:]

    def get_top_slow_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get functions with most slow queries"""
        sorted_metrics = sorted(
            self.query_metrics.values(), key=lambda m: m.slow_queries, reverse=True
        )

        return [
            {
                "function_name": metric.function_name,
                "slow_queries": metric.slow_queries,
                "avg_time": metric.avg_time,
                "max_time": metric.max_time,
                "total_calls": metric.total_calls,
            }
            for metric in sorted_metrics[:limit]
            if metric.slow_queries > 0
        ]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        if not self.query_metrics:
            return {
                "total_queries": 0,
                "total_slow_queries": 0,
                "average_execution_time": 0,
                "total_failed_queries": 0,
            }

        total_queries = sum(m.total_calls for m in self.query_metrics.values())
        total_slow = sum(m.slow_queries for m in self.query_metrics.values())
        total_failed = sum(m.failed_queries for m in self.query_metrics.values())
        total_time = sum(m.total_time for m in self.query_metrics.values())

        return {
            "total_queries": total_queries,
            "total_slow_queries": total_slow,
            "slow_query_percentage": (
                (total_slow / total_queries * 100) if total_queries > 0 else 0
            ),
            "average_execution_time": (
                total_time / (total_queries - total_failed)
                if (total_queries - total_failed) > 0
                else 0
            ),
            "total_failed_queries": total_failed,
            "failure_rate": (
                (total_failed / total_queries * 100) if total_queries > 0 else 0
            ),
            "unique_functions": len(self.query_metrics),
        }

    def reset_metrics(self):
        """Reset all performance metrics"""
        self.query_metrics.clear()
        self.slow_queries.clear()
        self.n_plus_one_detector.reset()
        logger.info("Performance metrics reset")

    def get_n_plus_one_alerts(self) -> List[Dict[str, Any]]:
        """Get potential N+1 query alerts"""
        return self.n_plus_one_detector.get_alerts()


class NPlusOneDetector:
    """
    Detector for potential N+1 query problems.

    Monitors query patterns to identify potential N+1 query issues
    where many similar queries are executed in rapid succession.
    """

    def __init__(self, threshold: int = 10, time_window: int = 60):
        self.threshold = threshold  # Number of similar queries to trigger alert
        self.time_window = time_window  # Time window in seconds
        self.query_patterns: Dict[str, List[float]] = defaultdict(list)
        self.alerts: List[Dict[str, Any]] = []

    def track_query(self, function_name: str):
        """Track a query execution for N+1 detection"""
        current_time = time.time()

        # Clean old entries
        self._cleanup_old_entries(current_time)

        # Add current query
        self.query_patterns[function_name].append(current_time)

        # Check for N+1 pattern
        if len(self.query_patterns[function_name]) >= self.threshold:
            self._trigger_n_plus_one_alert(function_name, current_time)

    def _cleanup_old_entries(self, current_time: float):
        """Remove query entries older than time window"""
        cutoff_time = current_time - self.time_window

        for function_name in list(self.query_patterns.keys()):
            self.query_patterns[function_name] = [
                t for t in self.query_patterns[function_name] if t >= cutoff_time
            ]

            if not self.query_patterns[function_name]:
                del self.query_patterns[function_name]

    def _trigger_n_plus_one_alert(self, function_name: str, current_time: float):
        """Trigger N+1 query alert"""
        query_count = len(self.query_patterns[function_name])

        alert = {
            "function_name": function_name,
            "query_count": query_count,
            "time_window": self.time_window,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "high" if query_count > self.threshold * 2 else "medium",
        }

        self.alerts.append(alert)

        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

        logger.warning(
            f"Potential N+1 query detected: {function_name} executed "
            f"{query_count} times in {self.time_window} seconds"
        )

        # Reset the pattern to avoid spam
        self.query_patterns[function_name] = []

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all N+1 query alerts"""
        return self.alerts.copy()

    def reset(self):
        """Reset N+1 detection state"""
        self.query_patterns.clear()
        self.alerts.clear()


# Global monitor instance
db_monitor = DatabaseMonitor()

# Decorator for easy use
track_query_performance = db_monitor.track_query_performance


# Utility functions
def get_query_metrics() -> Dict[str, Any]:
    """Get current query performance metrics"""
    return db_monitor.get_metrics()


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    return db_monitor.get_performance_summary()


def get_slow_queries(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent slow queries"""
    return db_monitor.get_slow_queries(limit)


def reset_monitoring() -> None:
    """Reset all monitoring data"""
    db_monitor.reset_metrics()


async def health_check_queries() -> Dict[str, Any]:
    """Perform health check on query performance"""
    summary = get_performance_summary()
    slow_queries = get_slow_queries(10)
    n_plus_one_alerts = db_monitor.get_n_plus_one_alerts()

    # Determine health status
    is_healthy = (
        summary.get("slow_query_percentage", 0) < 10  # Less than 10% slow queries
        and summary.get("failure_rate", 0) < 1  # Less than 1% failures
        and len(n_plus_one_alerts) == 0  # No N+1 alerts
    )

    return {
        "healthy": is_healthy,
        "summary": summary,
        "recent_slow_queries": len(slow_queries),
        "n_plus_one_alerts": len(n_plus_one_alerts),
        "recommendations": _get_performance_recommendations(
            summary, slow_queries, n_plus_one_alerts
        ),
    }


def _get_performance_recommendations(
    summary: Dict[str, Any],
    slow_queries: List[Dict[str, Any]],
    n_plus_one_alerts: List[Dict[str, Any]],
) -> List[str]:
    """Generate performance recommendations based on metrics"""
    recommendations = []

    if summary.get("slow_query_percentage", 0) > 5:
        recommendations.append(
            "Consider optimizing slow queries or adding database indexes"
        )

    if summary.get("failure_rate", 0) > 0.5:
        recommendations.append(
            "High query failure rate detected - check database connectivity"
        )

    if len(slow_queries) > 5:
        recommendations.append(
            "Multiple slow queries detected - review query optimization"
        )

    if len(n_plus_one_alerts) > 0:
        recommendations.append(
            "N+1 query patterns detected - consider using eager loading"
        )

    if summary.get("average_execution_time", 0) > 0.5:
        recommendations.append(
            "High average query time - consider connection pooling optimization"
        )

    return recommendations

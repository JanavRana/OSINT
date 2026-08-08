"""
Metrics collection for plugin execution.

Tracks performance, success rates, and other metrics for monitoring
and confidence scoring.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PluginMetrics:
    """Metrics for a single plugin."""
    plugin_id: str
    
    # Execution metrics
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_timeouts: int = 0
    
    # Timing metrics (milliseconds)
    total_duration_ms: float = 0.0
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    
    # Recent window metrics
    recent_attempts: int = 0
    recent_successes: int = 0
    recent_failures: int = 0
    
    # Timestamps
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    
    def record_attempt(self, duration_ms: float, success: bool, timeout: bool = False) -> None:
        """Record an execution attempt."""
        now = time.monotonic()
        
        if self.first_seen is None:
            self.first_seen = now
        self.last_seen = now
        
        self.total_attempts += 1
        self.total_duration_ms += duration_ms
        
        if self.min_duration_ms is None or duration_ms < self.min_duration_ms:
            self.min_duration_ms = duration_ms
        if self.max_duration_ms is None or duration_ms > self.max_duration_ms:
            self.max_duration_ms = duration_ms
        
        if timeout:
            self.total_timeouts += 1
        
        if success:
            self.total_successes += 1
            self.last_success = now
        else:
            self.total_failures += 1
            self.last_failure = now
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_successes / self.total_attempts
    
    def get_average_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_duration_ms / self.total_attempts
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "total_timeouts": self.total_timeouts,
            "success_rate": self.get_success_rate(),
            "average_duration_ms": self.get_average_duration_ms(),
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
        }


class MetricsCollector:
    """
    Collects and aggregates metrics for all plugins.
    """
    
    def __init__(self):
        self._metrics: dict[str, PluginMetrics] = {}
        self._start_time = time.monotonic()
    
    def record_execution(
        self,
        plugin_id: str,
        duration_ms: float,
        success: bool,
        timeout: bool = False
    ) -> None:
        """
        Record a plugin execution.
        
        Args:
            plugin_id: Plugin identifier
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            timeout: Whether execution timed out
        """
        if plugin_id not in self._metrics:
            self._metrics[plugin_id] = PluginMetrics(plugin_id=plugin_id)
        
        self._metrics[plugin_id].record_attempt(duration_ms, success, timeout)
        
        logger.debug(
            f"Recorded execution for {plugin_id}: "
            f"duration={duration_ms:.1f}ms, success={success}, timeout={timeout}"
        )
    
    def get_plugin_metrics(self, plugin_id: str) -> Optional[PluginMetrics]:
        """Get metrics for a specific plugin."""
        return self._metrics.get(plugin_id)
    
    def get_all_metrics(self) -> dict[str, PluginMetrics]:
        """Get metrics for all plugins."""
        return dict(self._metrics)
    
    def get_summary(self) -> dict:
        """Get summary metrics across all plugins."""
        total_attempts = sum(m.total_attempts for m in self._metrics.values())
        total_successes = sum(m.total_successes for m in self._metrics.values())
        total_failures = sum(m.total_failures for m in self._metrics.values())
        total_timeouts = sum(m.total_timeouts for m in self._metrics.values())
        
        success_rate = (total_successes / total_attempts) if total_attempts > 0 else 0.0
        
        avg_durations = [
            m.get_average_duration_ms()
            for m in self._metrics.values()
            if m.total_attempts > 0
        ]
        overall_avg_duration = sum(avg_durations) / len(avg_durations) if avg_durations else 0.0
        
        uptime_seconds = time.monotonic() - self._start_time
        
        return {
            "total_plugins": len(self._metrics),
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "total_timeouts": total_timeouts,
            "overall_success_rate": success_rate,
            "overall_average_duration_ms": overall_avg_duration,
            "uptime_seconds": uptime_seconds,
        }
    
    def get_top_performers(self, limit: int = 10) -> list[tuple[str, float]]:
        """
        Get top performing plugins by success rate.
        
        Args:
            limit: Maximum number of plugins to return
            
        Returns:
            List of (plugin_id, success_rate) tuples
        """
        performers = [
            (plugin_id, metrics.get_success_rate())
            for plugin_id, metrics in self._metrics.items()
            if metrics.total_attempts >= 5  # Minimum sample size
        ]
        
        performers.sort(key=lambda x: x[1], reverse=True)
        return performers[:limit]
    
    def get_worst_performers(self, limit: int = 10) -> list[tuple[str, float]]:
        """
        Get worst performing plugins by success rate.
        
        Args:
            limit: Maximum number of plugins to return
            
        Returns:
            List of (plugin_id, success_rate) tuples
        """
        performers = [
            (plugin_id, metrics.get_success_rate())
            for plugin_id, metrics in self._metrics.items()
            if metrics.total_attempts >= 5  # Minimum sample size
        ]
        
        performers.sort(key=lambda x: x[1])
        return performers[:limit]
    
    def get_slowest_plugins(self, limit: int = 10) -> list[tuple[str, float]]:
        """
        Get slowest plugins by average duration.
        
        Args:
            limit: Maximum number of plugins to return
            
        Returns:
            List of (plugin_id, avg_duration_ms) tuples
        """
        plugins = [
            (plugin_id, metrics.get_average_duration_ms())
            for plugin_id, metrics in self._metrics.items()
            if metrics.total_attempts > 0
        ]
        
        plugins.sort(key=lambda x: x[1], reverse=True)
        return plugins[:limit]
    
    def reset_plugin(self, plugin_id: str) -> None:
        """Reset metrics for a plugin."""
        if plugin_id in self._metrics:
            del self._metrics[plugin_id]
            logger.info(f"Reset metrics for {plugin_id}")
    
    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()
        self._start_time = time.monotonic()
        logger.info("Cleared all metrics")


# Global singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector. Mainly for testing."""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.clear()
    _metrics_collector = None

"""
Health check scheduler and management for plugins.

Periodically runs health checks on registered plugins to detect
platform-side breakage before real investigations hit it.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..plugin_base import Plugin, HealthCheckResult
from ..types import HealthStatus
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class HealthCheckScheduler:
    """
    Schedules and executes periodic health checks for plugins.
    
    Health checks run independently of active scans to detect issues
    proactively. Failed checks demote plugins to 'degraded' status.
    """
    
    def __init__(
        self, 
        registry: PluginRegistry,
        default_interval_seconds: int = 900,  # 15 minutes
        failure_threshold: int = 3
    ):
        """
        Initialize the health check scheduler.
        
        Args:
            registry: Plugin registry to monitor
            default_interval_seconds: Default check interval (15 min)
            failure_threshold: Consecutive failures before marking degraded
        """
        self.registry = registry
        self.default_interval = default_interval_seconds
        self.failure_threshold = failure_threshold
        
        # Track health check state per plugin
        self._last_check_time: dict[str, datetime] = {}
        self._check_intervals: dict[str, int] = {}  # Custom intervals per plugin
        self._consecutive_failures: dict[str, int] = {}
        self._last_results: dict[str, HealthCheckResult] = {}
        
        # Control
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def set_interval(self, plugin_id: str, interval_seconds: int) -> None:
        """Set custom check interval for a specific plugin."""
        self._check_intervals[plugin_id] = interval_seconds
    
    def get_interval(self, plugin_id: str) -> int:
        """Get check interval for a plugin."""
        return self._check_intervals.get(plugin_id, self.default_interval)
    
    def should_check(self, plugin_id: str) -> bool:
        """Determine if a plugin should be checked now."""
        last_check = self._last_check_time.get(plugin_id)
        if last_check is None:
            return True
        
        interval = self.get_interval(plugin_id)
        elapsed = (datetime.utcnow() - last_check).total_seconds()
        return elapsed >= interval
    
    async def check_plugin(self, plugin: Plugin) -> HealthCheckResult:
        """
        Execute health check for a single plugin.
        
        Args:
            plugin: Plugin to check
            
        Returns:
            HealthCheckResult with status and details
        """
        plugin_id = plugin.id
        start_time = datetime.utcnow()
        
        try:
            result = await plugin.health_check()
            
            # Update tracking
            self._last_check_time[plugin_id] = start_time
            self._last_results[plugin_id] = result
            
            # Update failure counter and registry status
            if result.status == HealthStatus.HEALTHY:
                self._consecutive_failures[plugin_id] = 0
                self.registry.update_health_status(plugin_id, HealthStatus.HEALTHY)
                logger.debug(f"Health check passed: {plugin_id}")
            
            elif result.status == HealthStatus.DEGRADED:
                failures = self._consecutive_failures.get(plugin_id, 0) + 1
                self._consecutive_failures[plugin_id] = failures
                
                if failures >= self.failure_threshold:
                    self.registry.update_health_status(plugin_id, HealthStatus.DEGRADED)
                    logger.warning(
                        f"Plugin {plugin_id} marked DEGRADED after {failures} consecutive issues"
                    )
                else:
                    logger.info(f"Health check degraded: {plugin_id} ({failures}/{self.failure_threshold})")
            
            else:  # UNKNOWN
                self.registry.update_health_status(plugin_id, HealthStatus.UNKNOWN)
            
            return result
        
        except Exception as e:
            # Health check itself failed
            logger.error(f"Health check exception for {plugin_id}: {e}", exc_info=True)
            
            failures = self._consecutive_failures.get(plugin_id, 0) + 1
            self._consecutive_failures[plugin_id] = failures
            
            if failures >= self.failure_threshold:
                self.registry.update_health_status(plugin_id, HealthStatus.DEGRADED)
                logger.error(
                    f"Plugin {plugin_id} marked DEGRADED after {failures} consecutive failures"
                )
            
            result = HealthCheckResult(
                status=HealthStatus.DEGRADED,
                timestamp=datetime.utcnow(),
                message=f"Health check exception: {str(e)}"
            )
            self._last_results[plugin_id] = result
            return result
    
    async def check_all_plugins(self) -> dict[str, HealthCheckResult]:
        """
        Check all enabled plugins that are due for a check.
        
        Returns:
            Dictionary mapping plugin IDs to health check results
        """
        enabled_ids = self.registry.list_enabled()
        results = {}
        
        for plugin_id in enabled_ids:
            if not self.should_check(plugin_id):
                continue
            
            plugin = self.registry.get(plugin_id)
            if plugin is None:
                continue
            
            try:
                result = await self.check_plugin(plugin)
                results[plugin_id] = result
            
            except Exception as e:
                logger.error(f"Failed to check plugin {plugin_id}: {e}", exc_info=True)
        
        if results:
            logger.info(f"Completed health checks for {len(results)} plugins")
        
        return results
    
    async def run(self) -> None:
        """
        Run the health check loop.
        
        This is the main async loop that periodically checks all plugins.
        """
        logger.info("Health check scheduler started")
        self._running = True
        
        try:
            while self._running:
                try:
                    await self.check_all_plugins()
                except Exception as e:
                    logger.error(f"Error in health check cycle: {e}", exc_info=True)
                
                # Wait before next cycle (use shorter interval to check "should_check")
                await asyncio.sleep(60)  # Check every minute, individual intervals honored
        
        finally:
            self._running = False
            logger.info("Health check scheduler stopped")
    
    def start(self) -> None:
        """Start the health check scheduler in the background."""
        if self._running:
            logger.warning("Health check scheduler already running")
            return
        
        self._task = asyncio.create_task(self.run())
        logger.info("Health check scheduler task created")
    
    async def stop(self) -> None:
        """Stop the health check scheduler."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health check scheduler stopped")
    
    def get_last_result(self, plugin_id: str) -> Optional[HealthCheckResult]:
        """Get the last health check result for a plugin."""
        return self._last_results.get(plugin_id)
    
    def get_statistics(self) -> dict:
        """Get health check statistics."""
        total_checks = len(self._last_check_time)
        
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNKNOWN: 0,
        }
        
        for result in self._last_results.values():
            status_counts[result.status] += 1
        
        plugins_with_failures = sum(
            1 for count in self._consecutive_failures.values() if count > 0
        )
        
        return {
            "total_plugins_checked": total_checks,
            "status_counts": {k.value: v for k, v in status_counts.items()},
            "plugins_with_consecutive_failures": plugins_with_failures,
            "running": self._running,
        }

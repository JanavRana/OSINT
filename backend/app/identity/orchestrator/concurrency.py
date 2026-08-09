"""
Concurrency governor for managing execution slots.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class ConcurrencyGovernor:
    """
    Manages concurrency limits at global and per-plugin levels.
    
    Ensures:
    - Global limit on concurrent tasks
    - Per-plugin limits based on rate limit configuration
    - Fair scheduling across plugins
    """
    
    def __init__(self, global_limit: int = 200):
        """
        Initialize concurrency governor.
        
        Args:
            global_limit: Maximum concurrent tasks globally
        """
        self.global_limit = global_limit
        self._global_semaphore = asyncio.Semaphore(global_limit)
        
        # Per-plugin semaphores
        self._plugin_semaphores: dict[str, asyncio.Semaphore] = {}
        self._plugin_limits: dict[str, int] = {}
        
        # Tracking
        self._global_active = 0
        self._plugin_active: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    def configure_plugin(self, plugin_id: str, limit: int) -> None:
        """
        Configure concurrency limit for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            limit: Maximum concurrent tasks for this plugin
        """
        self._plugin_limits[plugin_id] = limit
        self._plugin_semaphores[plugin_id] = asyncio.Semaphore(limit)
        logger.debug(f"Configured concurrency limit for {plugin_id}: {limit}")
    
    async def acquire(self, plugin_id: str) -> None:
        """
        Acquire global and plugin-specific execution slots.
        
        Blocks until both are available.
        
        Args:
            plugin_id: Plugin identifier
        """
        # Acquire global slot
        await self._global_semaphore.acquire()
        
        # Acquire plugin-specific slot if configured
        if plugin_id in self._plugin_semaphores:
            await self._plugin_semaphores[plugin_id].acquire()
        
        # Update tracking
        async with self._lock:
            self._global_active += 1
            self._plugin_active[plugin_id] += 1
        
        logger.debug(
            f"Acquired slots for {plugin_id} "
            f"(global: {self._global_active}/{self.global_limit})"
        )
    
    def release(self, plugin_id: str) -> None:
        """
        Release execution slots.
        
        Args:
            plugin_id: Plugin identifier
        """
        # Release plugin-specific slot
        if plugin_id in self._plugin_semaphores:
            self._plugin_semaphores[plugin_id].release()
        
        # Release global slot
        self._global_semaphore.release()
        
        # Update tracking (non-async for cleanup)
        self._global_active = max(0, self._global_active - 1)
        self._plugin_active[plugin_id] = max(0, self._plugin_active[plugin_id] - 1)
        
        logger.debug(
            f"Released slots for {plugin_id} "
            f"(global: {self._global_active}/{self.global_limit})"
        )
    
    def get_available_global_slots(self) -> int:
        """Get number of available global slots."""
        return self.global_limit - self._global_active
    
    def get_available_plugin_slots(self, plugin_id: str) -> Optional[int]:
        """Get number of available slots for a plugin."""
        if plugin_id not in self._plugin_limits:
            return None
        
        limit = self._plugin_limits[plugin_id]
        active = self._plugin_active.get(plugin_id, 0)
        return limit - active
    
    def get_statistics(self) -> dict:
        """Get concurrency statistics."""
        return {
            "global_limit": self.global_limit,
            "global_active": self._global_active,
            "global_available": self.get_available_global_slots(),
            "plugins_configured": len(self._plugin_limits),
            "plugin_active_counts": dict(self._plugin_active),
        }

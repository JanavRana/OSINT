"""
Progress publisher for streaming scan updates to clients.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Optional
from uuid import UUID

from .models import ProgressEvent

logger = logging.getLogger(__name__)


class ProgressPublisher:
    """
    Publishes progress events for scan execution.
    
    In production, would use Redis Streams or PostgreSQL LISTEN/NOTIFY.
    For the framework, provides in-memory pub/sub.
    """
    
    def __init__(self):
        # Subscribers per scan_id
        self._subscribers: dict[UUID, list[Callable]] = defaultdict(list)
        self._event_history: dict[UUID, list[ProgressEvent]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def publish(self, event: ProgressEvent) -> None:
        """
        Publish a progress event.
        
        Args:
            event: Progress event to publish
        """
        scan_id = event.scan_id
        
        async with self._lock:
            # Store in history
            self._event_history[scan_id].append(event)
            
            # Notify subscribers
            if scan_id in self._subscribers:
                for callback in self._subscribers[scan_id]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(
                            f"Error in progress subscriber callback: {e}",
                            exc_info=True
                        )
        
        logger.debug(
            f"Published progress event: {event.event_type} "
            f"for scan {scan_id}"
        )
    
    async def subscribe(
        self,
        scan_id: UUID,
        callback: Callable[[ProgressEvent], None]
    ) -> None:
        """
        Subscribe to progress events for a scan.
        
        Args:
            scan_id: Scan identifier
            callback: Callback function to receive events
        """
        async with self._lock:
            self._subscribers[scan_id].append(callback)
        
        logger.debug(f"Added subscriber for scan {scan_id}")
    
    async def unsubscribe(
        self,
        scan_id: UUID,
        callback: Callable[[ProgressEvent], None]
    ) -> None:
        """
        Unsubscribe from progress events.
        
        Args:
            scan_id: Scan identifier
            callback: Callback to remove
        """
        async with self._lock:
            if scan_id in self._subscribers:
                try:
                    self._subscribers[scan_id].remove(callback)
                except ValueError:
                    pass
        
        logger.debug(f"Removed subscriber for scan {scan_id}")
    
    def get_event_history(
        self,
        scan_id: UUID,
        limit: Optional[int] = None
    ) -> list[ProgressEvent]:
        """
        Get event history for a scan.
        
        Args:
            scan_id: Scan identifier
            limit: Optional limit on number of events
            
        Returns:
            List of progress events
        """
        events = self._event_history.get(scan_id, [])
        if limit:
            return events[-limit:]
        return events
    
    def clear_scan(self, scan_id: UUID) -> None:
        """Clear all data for a scan."""
        self._subscribers.pop(scan_id, None)
        self._event_history.pop(scan_id, None)
        logger.debug(f"Cleared progress data for scan {scan_id}")
    
    def clear(self) -> None:
        """Clear all progress data. Mainly for testing."""
        self._subscribers.clear()
        self._event_history.clear()


# Global singleton instance
_progress_publisher: Optional[ProgressPublisher] = None


def get_progress_publisher() -> ProgressPublisher:
    """Get the global progress publisher."""
    global _progress_publisher
    if _progress_publisher is None:
        _progress_publisher = ProgressPublisher()
    return _progress_publisher


def reset_progress_publisher() -> None:
    """Reset the global publisher. Mainly for testing."""
    global _progress_publisher
    if _progress_publisher:
        _progress_publisher.clear()
    _progress_publisher = None

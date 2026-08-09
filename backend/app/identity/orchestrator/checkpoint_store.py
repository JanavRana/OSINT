"""
Checkpoint store for scan resume support.
"""

import logging
from typing import Optional
from uuid import UUID

from ..types import TaskStatus
from .models import ScanPlan, ScanTask

logger = logging.getLogger(__name__)


class CheckpointStore:
    """
    Stores scan progress for resume capability.
    
    In production, this would persist to PostgreSQL or Redis.
    For the framework, we use in-memory storage.
    """
    
    def __init__(self):
        self._scans: dict[UUID, ScanPlan] = {}
        self._task_status: dict[UUID, dict[str, TaskStatus]] = {}
    
    def save_scan_plan(self, plan: ScanPlan) -> None:
        """
        Save or update a scan plan.
        
        Args:
            plan: Scan plan to save
        """
        self._scans[plan.scan_id] = plan
        
        # Initialize task status tracking
        if plan.scan_id not in self._task_status:
            self._task_status[plan.scan_id] = {}
        
        for task in plan.tasks:
            self._task_status[plan.scan_id][task.plugin_id] = task.status
        
        logger.debug(f"Saved scan plan: {plan.scan_id}")
    
    def update_task_status(
        self,
        scan_id: UUID,
        plugin_id: str,
        status: TaskStatus
    ) -> None:
        """
        Update status of a specific task.
        
        Args:
            scan_id: Scan identifier
            plugin_id: Plugin identifier
            status: New task status
        """
        if scan_id in self._task_status:
            self._task_status[scan_id][plugin_id] = status
            logger.debug(
                f"Updated task status: {scan_id}/{plugin_id} -> {status}"
            )
    
    def get_scan_plan(self, scan_id: UUID) -> Optional[ScanPlan]:
        """Get a saved scan plan."""
        return self._scans.get(scan_id)
    
    def get_task_status(
        self,
        scan_id: UUID,
        plugin_id: str
    ) -> Optional[TaskStatus]:
        """Get status of a specific task."""
        if scan_id in self._task_status:
            return self._task_status[scan_id].get(plugin_id)
        return None
    
    def get_incomplete_tasks(self, scan_id: UUID) -> list[ScanTask]:
        """
        Get tasks that need to be executed or retried.
        
        Args:
            scan_id: Scan identifier
            
        Returns:
            List of incomplete tasks
        """
        plan = self.get_scan_plan(scan_id)
        if not plan:
            return []
        
        terminal_states = {
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,  # After max retries
            TaskStatus.SKIPPED_CIRCUIT_OPEN,
            TaskStatus.SKIPPED_DISABLED,
            TaskStatus.CANCELLED,
        }
        
        incomplete = [
            task for task in plan.tasks
            if task.status not in terminal_states
        ]
        
        return incomplete
    
    def delete_scan(self, scan_id: UUID) -> bool:
        """
        Delete a scan's checkpoint data.
        
        Args:
            scan_id: Scan identifier
            
        Returns:
            True if scan was deleted
        """
        if scan_id in self._scans:
            del self._scans[scan_id]
            self._task_status.pop(scan_id, None)
            logger.info(f"Deleted scan checkpoint: {scan_id}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all checkpoints. Mainly for testing."""
        self._scans.clear()
        self._task_status.clear()

"""
Data models for the orchestrator.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from ..types import IdentifierType, ScanStatus, TaskStatus


@dataclass
class ScanTask:
    """A single task within a scan."""
    id: UUID
    scan_id: UUID
    plugin_id: str
    identifier_type: IdentifierType
    identifier_value: str
    status: TaskStatus = TaskStatus.QUEUED
    priority: int = 0
    attempt_count: int = 0
    max_retries: int = 2
    last_error: Optional[str] = None
    result: Optional[Any] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScanPlan:
    """
    Complete plan for a scan.
    
    Contains the flat list of tasks to execute.
    """
    scan_id: UUID
    investigation_id: UUID
    identifier_type: IdentifierType
    identifier_value: str
    tasks: list[ScanTask] = field(default_factory=list)
    status: ScanStatus = ScanStatus.QUEUED
    options: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def get_task_counts(self) -> dict[str, int]:
        """Get count of tasks by status."""
        counts = {}
        for status in TaskStatus:
            counts[status.value] = sum(
                1 for task in self.tasks if task.status == status
            )
        return counts
    
    def is_complete(self) -> bool:
        """Check if all tasks are in a terminal state."""
        terminal_states = {
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.SKIPPED_CIRCUIT_OPEN,
            TaskStatus.SKIPPED_DISABLED,
            TaskStatus.CANCELLED,
        }
        return all(task.status in terminal_states for task in self.tasks)
    
    def has_failures(self) -> bool:
        """Check if any tasks failed."""
        return any(task.status == TaskStatus.FAILED for task in self.tasks)


@dataclass
class ProgressEvent:
    """Progress event for streaming to clients."""
    scan_id: UUID
    event_type: str  # task_started, task_complete, task_failed, task_skipped, scan_complete
    plugin_id: Optional[str] = None
    task_id: Optional[UUID] = None
    message: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

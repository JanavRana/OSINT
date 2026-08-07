"""
Tests for orchestrator components.
"""

import pytest
from uuid import uuid4

from app.identity.orchestrator.models import ScanTask, ScanPlan, ProgressEvent
from app.identity.orchestrator.planner import ScanPlanner
from app.identity.orchestrator.concurrency import ConcurrencyGovernor
from app.identity.orchestrator.checkpoint_store import CheckpointStore
from app.identity.plugin_runtime.registry import PluginRegistry
from app.identity.types import IdentifierType, PluginCategory, ScanStatus, TaskStatus


# Use the MockPlugin from test_plugin_registry
class MockPlugin:
    """Mock plugin for testing."""
    
    def __init__(self, plugin_id: str, category: PluginCategory, tags: list[str] = None, enabled: bool = True):
        from app.identity.plugin_base import PluginMetadata
        self._id = plugin_id
        self._category = category
        self._tags = tags or []
        self._enabled = enabled
    
    def describe(self):
        from app.identity.plugin_base import PluginMetadata
        return PluginMetadata(
            id=self._id,
            display_name=f"Mock {self._id}",
            category=self._category,
            identifier_type=IdentifierType.USERNAME,
            version="1.0.0",
            enabled=self._enabled,
            tags=self._tags,
        )


def test_scan_plan_task_counts():
    """Test counting tasks by status."""
    plan = ScanPlan(
        scan_id=uuid4(),
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser"
    )
    
    task1 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-1",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.SUCCESS
    )
    task2 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-2",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.FAILED
    )
    task3 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-3",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.QUEUED
    )
    
    plan.tasks = [task1, task2, task3]
    
    counts = plan.get_task_counts()
    
    assert counts[TaskStatus.SUCCESS.value] == 1
    assert counts[TaskStatus.FAILED.value] == 1
    assert counts[TaskStatus.QUEUED.value] == 1


def test_scan_plan_is_complete():
    """Test checking if scan plan is complete."""
    plan = ScanPlan(
        scan_id=uuid4(),
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser"
    )
    
    task1 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-1",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.SUCCESS
    )
    task2 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-2",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.QUEUED
    )
    
    plan.tasks = [task1, task2]
    
    # Not complete with queued task
    assert plan.is_complete() is False
    
    # Complete when all terminal
    task2.status = TaskStatus.SUCCESS
    assert plan.is_complete() is True


def test_scan_planner():
    """Test scan planner."""
    registry = PluginRegistry()
    
    # Register some plugins
    plugin1 = MockPlugin("social-1", PluginCategory.SOCIAL, tags=["high-confidence"])
    plugin2 = MockPlugin("social-2", PluginCategory.SOCIAL, tags=["medium"])
    plugin3 = MockPlugin("dev-1", PluginCategory.DEVELOPER, tags=["api"])
    
    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)
    
    planner = ScanPlanner(registry)
    
    # Plan a scan
    plan = planner.plan_scan(
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        options={}
    )
    
    # Should have created tasks for all enabled plugins
    assert len(plan.tasks) == 3
    assert plan.identifier_value == "testuser"
    assert plan.status == ScanStatus.QUEUED


def test_scan_planner_with_filters():
    """Test scan planner with category filter."""
    registry = PluginRegistry()
    
    plugin1 = MockPlugin("social-1", PluginCategory.SOCIAL)
    plugin2 = MockPlugin("dev-1", PluginCategory.DEVELOPER)
    
    registry.register(plugin1)
    registry.register(plugin2)
    
    planner = ScanPlanner(registry)
    
    # Plan scan with category filter
    plan = planner.plan_scan(
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        options={"category": "social"}
    )
    
    # Should only have social plugins
    assert len(plan.tasks) == 1
    assert plan.tasks[0].plugin_id == "social-1"


@pytest.mark.asyncio
async def test_concurrency_governor():
    """Test concurrency governor."""
    governor = ConcurrencyGovernor(global_limit=10)
    
    # Configure a plugin
    governor.configure_plugin("plugin-1", limit=3)
    
    # Acquire slots
    await governor.acquire("plugin-1")
    
    assert governor.get_available_global_slots() == 9
    assert governor.get_available_plugin_slots("plugin-1") == 2
    
    # Release slots
    governor.release("plugin-1")
    
    assert governor.get_available_global_slots() == 10
    assert governor.get_available_plugin_slots("plugin-1") == 3


def test_checkpoint_store():
    """Test checkpoint store."""
    store = CheckpointStore()
    
    plan = ScanPlan(
        scan_id=uuid4(),
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser"
    )
    
    task1 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-1",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.QUEUED
    )
    plan.tasks = [task1]
    
    # Save plan
    store.save_scan_plan(plan)
    
    # Retrieve plan
    retrieved = store.get_scan_plan(plan.scan_id)
    assert retrieved is not None
    assert retrieved.scan_id == plan.scan_id
    
    # Update task status
    store.update_task_status(plan.scan_id, "plugin-1", TaskStatus.SUCCESS)
    
    status = store.get_task_status(plan.scan_id, "plugin-1")
    assert status == TaskStatus.SUCCESS


def test_checkpoint_store_incomplete_tasks():
    """Test getting incomplete tasks."""
    store = CheckpointStore()
    
    plan = ScanPlan(
        scan_id=uuid4(),
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser"
    )
    
    task1 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-1",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.SUCCESS
    )
    task2 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-2",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.QUEUED
    )
    task3 = ScanTask(
        id=uuid4(),
        scan_id=plan.scan_id,
        plugin_id="plugin-3",
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser",
        status=TaskStatus.RUNNING
    )
    
    plan.tasks = [task1, task2, task3]
    store.save_scan_plan(plan)
    
    incomplete = store.get_incomplete_tasks(plan.scan_id)
    
    # Should only return queued and running
    assert len(incomplete) == 2
    assert task1 not in incomplete

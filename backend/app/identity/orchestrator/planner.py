"""
Scan planner - builds ScanPlan from identifier and options.
"""

import logging
from uuid import UUID, uuid4

from ..plugin_runtime.registry import PluginRegistry
from ..types import IdentifierType, PluginCategory
from .models import ScanPlan, ScanTask

logger = logging.getLogger(__name__)


class ScanPlanner:
    """
    Plans scan execution by resolving eligible plugins and building task list.
    """
    
    def __init__(self, registry: PluginRegistry):
        """
        Initialize planner.
        
        Args:
            registry: Plugin registry to query for eligible plugins
        """
        self.registry = registry
    
    def plan_scan(
        self,
        investigation_id: UUID,
        identifier_type: IdentifierType,
        identifier_value: str,
        options: dict = None
    ) -> ScanPlan:
        """
        Build a scan plan.
        
        Args:
            investigation_id: Investigation ID
            identifier_type: Type of identifier
            identifier_value: Identifier value
            options: Optional scan options (filters, tags, etc.)
            
        Returns:
            ScanPlan with tasks for all eligible plugins
        """
        options = options or {}
        scan_id = uuid4()
        
        logger.info(
            f"Planning scan {scan_id} for {identifier_type}/{identifier_value}"
        )
        
        # Resolve eligible plugins
        plugin_ids = self._resolve_plugins(identifier_type, options)
        
        logger.info(f"Resolved {len(plugin_ids)} plugins for scan {scan_id}")
        
        # Create tasks
        tasks = []
        for plugin_id in plugin_ids:
            task = ScanTask(
                id=uuid4(),
                scan_id=scan_id,
                plugin_id=plugin_id,
                identifier_type=identifier_type,
                identifier_value=identifier_value,
                priority=self._calculate_priority(plugin_id, options),
                max_retries=options.get('max_retries', 2),
            )
            tasks.append(task)
        
        # Sort by priority (higher first)
        tasks.sort(key=lambda t: t.priority, reverse=True)
        
        plan = ScanPlan(
            scan_id=scan_id,
            investigation_id=investigation_id,
            identifier_type=identifier_type,
            identifier_value=identifier_value,
            tasks=tasks,
            options=options,
        )
        
        logger.info(
            f"Scan plan created: {len(tasks)} tasks, "
            f"priority range: {min(t.priority for t in tasks) if tasks else 0}-"
            f"{max(t.priority for t in tasks) if tasks else 0}"
        )
        
        return plan
    
    def _resolve_plugins(
        self,
        identifier_type: IdentifierType,
        options: dict
    ) -> list[str]:
        """
        Resolve which plugins are eligible for this scan.
        
        Args:
            identifier_type: Type of identifier
            options: Scan options with filters
            
        Returns:
            List of plugin IDs
        """
        category = options.get('category')
        tags = options.get('tags', [])
        match_all_tags = options.get('match_all_tags', False)
        healthy_only = options.get('healthy_only', False)
        
        # Filter plugins
        plugin_ids = self.registry.filter_plugins(
            identifier_type=identifier_type,
            category=PluginCategory(category) if category else None,
            tags=tags if tags else None,
            match_all_tags=match_all_tags,
            enabled_only=True,
            healthy_only=healthy_only,
        )
        
        return plugin_ids
    
    def _calculate_priority(self, plugin_id: str, options: dict) -> int:
        """
        Calculate task priority.
        
        Higher priority tasks are executed first.
        
        Args:
            plugin_id: Plugin identifier
            options: Scan options
            
        Returns:
            Priority value (higher = more urgent)
        """
        base_priority = 0
        
        metadata = self.registry.get_metadata(plugin_id)
        if not metadata:
            return base_priority
        
        # High-confidence platforms get priority
        if 'high-confidence' in metadata.tags:
            base_priority += 10
        
        # Fast platforms get priority
        if 'fast' in metadata.tags:
            base_priority += 5
        
        # API-based platforms typically more reliable
        if 'api' in metadata.tags:
            base_priority += 3
        
        # Apply user-specified priorities
        priority_overrides = options.get('priority_overrides', {})
        if plugin_id in priority_overrides:
            base_priority = priority_overrides[plugin_id]
        
        return base_priority

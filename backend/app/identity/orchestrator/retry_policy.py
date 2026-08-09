"""
Retry policy engine with backoff strategies.
"""

import asyncio
import logging
import random
from typing import Optional

from ..types import BackoffStrategy
from .models import ScanTask

logger = logging.getLogger(__name__)


class RetryPolicy:
    """
    Determines if and when a task should be retried.
    """
    
    def __init__(
        self,
        default_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        base_delay_ms: int = 250,
        max_delay_ms: int = 30000,
        jitter: bool = True
    ):
        """
        Initialize retry policy.
        
        Args:
            default_strategy: Default backoff strategy
            base_delay_ms: Base delay in milliseconds
            max_delay_ms: Maximum delay in milliseconds
            jitter: Whether to add random jitter to delays
        """
        self.default_strategy = default_strategy
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter
    
    def should_retry(self, task: ScanTask) -> bool:
        """
        Determine if a task should be retried.
        
        Args:
            task: Task to check
            
        Returns:
            True if task should be retried
        """
        if task.attempt_count >= task.max_retries:
            return False
        
        # Don't retry certain failures
        if task.last_error:
            # In production, would check for specific error types
            # e.g., 401/403 shouldn't be retried
            pass
        
        return True
    
    def calculate_delay(
        self,
        task: ScanTask,
        strategy: Optional[BackoffStrategy] = None
    ) -> float:
        """
        Calculate retry delay in seconds.
        
        Args:
            task: Task to retry
            strategy: Optional backoff strategy override
            
        Returns:
            Delay in seconds
        """
        strategy = strategy or self.default_strategy
        attempt = task.attempt_count
        
        if strategy == BackoffStrategy.NONE:
            delay_ms = 0
        
        elif strategy == BackoffStrategy.LINEAR:
            delay_ms = self.base_delay_ms * (attempt + 1)
        
        elif strategy == BackoffStrategy.EXPONENTIAL:
            delay_ms = self.base_delay_ms * (2 ** attempt)
        
        else:
            delay_ms = self.base_delay_ms
        
        # Apply maximum
        delay_ms = min(delay_ms, self.max_delay_ms)
        
        # Add jitter
        if self.jitter and delay_ms > 0:
            jitter_amount = delay_ms * 0.1
            delay_ms += random.uniform(-jitter_amount, jitter_amount)
        
        delay_seconds = delay_ms / 1000.0
        
        logger.debug(
            f"Calculated retry delay for task {task.id}: "
            f"{delay_seconds:.2f}s (attempt {attempt}, strategy={strategy})"
        )
        
        return delay_seconds
    
    async def wait_for_retry(
        self,
        task: ScanTask,
        strategy: Optional[BackoffStrategy] = None
    ) -> None:
        """
        Wait for the calculated retry delay.
        
        Args:
            task: Task to retry
            strategy: Optional backoff strategy override
        """
        delay = self.calculate_delay(task, strategy)
        if delay > 0:
            await asyncio.sleep(delay)


class RetryPolicyEngine:
    """
    Engine managing retry policies across all tasks.
    """
    
    def __init__(self, default_policy: Optional[RetryPolicy] = None):
        """
        Initialize retry policy engine.
        
        Args:
            default_policy: Default retry policy
        """
        self.default_policy = default_policy or RetryPolicy()
        self._plugin_policies: dict[str, RetryPolicy] = {}
    
    def configure_plugin(
        self,
        plugin_id: str,
        strategy: BackoffStrategy,
        base_delay_ms: int
    ) -> None:
        """
        Configure custom retry policy for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            strategy: Backoff strategy
            base_delay_ms: Base delay in milliseconds
        """
        policy = RetryPolicy(
            default_strategy=strategy,
            base_delay_ms=base_delay_ms
        )
        self._plugin_policies[plugin_id] = policy
        logger.debug(
            f"Configured retry policy for {plugin_id}: "
            f"strategy={strategy}, base_delay={base_delay_ms}ms"
        )
    
    def get_policy(self, plugin_id: str) -> RetryPolicy:
        """Get retry policy for a plugin."""
        return self._plugin_policies.get(plugin_id, self.default_policy)
    
    def should_retry(self, task: ScanTask) -> bool:
        """Check if task should be retried."""
        policy = self.get_policy(task.plugin_id)
        return policy.should_retry(task)
    
    async def wait_and_requeue(self, task: ScanTask) -> bool:
        """
        Wait for retry delay and prepare task for requeue.
        
        Args:
            task: Task to retry
            
        Returns:
            True if task should be requeued
        """
        policy = self.get_policy(task.plugin_id)
        
        if not policy.should_retry(task):
            return False
        
        await policy.wait_for_retry(task)
        
        # Increment attempt count
        task.attempt_count += 1
        
        return True

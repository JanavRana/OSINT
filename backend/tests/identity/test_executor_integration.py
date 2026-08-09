"""
Integration tests for username executor with HTTP mocking.

Tests the complete execution flow with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import httpx

from app.identity.username.loader import PlatformLoader
from app.identity.username.executor import create_platform_plugin
from app.identity.plugin_base import ExecutionContext, DetectionOutcome
from app.identity.types import IdentifierType


class TestExecutorWithMockedHTTP:
    """Test executor with mocked HTTP responses."""
    
    @pytest.mark.asyncio
    async def test_github_user_exists(self):
        """Test GitHub platform with user that exists."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "bio": "Test bio",
            "created_at": "2020-01-01T00:00:00Z",
            "location": "San Francisco",
            "company": "Test Company",
            "public_repos": 42,
            "followers": 100
        })
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        assert result.success is True
        assert result.identifier_value == "testuser"
        assert result.http_status == 200
        
        # Check detection outcome
        outcome = result.payload
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is True
        assert outcome.http_status == 200
        assert outcome.strategy_confidence_hint > 0.9
        
        # Check evidence fields
        assert "display_name" in outcome.evidence_fields
        assert outcome.evidence_fields["display_name"] == "Test User"
        assert "avatar_url" in outcome.evidence_fields
    
    @pytest.mark.asyncio
    async def test_github_user_not_found(self):
        """Test GitHub platform with user that doesn't exist."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client with 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="nonexistent_user_xyz123",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        assert result.success is True
        assert result.http_status == 404
        
        # Check detection outcome
        outcome = result.payload
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is False
        assert outcome.http_status == 404
        assert outcome.strategy_confidence_hint > 0.8
    
    @pytest.mark.asyncio
    async def test_npm_status_code_strategy(self):
        """Test npm platform using status code strategy."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("npm.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>npm user page</html>"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        assert result.success is True
        assert result.http_status == 200
        
        outcome = result.payload
        assert outcome.exists is True
    
    @pytest.mark.asyncio
    async def test_leetcode_graphql_strategy(self):
        """Test LeetCode platform using GraphQL strategy."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("leetcode.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client for GraphQL
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "data": {
                "matchedUser": {
                    "username": "testuser",
                    "profile": {
                        "realName": "Test User",
                        "userAvatar": "https://assets.leetcode.com/users/testuser/avatar.png",
                        "reputation": 1500
                    }
                }
            }
        })
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        assert result.success is True
        assert result.http_status == 200
        
        outcome = result.payload
        assert outcome.exists is True
        assert outcome.strategy_confidence_hint > 0.9
    
    @pytest.mark.asyncio
    async def test_http_timeout_handling(self):
        """Test handling of HTTP timeouts."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client that raises timeout
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        # Executor catches exceptions and returns unknown outcome
        assert result.success is True
        outcome = result.payload
        assert outcome.exists == "unknown"
        assert outcome.strategy_confidence_hint == 0.0
    
    @pytest.mark.asyncio
    async def test_http_403_forbidden(self):
        """Test handling of 403 Forbidden responses."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client with 403
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json = MagicMock(return_value={"message": "API rate limit exceeded"})
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        # Should handle 403 gracefully
        assert result.success is True  # Request succeeded, but detection is unknown
        outcome = result.payload
        assert outcome.exists == "unknown"  # Can't determine from 403
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON responses."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client with malformed JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(side_effect=ValueError("Invalid JSON"))
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        # Should handle JSON parse error gracefully
        assert result.success is True
        outcome = result.payload
        assert outcome.exists == "unknown"  # Can't parse response
    
    @pytest.mark.asyncio
    async def test_reddit_json_api_with_error_field(self):
        """Test Reddit platform with error field in response."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("reddit.yaml")
        
        plugin = create_platform_plugin(definition)
        
        # Mock HTTP client with error in JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "error": 404,
            "message": "User not found"
        })
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        context = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="nonexistent",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=mock_client,
            logger=None,
        )
        
        result = await plugin.execute(context)
        
        assert result.success is True
        outcome = result.payload
        assert outcome.exists is False
        assert "error" in outcome.evidence_fields


class TestConcurrentExecution:
    """Test concurrent execution of multiple platforms."""
    
    @pytest.mark.asyncio
    async def test_parallel_platform_execution(self):
        """Test executing multiple platforms in parallel."""
        import asyncio
        
        loader = PlatformLoader()
        github_def = loader.load_platform_file("github.yaml")
        reddit_def = loader.load_platform_file("reddit.yaml")
        npm_def = loader.load_platform_file("npm.yaml")
        
        github_plugin = create_platform_plugin(github_def)
        reddit_plugin = create_platform_plugin(reddit_def)
        npm_plugin = create_platform_plugin(npm_def)
        
        # Create mock responses
        github_response = MagicMock()
        github_response.status_code = 200
        github_response.json = MagicMock(return_value={"login": "testuser"})
        
        reddit_response = MagicMock()
        reddit_response.status_code = 200
        reddit_response.json = MagicMock(return_value={"data": {"name": "testuser"}})
        
        npm_response = MagicMock()
        npm_response.status_code = 200
        
        # Mock HTTP clients
        github_client = AsyncMock()
        github_client.get = AsyncMock(return_value=github_response)
        
        reddit_client = AsyncMock()
        reddit_client.get = AsyncMock(return_value=reddit_response)
        
        npm_client = AsyncMock()
        npm_client.get = AsyncMock(return_value=npm_response)
        
        # Create contexts
        github_ctx = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=github_client,
            logger=None,
        )
        
        reddit_ctx = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=reddit_client,
            logger=None,
        )
        
        npm_ctx = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=npm_client,
            logger=None,
        )
        
        # Execute in parallel
        results = await asyncio.gather(
            github_plugin.execute(github_ctx),
            reddit_plugin.execute(reddit_ctx),
            npm_plugin.execute(npm_ctx),
            return_exceptions=True
        )
        
        # All should succeed
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_one_platform_failure_doesnt_stop_others(self):
        """Test that one platform failure doesn't stop others."""
        import asyncio
        
        loader = PlatformLoader()
        github_def = loader.load_platform_file("github.yaml")
        reddit_def = loader.load_platform_file("reddit.yaml")
        
        github_plugin = create_platform_plugin(github_def)
        reddit_plugin = create_platform_plugin(reddit_def)
        
        # GitHub fails with timeout
        github_client = AsyncMock()
        github_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        
        # Reddit succeeds
        reddit_response = MagicMock()
        reddit_response.status_code = 200
        reddit_response.json = MagicMock(return_value={"data": {"name": "testuser"}})
        
        reddit_client = AsyncMock()
        reddit_client.get = AsyncMock(return_value=reddit_response)
        
        github_ctx = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=github_client,
            logger=None,
        )
        
        reddit_ctx = ExecutionContext(
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            investigation_id=uuid4(),
            scan_id=uuid4(),
            task_id=uuid4(),
            http_client=reddit_client,
            logger=None,
        )
        
        # Execute with return_exceptions=True
        results = await asyncio.gather(
            github_plugin.execute(github_ctx),
            reddit_plugin.execute(reddit_ctx),
            return_exceptions=True
        )
        
        # GitHub should return unknown (not crash the scan)
        assert results[0].success is True
        assert results[0].payload.exists == "unknown"
        
        # Reddit should succeed
        assert results[1].success is True
        outcome = results[1].payload
        assert outcome.exists is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

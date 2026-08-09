"""
Tests for username detection strategies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.identity.username.detection.base import get_strategy_registry
from app.identity.username.detection.strategies import (
    StatusCodeStrategy,
    JsonApiStrategy,
    GraphQLStrategy,
    RedirectStrategy,
    RegexBodyStrategy,
    HtmlParseStrategy,
    CustomLogicStrategy,
)
from app.identity.username.schema.platform_schema import (
    PlatformDefinition,
    DetectionConfig,
    DetectionStrategyType,
    StatusCodeDetectionConfig,
    JsonApiDetectionConfig,
    GraphQLDetectionConfig,
)
from app.identity.plugin_base import DetectionOutcome
from app.identity.types import PluginCategory, VerificationMethod, BackoffStrategy, RateLimitScope, CaptchaRisk


class TestStrategyRegistry:
    """Test detection strategy registration."""
    
    def test_strategies_registered(self):
        """Test that all strategies are registered."""
        registry = get_strategy_registry()
        
        expected_strategies = [
            'status_code',
            'redirect',
            'regex_body',
            'json_api',
            'graphql',
            'html_parse',
            'custom',
        ]
        
        registered = registry.list_strategies()
        
        for strategy in expected_strategies:
            assert strategy in registered, f"Strategy '{strategy}' not registered"
    
    def test_create_strategy_instances(self):
        """Test creating instances of registered strategies."""
        registry = get_strategy_registry()
        
        strategies = ['status_code', 'json_api', 'graphql']
        
        for strategy_name in strategies:
            instance = registry.create_instance(strategy_name)
            assert instance is not None, f"Failed to create instance of '{strategy_name}'"
            assert hasattr(instance, 'check')
    
    def test_unknown_strategy_returns_none(self):
        """Test that unknown strategy returns None."""
        registry = get_strategy_registry()
        
        instance = registry.create_instance('nonexistent_strategy')
        assert instance is None


class TestStatusCodeStrategy:
    """Test status code detection strategy."""
    
    def create_test_definition(self):
        """Create a test platform definition for status code strategy."""
        return PlatformDefinition(
            id='test-platform',
            display_name='Test Platform',
            category=PluginCategory.SOCIAL,
            homepage='https://example.com',
            profile_url_template='https://example.com/users/{username}',
            detection=DetectionConfig(
                strategy=DetectionStrategyType.STATUS_CODE,
                status_code=StatusCodeDetectionConfig(
                    success_codes=[200],
                    not_found_codes=[404]
                )
            ),
            network={
                'timeout_seconds': 5,
                'retries': 2,
                'backoff': BackoffStrategy.EXPONENTIAL,
                'base_delay_ms': 250,
                'headers': {},
            },
            rate_limit={
                'requests_per_minute': 30,
                'scope': RateLimitScope.GLOBAL,
            },
            auth={
                'login_required': False,
                'captcha_risk': CaptchaRisk.LOW,
                'api_key_required': False,
                'oauth_required': False,
            },
            confidence_rules={
                'base_reliability': 0.85,
                'verification_method': VerificationMethod.HTML_SCRAPE,
                'corroboration_fields': [],
            },
            parser={
                'type': 'html',
                'fields': {},
            },
        )
    
    @pytest.mark.asyncio
    async def test_status_code_exists(self):
        """Test status code strategy when profile exists."""
        strategy = StatusCodeStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        http_client = AsyncMock()
        http_client.get = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='testuser',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is True
        assert outcome.http_status == 200
        assert outcome.strategy_confidence_hint > 0.5
    
    @pytest.mark.asyncio
    async def test_status_code_not_found(self):
        """Test status code strategy when profile doesn't exist."""
        strategy = StatusCodeStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        http_client = AsyncMock()
        http_client.get = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='nonexistent',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is False
        assert outcome.http_status == 404
        assert outcome.strategy_confidence_hint > 0.5
    
    @pytest.mark.asyncio
    async def test_status_code_unknown(self):
        """Test status code strategy with unexpected status."""
        strategy = StatusCodeStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 503
        
        http_client = AsyncMock()
        http_client.get = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='testuser',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists == "unknown"
        assert outcome.http_status == 503
        assert outcome.strategy_confidence_hint < 0.5


class TestJsonApiStrategy:
    """Test JSON API detection strategy."""
    
    def create_test_definition(self):
        """Create a test platform definition for JSON API strategy."""
        return PlatformDefinition(
            id='test-api-platform',
            display_name='Test API Platform',
            category=PluginCategory.DEVELOPER,
            homepage='https://api.example.com',
            profile_url_template='https://example.com/{username}',
            api_endpoint='https://api.example.com/users/{username}',
            detection=DetectionConfig(
                strategy=DetectionStrategyType.JSON_API,
                json_api=JsonApiDetectionConfig(
                    success_field='$.username',
                    not_found_status=404
                )
            ),
            network={
                'timeout_seconds': 5,
                'retries': 2,
                'backoff': BackoffStrategy.EXPONENTIAL,
                'base_delay_ms': 250,
                'headers': {},
            },
            rate_limit={
                'requests_per_minute': 30,
                'scope': RateLimitScope.GLOBAL,
            },
            auth={
                'login_required': False,
                'captcha_risk': CaptchaRisk.LOW,
                'api_key_required': False,
                'oauth_required': False,
            },
            confidence_rules={
                'base_reliability': 0.95,
                'verification_method': VerificationMethod.API_CONFIRMED,
                'corroboration_fields': ['display_name'],
            },
            parser={
                'type': 'json',
                'fields': {
                    'display_name': '$.name',
                },
            },
        )
    
    @pytest.mark.asyncio
    async def test_json_api_exists(self):
        """Test JSON API strategy when user exists."""
        strategy = JsonApiStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            'username': 'testuser',
            'name': 'Test User',
        })
        
        http_client = AsyncMock()
        http_client.get = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='testuser',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is True
        assert outcome.http_status == 200
        assert outcome.strategy_confidence_hint > 0.9
        assert 'display_name' in outcome.evidence_fields
        assert outcome.evidence_fields['display_name'] == 'Test User'
    
    @pytest.mark.asyncio
    async def test_json_api_not_found(self):
        """Test JSON API strategy when user doesn't exist."""
        strategy = JsonApiStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        http_client = AsyncMock()
        http_client.get = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='nonexistent',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is False
        assert outcome.http_status == 404
        assert outcome.strategy_confidence_hint > 0.8


class TestGraphQLStrategy:
    """Test GraphQL detection strategy."""
    
    def create_test_definition(self):
        """Create a test platform definition for GraphQL strategy."""
        return PlatformDefinition(
            id='test-graphql-platform',
            display_name='Test GraphQL Platform',
            category=PluginCategory.DEVELOPER,
            homepage='https://graphql.example.com',
            profile_url_template='https://example.com/{username}',
            api_endpoint='https://graphql.example.com/api',
            detection=DetectionConfig(
                strategy=DetectionStrategyType.GRAPHQL,
                graphql=GraphQLDetectionConfig(
                    query='query { user(username: "{username}") { username } }',
                    success_field='$.user.username',
                    variables={}
                )
            ),
            network={
                'timeout_seconds': 8,
                'retries': 2,
                'backoff': BackoffStrategy.EXPONENTIAL,
                'base_delay_ms': 250,
                'headers': {},
            },
            rate_limit={
                'requests_per_minute': 20,
                'scope': RateLimitScope.GLOBAL,
            },
            auth={
                'login_required': False,
                'captcha_risk': CaptchaRisk.LOW,
                'api_key_required': False,
                'oauth_required': False,
            },
            confidence_rules={
                'base_reliability': 0.90,
                'verification_method': VerificationMethod.GRAPHQL_CONFIRMED,
                'corroboration_fields': [],
            },
            parser={
                'type': 'json',
                'fields': {},
            },
        )
    
    @pytest.mark.asyncio
    async def test_graphql_exists(self):
        """Test GraphQL strategy when user exists."""
        strategy = GraphQLStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            'data': {
                'user': {
                    'username': 'testuser'
                }
            }
        })
        
        http_client = AsyncMock()
        http_client.post = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='testuser',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is True
        assert outcome.http_status == 200
        assert outcome.strategy_confidence_hint > 0.9
    
    @pytest.mark.asyncio
    async def test_graphql_not_found(self):
        """Test GraphQL strategy when user doesn't exist."""
        strategy = GraphQLStrategy()
        definition = self.create_test_definition()
        
        # Mock HTTP client with GraphQL error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            'errors': [
                {'message': 'User not found'}
            ]
        })
        
        http_client = AsyncMock()
        http_client.post = AsyncMock(return_value=mock_response)
        
        outcome = await strategy.check(
            username='nonexistent',
            definition=definition,
            http_client=http_client,
            logger=None
        )
        
        assert isinstance(outcome, DetectionOutcome)
        assert outcome.exists is False
        assert outcome.http_status == 200
        assert outcome.strategy_confidence_hint > 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

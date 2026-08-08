"""
Concrete detection strategy implementations.

Each strategy implements a different method for determining username existence.
"""

import json
import re
from typing import Any, Optional

from ...plugin_base import DetectionOutcome
from ..schema.platform_schema import PlatformDefinition
from .base import DetectionStrategy, register_strategy


@register_strategy('status_code')
class StatusCodeStrategy(DetectionStrategy):
    """
    Detection based on HTTP status codes.
    
    Profile exists if status code is in success_codes list.
    """
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via HTTP status code."""
        url = self._build_url(username, definition)
        headers = self._get_headers(definition)
        timeout = self._get_timeout(definition)
        
        config = definition.detection.status_code
        if not config:
            raise ValueError("status_code configuration missing")
        
        try:
            response = await http_client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True
            )
            
            status_code = response.status_code
            
            # Determine existence based on status code
            if status_code in config.success_codes:
                exists = True
                confidence = 0.85
            elif status_code in config.not_found_codes:
                exists = False
                confidence = 0.9
            else:
                exists = "unknown"
                confidence = 0.3
            
            return DetectionOutcome(
                exists=exists,
                http_status=status_code,
                strategy_confidence_hint=confidence
            )
        
        except Exception as e:
            if logger:
                logger.warning(f"Status code check failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )


@register_strategy('redirect')
class RedirectStrategy(DetectionStrategy):
    """
    Detection based on redirect patterns.
    
    Follows redirects and checks if final URL matches expected pattern.
    """
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via redirect patterns."""
        url = self._build_url(username, definition)
        headers = self._get_headers(definition)
        timeout = self._get_timeout(definition)
        
        config = definition.detection.redirect
        if not config:
            raise ValueError("redirect configuration missing")
        
        try:
            response = await http_client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                max_redirects=config.max_redirects
            )
            
            final_url = str(response.url)
            status_code = response.status_code
            
            # Check patterns
            exists = "unknown"
            confidence = 0.5
            
            if config.success_pattern:
                if re.search(config.success_pattern, final_url, re.IGNORECASE):
                    exists = True
                    confidence = 0.8
            
            if config.not_found_pattern:
                if re.search(config.not_found_pattern, final_url, re.IGNORECASE):
                    exists = False
                    confidence = 0.85
            
            return DetectionOutcome(
                exists=exists,
                http_status=status_code,
                evidence_fields={"final_url": final_url},
                strategy_confidence_hint=confidence
            )
        
        except Exception as e:
            if logger:
                logger.warning(f"Redirect check failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )


@register_strategy('regex_body')
class RegexBodyStrategy(DetectionStrategy):
    """
    Detection based on regex patterns in response body.
    
    Checks if response body contains patterns indicating existence/non-existence.
    """
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via regex in response body."""
        url = self._build_url(username, definition)
        headers = self._get_headers(definition)
        timeout = self._get_timeout(definition)
        
        config = definition.detection.regex
        if not config:
            raise ValueError("regex configuration missing")
        
        try:
            response = await http_client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True
            )
            
            status_code = response.status_code
            body = response.text
            
            flags = re.IGNORECASE if config.case_insensitive else 0
            
            exists = "unknown"
            confidence = 0.5
            
            # Check exists pattern
            if config.exists_pattern:
                if re.search(config.exists_pattern, body, flags):
                    exists = True
                    confidence = 0.75
            
            # Check not-exists pattern (overrides exists)
            if config.not_exists_pattern:
                if re.search(config.not_exists_pattern, body, flags):
                    exists = False
                    confidence = 0.8
            
            return DetectionOutcome(
                exists=exists,
                http_status=status_code,
                strategy_confidence_hint=confidence
            )
        
        except Exception as e:
            if logger:
                logger.warning(f"Regex check failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )


@register_strategy('json_api')
class JsonApiStrategy(DetectionStrategy):
    """
    Detection via JSON API.
    
    Calls API endpoint and checks for presence of expected fields.
    """
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via JSON API."""
        url = self._build_url(username, definition, use_api=True)
        headers = self._get_headers(definition)
        timeout = self._get_timeout(definition)
        
        # Add JSON accept header
        headers['Accept'] = 'application/json'
        
        config = definition.detection.json_api
        if not config:
            raise ValueError("json_api configuration missing")
        
        try:
            response = await http_client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True
            )
            
            status_code = response.status_code
            
            # Check for not-found status
            if status_code == config.not_found_status:
                return DetectionOutcome(
                    exists=False,
                    http_status=status_code,
                    strategy_confidence_hint=0.9
                )
            
            # Try to parse JSON
            try:
                data = response.json()
            except Exception:
                return DetectionOutcome(
                    exists="unknown",
                    http_status=status_code,
                    strategy_confidence_hint=0.2
                )
            
            # Check for error field
            if config.error_field:
                error_value = self._extract_json_path(data, config.error_field)
                if error_value:
                    return DetectionOutcome(
                        exists=False,
                        http_status=status_code,
                        evidence_fields={"error": error_value},
                        strategy_confidence_hint=0.85
                    )
            
            # Check for success field
            success_value = self._extract_json_path(data, config.success_field)
            if success_value is not None:
                # Extract evidence fields from parser config
                evidence = {}
                for field_name, json_path in definition.parser.fields.items():
                    value = self._extract_json_path(data, json_path)
                    if value is not None:
                        evidence[field_name] = value
                
                return DetectionOutcome(
                    exists=True,
                    http_status=status_code,
                    evidence_fields=evidence,
                    strategy_confidence_hint=0.95
                )
            
            return DetectionOutcome(
                exists="unknown",
                http_status=status_code,
                strategy_confidence_hint=0.4
            )
        
        except Exception as e:
            if logger:
                logger.warning(f"JSON API check failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )
    
    def _extract_json_path(self, data: Any, path: str) -> Any:
        """
        Extract value from JSON using simplified JSONPath.
        
        Supports: $.field, $.nested.field, $.array[0]
        """
        if not path or not path.startswith('$.'):
            return None
        
        parts = path[2:].split('.')
        current = data
        
        for part in parts:
            if not current:
                return None
            
            # Handle array indexing
            if '[' in part and ']' in part:
                field_name = part[:part.index('[')]
                index_str = part[part.index('[') + 1:part.index(']')]
                
                if field_name:
                    if isinstance(current, dict):
                        current = current.get(field_name)
                    else:
                        return None
                
                try:
                    index = int(index_str)
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                except (ValueError, TypeError):
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
        
        return current


@register_strategy('graphql')
class GraphQLStrategy(DetectionStrategy):
    """
    Detection via GraphQL API.
    
    Executes GraphQL query and checks for expected fields in response.
    """
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via GraphQL API."""
        url = self._build_url(username, definition, use_api=True)
        headers = self._get_headers(definition)
        timeout = self._get_timeout(definition)
        
        # Add JSON content type
        headers['Content-Type'] = 'application/json'
        
        config = definition.detection.graphql
        if not config:
            raise ValueError("graphql configuration missing")
        
        # Build GraphQL query
        query = config.query.format(username=username)
        variables = dict(config.variables)
        variables['username'] = username
        
        payload = {
            'query': query,
            'variables': variables
        }
        
        try:
            response = await http_client.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            status_code = response.status_code
            
            try:
                data = response.json()
            except Exception:
                return DetectionOutcome(
                    exists="unknown",
                    http_status=status_code,
                    strategy_confidence_hint=0.2
                )
            
            # Check for GraphQL errors
            if 'errors' in data:
                return DetectionOutcome(
                    exists=False,
                    http_status=status_code,
                    evidence_fields={"errors": data['errors']},
                    strategy_confidence_hint=0.85
                )
            
            # Check for success field in data
            if 'data' in data:
                success_value = self._extract_json_path(data['data'], config.success_field)
                if success_value is not None:
                    # Extract evidence fields
                    evidence = {}
                    for field_name, json_path in definition.parser.fields.items():
                        value = self._extract_json_path(data['data'], json_path)
                        if value is not None:
                            evidence[field_name] = value
                    
                    return DetectionOutcome(
                        exists=True,
                        http_status=status_code,
                        evidence_fields=evidence,
                        strategy_confidence_hint=0.92
                    )
            
            return DetectionOutcome(
                exists="unknown",
                http_status=status_code,
                strategy_confidence_hint=0.4
            )
        
        except Exception as e:
            if logger:
                logger.warning(f"GraphQL check failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )
    
    def _extract_json_path(self, data: Any, path: str) -> Any:
        """Extract value from nested dict/list structure."""
        if not path or not path.startswith('$.'):
            return None
        
        parts = path[2:].split('.')
        current = data
        
        for part in parts:
            if not current:
                return None
            
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current


@register_strategy('html_parse')
class HtmlParseStrategy(DetectionStrategy):
    """
    Detection via HTML parsing.
    
    Uses CSS selectors to extract elements indicating existence.
    """
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via HTML parsing."""
        url = self._build_url(username, definition)
        headers = self._get_headers(definition)
        timeout = self._get_timeout(definition)
        
        config = definition.detection.html_parse
        if not config:
            raise ValueError("html_parse configuration missing")
        
        try:
            response = await http_client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True
            )
            
            status_code = response.status_code
            html = response.text
            
            # Simple existence check based on selector presence
            # In production, would use BeautifulSoup or lxml
            # For framework: just check if selector appears in HTML
            
            exists = "unknown"
            confidence = 0.5
            
            if config.exists_selector in html:
                exists = True
                confidence = 0.7
            
            if config.not_exists_pattern:
                if config.not_exists_pattern in html:
                    exists = False
                    confidence = 0.75
            
            # Note: In production implementation, would properly parse HTML
            # and extract evidence fields using CSS selectors
            evidence = {}
            
            return DetectionOutcome(
                exists=exists,
                http_status=status_code,
                evidence_fields=evidence,
                strategy_confidence_hint=confidence
            )
        
        except Exception as e:
            if logger:
                logger.warning(f"HTML parse check failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )


@register_strategy('custom')
class CustomLogicStrategy(DetectionStrategy):
    """
    Escape hatch for custom detection logic.
    
    Delegates to a registered handler function for platforms
    with unique verification flows.
    """
    
    def __init__(self):
        super().__init__()
        self._handlers: dict[str, Any] = {}
    
    def register_handler(self, handler_id: str, handler_func: Any) -> None:
        """Register a custom handler function."""
        self._handlers[handler_id] = handler_func
    
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """Check username via custom handler."""
        config = definition.detection.custom
        if not config:
            raise ValueError("custom configuration missing")
        
        handler_id = config.handler_id
        handler = self._handlers.get(handler_id)
        
        if not handler:
            raise ValueError(f"Custom handler '{handler_id}' not registered")
        
        try:
            # Call custom handler
            outcome = await handler(
                username=username,
                definition=definition,
                http_client=http_client,
                config=config.config,
                logger=logger
            )
            
            if not isinstance(outcome, DetectionOutcome):
                raise ValueError(f"Custom handler must return DetectionOutcome")
            
            return outcome
        
        except Exception as e:
            if logger:
                logger.error(f"Custom handler '{handler_id}' failed for {username}: {e}")
            
            return DetectionOutcome(
                exists="unknown",
                strategy_confidence_hint=0.0
            )

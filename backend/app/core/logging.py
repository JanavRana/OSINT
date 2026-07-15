import logging
import sys
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("osint-aggregator")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", "N/A")
        
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path
            }
        )
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration
                }
            )
            
            return response
        except Exception as exc:
            duration = time.time() - start_time
            
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(exc)} - {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "duration": duration
                },
                exc_info=True
            )
            
            raise


def log_connector_failure(connector_name: str, error: str):
    logger.error(
        f"Connector failure: {connector_name}",
        extra={
            "connector": connector_name,
            "error": error
        }
    )


def log_unexpected_exception(context: str, error: Exception):
    logger.error(
        f"Unexpected exception in {context}: {str(error)}",
        extra={
            "context": context,
            "error": str(error)
        },
        exc_info=True
    )

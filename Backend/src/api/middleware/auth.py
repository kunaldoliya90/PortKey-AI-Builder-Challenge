"""API authentication middleware."""

import os
from typing import Optional

from fastapi import Header, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog import get_logger

from src.config.settings import get_settings

logger = get_logger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""

    def __init__(self, app, api_keys: Optional[list[str]] = None):
        """
        Initialize authentication middleware.

        Args:
            app: ASGI application
            api_keys: Optional list of valid API keys. If None, loads from config/env.
        """
        super().__init__(app)
        self.api_keys = api_keys or self._load_api_keys()

    def _load_api_keys(self) -> list[str]:
        """Load API keys from config or environment."""
        # Try environment variable first
        api_key = os.getenv("API_KEY")
        if api_key:
            return [api_key]

        # Try config (if available)
        try:
            settings = get_settings()
            # API keys could be stored in config, but for now use env var
            # This can be extended to support multiple keys
            return []
        except Exception:
            return []

    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate API key.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response

        Raises:
            HTTPException: If API key is invalid
        """
        # Skip authentication for health checks and docs
        if request.url.path in ["/health", "/health/ready", "/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")

        # Handle Bearer token format
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]

        # Validate API key
        if not api_key:
            logger.warning("API key missing", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "API key required", "code": "MISSING_API_KEY"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if self.api_keys and api_key not in self.api_keys:
            logger.warning("Invalid API key", path=request.url.path, api_key_prefix=api_key[:8] + "...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid API key", "code": "INVALID_API_KEY"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Add API key to request state for logging
        request.state.api_key = api_key[:8] + "..." if len(api_key) > 8 else api_key

        logger.debug("API key validated", path=request.url.path)

        return await call_next(request)


def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Dependency to extract API key from headers.

    Args:
        x_api_key: X-API-Key header
        authorization: Authorization header (Bearer token)

    Returns:
        API key string

    Raises:
        HTTPException: If API key is missing
    """
    api_key = x_api_key

    if not api_key and authorization:
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "API key required"},
        )

    return api_key


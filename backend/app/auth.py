"""API Key authentication dependency for FastAPI.

When OPENSDLC_API_KEY is set, all protected endpoints require
the key in the X-API-Key header. When empty (dev mode), auth is disabled.
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_api_key

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """FastAPI dependency: validate API key if authentication is enabled."""
    configured_key = get_api_key()
    if not configured_key:
        # Auth disabled — dev mode
        return None
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if not secrets.compare_digest(api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key

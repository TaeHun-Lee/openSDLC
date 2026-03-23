"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import LLM_PROVIDER, MODEL
from app.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_provider=LLM_PROVIDER,
        model=MODEL,
    )

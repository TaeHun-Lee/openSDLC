"""Agent registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.registry.agent_registry import load_all_agents
from app.models.responses import AgentInfo

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentInfo])
async def list_agents_endpoint() -> list[AgentInfo]:
    """List all registered agents."""
    agents = load_all_agents()
    return [
        AgentInfo(
            agent_id=config.agent_id,
            display_name=config.display_name,
            role=config.role,
            primary_inputs=config.primary_inputs,
            primary_outputs=config.primary_outputs,
        )
        for config in agents.values()
    ]


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent_endpoint(agent_id: str) -> AgentInfo:
    """Get a single agent's configuration."""
    agents = load_all_agents()
    config = agents.get(agent_id)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found. Available: {list(agents.keys())}",
        )
    return AgentInfo(
        agent_id=config.agent_id,
        display_name=config.display_name,
        role=config.role,
        primary_inputs=config.primary_inputs,
        primary_outputs=config.primary_outputs,
    )

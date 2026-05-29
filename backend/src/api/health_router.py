"""健康检查路由"""

from fastapi import APIRouter, Request
from src.models.schemas import APIResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request) -> APIResponse:
    """健康检查"""
    agent_service = getattr(request.app.state, "agent_service", None)
    connection_manager = getattr(agent_service, "connection_manager", None)

    return APIResponse(
        code=0,
        message="Health check passed",
        data={
            "status": "healthy",
            "task_store": getattr(agent_service, "task_store_backend", "unknown"),
            "online_agents": len(connection_manager.get_online_agents()) if connection_manager else 0,
        },
    )


@router.get("/")
async def root() -> APIResponse:
    """根端点"""
    return APIResponse(
        code=0,
        message="Welcome to YXS Agent Tool API",
        data={"version": "0.1.0"}
    )

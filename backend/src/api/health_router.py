"""健康检查路由"""

from fastapi import APIRouter
from src.models.schemas import APIResponse

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check() -> APIResponse:
    """健康检查"""
    return APIResponse(
        code=0,
        message="Health check passed",
        data={"status": "healthy"}
    )

@router.get("/")
async def root() -> APIResponse:
    """根端点"""
    return APIResponse(
        code=0,
        message="Welcome to YXS Agent Tool API",
        data={"version": "0.1.0"}
    )

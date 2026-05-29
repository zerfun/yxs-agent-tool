"""Agent API路由"""

from fastapi import APIRouter, Depends, Request

from src.models.schemas import APIResponse, MessageSource, TaskRequest
from src.services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["Agent"])


def get_agent_service(request: Request) -> AgentService:
    """获取Agent服务"""
    return request.app.state.agent_service


@router.post("/task")
async def create_task(
    request: TaskRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse:
    """创建任务"""

    # 这里user_id应该从认证令牌中获取，现在使用默认值
    user_id = "default_user"
    source = MessageSource.API

    result = await agent_service.process_task(request, user_id, source)

    return APIResponse(
        code=0,
        message="Task created successfully",
        data=result.model_dump(),
    )


@router.get("/task/{task_id}")
async def get_task(
    task_id: str,
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse:
    """获取任务状态"""

    result = agent_service.get_task(task_id)

    if not result:
        return APIResponse(
            code=1,
            message="Task not found",
            data=None,
        )

    return APIResponse(
        code=0,
        message="Task retrieved successfully",
        data=result.model_dump(),
    )

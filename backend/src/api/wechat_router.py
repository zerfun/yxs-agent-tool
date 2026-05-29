"""微信 API 路由。"""

import logging

from fastapi import APIRouter, Depends, Query, Request, Response

from src.api.exceptions import BadRequestException, ServerException
from src.config.settings import settings
from src.models.schemas import AIModel, MessageSource, TaskRequest
from src.services.agent_service import AgentService
from src.services.wechat_service import WeChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wechat", tags=["WeChat"])


def get_wechat_service(request: Request) -> WeChatService:
    """获取微信服务。"""
    return request.app.state.wechat_service


def get_agent_service(request: Request) -> AgentService:
    """获取 Agent 服务。"""
    return request.app.state.agent_service


@router.get("/callback")
async def verify_wechat(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
    wechat_service: WeChatService = Depends(get_wechat_service),
):
    """微信服务器验证。"""
    if wechat_service.verify_signature(signature, timestamp, nonce):
        return echostr
    raise BadRequestException("Invalid signature")


@router.post("/callback")
async def handle_wechat_message(
    request: Request,
    wechat_service: WeChatService = Depends(get_wechat_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    """处理微信消息。"""
    try:
        data = (await request.body()).decode("utf-8")
        message = wechat_service.parse_message(data)
        if not message:
            raise BadRequestException("Invalid message format")

        if message["msg_type"] != "text":
            return _xml_reply(
                wechat_service,
                message["from_user"],
                message["to_user"],
                "暂只支持文本消息，请输入您的需求。",
            )

        command = wechat_service.parse_text_command(message["content"])
        if command is not None:
            response_content = await _handle_command(
                command=command,
                user_id=message["from_user"],
                agent_service=agent_service,
                wechat_service=wechat_service,
            )
            return _xml_reply(
                wechat_service,
                message["from_user"],
                message["to_user"],
                response_content,
            )

        task_request = TaskRequest(
            prompt=message["content"],
            model=AIModel.CODEX,
            temperature=0.5,
            max_tokens=2048,
        )
        task_result = await agent_service.process_task(
            task_request,
            user_id=message["from_user"],
            source=MessageSource.WECHAT,
        )

        logger.info("WeChat message processed successfully")
        return _xml_reply(
            wechat_service,
            message["from_user"],
            message["to_user"],
            wechat_service.build_submission_message(task_result),
        )
    except Exception as exc:
        logger.error("Error handling WeChat message: %s", exc)
        raise ServerException("Failed to process message")


async def _handle_command(
    command: dict[str, str],
    user_id: str,
    agent_service: AgentService,
    wechat_service: WeChatService,
) -> str:
    """处理微信文本命令。"""
    if command["type"] == "help":
        return wechat_service.build_help_message()

    if command["type"] == "recent_tasks":
        tasks = await agent_service.list_tasks(
            limit=settings.WECHAT_COMMAND_TASK_LIMIT,
            user_id=user_id,
        )
        return wechat_service.build_task_list_message(tasks)

    if command["type"] == "task_status":
        task_id = command["task_id"]
        task = await agent_service.get_task(task_id)
        if task is None:
            return f"未找到任务：{task_id}\n发送“最近任务”可查看近期记录。"

        if task.user_id and task.user_id != user_id:
            return "这个任务不属于当前微信用户，无法查看。"

        return wechat_service.build_task_status_message(task)

    return wechat_service.build_help_message()


def _xml_reply(
    wechat_service: WeChatService,
    from_user: str,
    to_user: str,
    content: str,
) -> Response:
    """返回微信 XML 文本消息。"""
    return Response(
        content=wechat_service.create_response(from_user, to_user, content),
        media_type="application/xml",
    )

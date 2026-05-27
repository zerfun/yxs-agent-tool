"""微信API路由"""

from fastapi import APIRouter, Request, Query, Depends
import logging

from src.models.schemas import APIResponse, MessageSource, TaskRequest, AIModel
from src.services.wechat_service import WeChatService
from src.services.agent_service import AgentService
from src.api.exceptions import BadRequestException, ServerException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wechat", tags=["WeChat"])

def get_wechat_service(request: Request) -> WeChatService:
    """获取微信服务"""
    return request.app.state.wechat_service

def get_agent_service(request: Request) -> AgentService:
    """获取Agent服务"""
    return request.app.state.agent_service

@router.get("/callback")
async def verify_wechat(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
    wechat_service: WeChatService = Depends(get_wechat_service)
):
    """微信服务器验证 (GET请求)"""
    
    if wechat_service.verify_signature(signature, timestamp, nonce):
        return echostr
    else:
        raise BadRequestException("Invalid signature")

@router.post("/callback")
async def handle_wechat_message(
    request: Request,
    wechat_service: WeChatService = Depends(get_wechat_service),
    agent_service: AgentService = Depends(get_agent_service)
):
    """处理微信消息 (POST请求)"""
    
    try:
        # 获取消息体
        data = await request.body()
        data = data.decode('utf-8')
        
        # 解析消息
        message = wechat_service.parse_message(data)
        
        if not message:
            raise BadRequestException("Invalid message format")
        
        # 检查消息类型
        if message['msg_type'] != 'text':
            # 对于非文本消息，返回提示
            response_xml = wechat_service.create_response(
                message['from_user'],
                message['to_user'],
                "暂只支持文本消息，请输入您的需求。"
            )
            return response_xml
        
        # 创建任务
        task_request = TaskRequest(
            prompt=message['content'],
            model=AIModel.CODEX,
            temperature=0.5,
            max_tokens=2048
        )
        
        task_result = await agent_service.process_task(
            task_request,
            user_id=message['from_user'],
            source=MessageSource.WECHAT
        )
        
        # 创建响应
        response_content = task_result.result or f"错误: {task_result.error}"
        response_xml = wechat_service.create_response(
            message['from_user'],
            message['to_user'],
            response_content
        )
        
        logger.info(f"WeChat message processed successfully")
        return response_xml
        
    except Exception as e:
        logger.error(f"Error handling WeChat message: {e}")
        raise ServerException("Failed to process message")

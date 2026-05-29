"""Agent WebSocket API路由 - 连接本地Agent守护进程"""

import datetime
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.config.settings import settings
from src.daemon.connection_manager import AgentWebSocketHandler, agent_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent WebSocket"])

# WebSocket处理器
ws_handler = AgentWebSocketHandler(agent_manager)


@router.websocket("/ws")
async def websocket_agent(websocket: WebSocket, agent_id: str = Query(...), api_key: str = Query(...)):
    """
    Agent WebSocket端点
    
    本地Agent守护进程通过此端点连接到云端服务器
    
    Args:
        agent_id: Agent ID（唯一标识）
        api_key: API密钥（用于认证）
    
    使用示例：
    ```
    ws://your-server.com/api/v1/agent/ws?agent_id=my-agent-1&api_key=secret-key
    ```
    """
    
    # 验证API密钥
    if not _verify_api_key(api_key):
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    logger.info(f"🔗 Agent WebSocket connection attempt: {agent_id}")
    
    try:
        # 处理Agent连接
        await ws_handler.handle_connection(websocket, agent_id)
    except WebSocketDisconnect:
        logger.info(f"📴 Agent disconnected: {agent_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")


@router.get("/agents")
async def list_agents():
    """
    获取所有在线Agent列表
    
    Returns:
        在线Agent信息列表
    """
    agents = agent_manager.get_online_agents()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": len(agents),
            "agents": agents
        }
    }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """
    获取指定Agent的信息
    
    Args:
        agent_id: Agent ID
    
    Returns:
        Agent信息
    """
    info = agent_manager.get_agent_info(agent_id)
    
    if not info:
        return {
            "code": 1,
            "message": "Agent not found",
            "data": None
        }
    
    return {
        "code": 0,
        "message": "success",
        "data": info
    }


@router.post("/task/submit")
async def submit_task(task_data: dict):
    """
    提交任务给Agent
    
    Args:
        task_data: 任务数据
            {
                "task_id": "uuid",
                "prompt": "任务提示词",
                "model": "codex",
                "user_id": "user123",
                "source": "wechat"
            }
    
    Returns:
        提交结果
    """
    task_id = task_data.get("task_id")
    model = task_data.get("model", "codex")
    
    # 查找支持该模型的Agent
    agent_id = agent_manager.find_suitable_agent(model)
    
    if not agent_id:
        return {
            "code": 1,
            "message": f"No agent available for model: {model}",
            "data": None
        }
    
    # 发送任务给Agent
    success = await agent_manager.send_task(agent_id, task_data)
    
    if success:
        return {
            "code": 0,
            "message": "Task submitted successfully",
            "data": {
                "task_id": task_id,
                "agent_id": agent_id,
                "status": "queued"
            }
        }
    else:
        return {
            "code": 1,
            "message": "Failed to submit task",
            "data": None
        }


@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果
    
    Args:
        task_id: 任务ID
    
    Returns:
        任务结果
    """
    result = agent_manager.pending_results.get(task_id)
    
    if not result:
        return {
            "code": 1,
            "message": "Task result not found",
            "data": None
        }
    
    return {
        "code": 0,
        "message": "success",
        "data": result
    }


@router.post("/broadcast")
async def broadcast_message(message: dict, agent_ids: list = None):
    """
    广播消息给Agent
    
    Args:
        message: 消息内容
        agent_ids: 目标Agent ID列表（可选，不指定则发给所有Agent）
    
    Returns:
        广播结果
    """
    target_agents = set(agent_ids) if agent_ids else None
    await agent_manager.broadcast_to_agents(message, target_agents)
    
    return {
        "code": 0,
        "message": "Message broadcasted successfully",
        "data": None
    }


@router.post("/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, config: dict):
    """
    更新Agent配置
    
    Args:
        agent_id: Agent ID
        config: 配置信息
    
    Returns:
        更新结果
    """
    info = agent_manager.get_agent_info(agent_id)
    
    if not info:
        return {
            "code": 1,
            "message": "Agent not found",
            "data": None
        }
    
    # 发送配置更新给Agent
    config_msg = {
        "type": "config",
        "config": config,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    success = await agent_manager.send_task(agent_id, config_msg)
    
    if success:
        return {
            "code": 0,
            "message": "Configuration updated successfully",
            "data": None
        }
    else:
        return {
            "code": 1,
            "message": "Failed to update configuration",
            "data": None
        }


def _verify_api_key(api_key: str) -> bool:
    """
    验证API密钥
    
    Args:
        api_key: 提供的API密钥
    
    Returns:
        是否验证通过
    """
    return api_key in settings.agent_api_keys

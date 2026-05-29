"""WebSocket服务 - 管理本地Agent守护进程的连接"""

import logging
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)

class AgentConnectionManager:
    """
    Agent连接管理器
    
    管理所有连接的本地Agent守护进程
    维护Agent状态和任务队列
    """
    
    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_info: Dict[str, Dict[str, Any]] = {}
        self.task_queue: Dict[str, list] = {}  # agent_id -> [tasks]
        self.pending_results: Dict[str, Dict[str, Any]] = {}  # task_id -> result
        logger.info("AgentConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, agent_id: str):
        """
        连接Agent
        
        Args:
            websocket: WebSocket连接
            agent_id: Agent ID
        """
        await websocket.accept()
        self.active_connections[agent_id] = websocket
        logger.info(f"✅ Agent connected: {agent_id}")
    
    def disconnect(self, agent_id: str):
        """
        断开Agent连接
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]
        if agent_id in self.agent_info:
            del self.agent_info[agent_id]
        logger.info(f"❌ Agent disconnected: {agent_id}")
    
    async def register_agent(self, agent_id: str, agent_data: Dict[str, Any]):
        """
        注册Agent信息
        
        Args:
            agent_id: Agent ID
            agent_data: Agent信息（名称、支持的模型等）
        """
        self.agent_info[agent_id] = {
            **agent_data,
            "registered_at": datetime.now().isoformat(),
            "status": "online"
        }
        self.task_queue[agent_id] = []
        logger.info(f"📝 Agent registered: {agent_data.get('agent_name', agent_id)}")
    
    async def send_task(self, agent_id: str, task: Dict[str, Any]) -> bool:
        """
        发送任务给Agent
        
        Args:
            agent_id: Agent ID
            task: 任务数据
        
        Returns:
            是否发送成功
        """
        if agent_id not in self.active_connections:
            logger.warning(f"Agent {agent_id} is offline")
            return False
        
        try:
            ws = self.active_connections[agent_id]
            await ws.send_json(task)
            logger.info(f"📤 Task sent to {agent_id}: {task.get('task_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send task to {agent_id}: {e}")
            return False
    
    async def broadcast_to_agents(self, message: Dict[str, Any], agent_ids: Optional[Set[str]] = None):
        """
        广播消息给多个Agent
        
        Args:
            message: 消息内容
            agent_ids: 目标Agent ID集合（如果为None则发给所有Agent）
        """
        targets = agent_ids or set(self.active_connections.keys())
        
        for agent_id in targets:
            if agent_id in self.active_connections:
                try:
                    await self.active_connections[agent_id].send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to {agent_id}: {e}")
    
    async def send_heartbeat(self):
        """发送心跳检测给所有Agent"""
        heartbeat = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_agents(heartbeat)
    
    def get_online_agents(self) -> list:
        """
        获取在线的Agent列表
        
        Returns:
            在线Agent信息列表
        """
        agents = []
        for agent_id, info in self.agent_info.items():
            if agent_id in self.active_connections:
                agents.append({
                    "agent_id": agent_id,
                    **info
                })
        return agents
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的信息
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Agent信息或None
        """
        return self.agent_info.get(agent_id)
    
    def find_suitable_agent(self, model: str) -> Optional[str]:
        """
        查找支持指定模型的Agent
        
        Args:
            model: 模型名称
        
        Returns:
            Agent ID或None
        """
        for agent_id, info in self.agent_info.items():
            if agent_id in self.active_connections:
                supported_models = info.get("supported_models", [])
                if model in supported_models:
                    return agent_id
        return None
    
    async def handle_agent_message(self, agent_id: str, message: Dict[str, Any]):
        """
        处理来自Agent的消息
        
        Args:
            agent_id: Agent ID
            message: 消息内容
        """
        msg_type = message.get("type")
        
        if msg_type == "register":
            # Agent注册
            await self.register_agent(agent_id, message)
        
        elif msg_type == "status_update":
            # 任务状态更新
            task_id = message.get("task_id")
            status = message.get("status")
            logger.info(f"📊 Task {task_id} status: {status}")
        
        elif msg_type == "task_result":
            # 任务结果
            task_id = message.get("task_id")
            result = message.get("result")
            user_id = message.get("user_id")
            source = message.get("source")
            
            # 保存结果
            self.pending_results[task_id] = message
            
            # 推送结果给用户
            await self._push_result_to_user(user_id, source, task_id, result)
            
            logger.info(f"✅ Result received for task {task_id}")
        
        elif msg_type == "heartbeat_response":
            # 心跳响应
            pass
    
    async def _push_result_to_user(self, user_id: str, source: str, task_id: str, result: str):
        """
        推送结果给用户
        
        Args:
            user_id: 用户ID
            source: 来源平台 (wechat, feishu, qq)
            task_id: 任务ID
            result: 结果内容
        """
        if source == "wechat":
            await self._push_to_wechat(user_id, result)
        elif source == "feishu":
            await self._push_to_feishu(user_id, result)
        elif source == "qq":
            await self._push_to_qq(user_id, result)
    
    async def _push_to_wechat(self, user_id: str, result: str):
        """推送结果到微信"""
        # TODO: 实现微信推送
        logger.info(f"📱 Pushing to WeChat user {user_id}")
    
    async def _push_to_feishu(self, user_id: str, result: str):
        """推送结果到飞书"""
        # TODO: 实现飞书推送
        logger.info(f"📱 Pushing to Feishu user {user_id}")
    
    async def _push_to_qq(self, user_id: str, result: str):
        """推送结果到QQ"""
        # TODO: 实现QQ推送
        logger.info(f"📱 Pushing to QQ user {user_id}")


class AgentWebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self, manager: AgentConnectionManager):
        """
        初始化WebSocket处理器
        
        Args:
            manager: 连接管理器
        """
        self.manager = manager
    
    async def handle_connection(self, websocket: WebSocket, agent_id: str):
        """
        处理Agent连接
        
        Args:
            websocket: WebSocket连接
            agent_id: Agent ID
        """
        await self.manager.connect(websocket, agent_id)
        
        try:
            while True:
                # 接收来自Agent的消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理消息
                await self.manager.handle_agent_message(agent_id, message)
        
        except WebSocketDisconnect:
            self.manager.disconnect(agent_id)
        except Exception as e:
            logger.error(f"WebSocket error for {agent_id}: {e}")
            self.manager.disconnect(agent_id)


# 全局连接管理器实例
agent_manager = AgentConnectionManager()


async def start_heartbeat_task():
    """
    启动心跳检测任务
    
    每30秒发送一次心跳给所有在线Agent
    """
    while True:
        try:
            await agent_manager.send_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(30)

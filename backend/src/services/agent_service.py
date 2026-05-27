"""Agent服务 - 核心业务逻辑"""

import logging
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from src.config.settings import settings
from src.models.schemas import Task, TaskRequest, TaskResponse, AgentStatus, MessageSource, AIModel

logger = logging.getLogger(__name__)

class AgentService:
    """Agent服务"""
    
    def __init__(self):
        """初始化Agent服务"""
        self.tasks: Dict[str, Task] = {}  # 临时存储，实际应用应使用数据库
        logger.info("AgentService initialized")
    
    async def process_task(self, request: TaskRequest, user_id: str, source: MessageSource) -> TaskResponse:
        """处理任务"""
        
        task_id = str(uuid.uuid4())
        
        try:
            # 创建任务
            task = Task(
                id=task_id,
                user_id=user_id,
                prompt=request.prompt,
                model=request.model,
                status=AgentStatus.RUNNING,
                source=source,
                metadata={"temperature": request.temperature, "max_tokens": request.max_tokens}
            )
            
            # 保存任务
            self.tasks[task_id] = task
            
            # 根据模型调用相应的API
            if request.model == AIModel.CODEX:
                result = await self._call_codex(request.prompt, request.temperature, request.max_tokens)
            elif request.model == AIModel.CLAUDE:
                result = await self._call_claude(request.prompt, request.temperature, request.max_tokens)
            elif request.model == AIModel.QWEN:
                result = await self._call_qwen(request.prompt, request.temperature, request.max_tokens)
            else:
                raise ValueError(f"Unsupported model: {request.model}")
            
            # 更新任务状态
            task.status = AgentStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            
            logger.info(f"Task {task_id} completed successfully")
            
            return TaskResponse(
                task_id=task_id,
                status=task.status,
                result=result,
                created_at=task.created_at,
                completed_at=task.completed_at
            )
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            
            # 更新任务状态为失败
            if task_id in self.tasks:
                self.tasks[task_id].status = AgentStatus.FAILED
                self.tasks[task_id].error = str(e)
                self.tasks[task_id].completed_at = datetime.now()
            
            return TaskResponse(
                task_id=task_id,
                status=AgentStatus.FAILED,
                error=str(e),
                created_at=datetime.now(),
                completed_at=datetime.now()
            )
    
    async def _call_codex(self, prompt: str, temperature: float = 0.5, max_tokens: int = 2048) -> str:
        """调用GitHub Codex API"""
        import aiohttp
        
        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        
        # 这是一个示例实现，实际应该使用GitHub的Copilot或Codex API
        # 当前GitHub Codex主要通过GitHub Copilot或编辑器集成提供
        
        logger.warning("Codex API integration pending - requires proper GitHub API credentials")
        
        # 返回模拟响应
        return f"# Codex Response\n\nPrompt: {prompt}\n\nNote: Actual Codex integration pending GitHub API setup."
    
    async def _call_claude(self, prompt: str, temperature: float = 0.5, max_tokens: int = 2048) -> str:
        """调用Claude API"""
        logger.warning("Claude API integration pending")
        return f"# Claude Response\n\nPrompt: {prompt}"
    
    async def _call_qwen(self, prompt: str, temperature: float = 0.5, max_tokens: int = 2048) -> str:
        """调用Qwen API"""
        logger.warning("Qwen API integration pending")
        return f"# Qwen Response\n\nPrompt: {prompt}"
    
    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """获取任务状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            return TaskResponse(
                task_id=task.id,
                status=task.status,
                result=task.result,
                error=task.error,
                created_at=task.created_at,
                completed_at=task.completed_at
            )
        return None

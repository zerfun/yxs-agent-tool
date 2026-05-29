"""Agent服务 - 核心业务逻辑"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from src.models.schemas import AIModel, AgentStatus, MessageSource, Task, TaskRequest, TaskResponse
from src.repositories.task_store import BaseTaskStore, InMemoryTaskStore
from src.services.codex_service import CodexService

logger = logging.getLogger(__name__)


class AgentService:
    """Agent服务"""

    def __init__(
        self,
        connection_manager: Optional[Any] = None,
        task_store: Optional[BaseTaskStore] = None,
    ):
        """初始化Agent服务"""
        self.codex_service = CodexService()
        self.connection_manager = connection_manager
        self.task_store = task_store or InMemoryTaskStore()
        logger.info("AgentService initialized")

    async def process_task(self, request: TaskRequest, user_id: str, source: MessageSource) -> TaskResponse:
        """处理任务"""
        task_id = str(uuid.uuid4())
        created_at = datetime.now()

        try:
            # 创建任务
            task = Task(
                id=task_id,
                user_id=user_id,
                prompt=request.prompt,
                model=request.model,
                status=AgentStatus.QUEUED,
                source=source,
                created_at=created_at,
                metadata={
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "context": request.context or {},
                },
            )

            # 保存任务
            await self.task_store.save(task)

            agent_id = await self._dispatch_to_remote_agent(task, request)
            if agent_id:
                task.metadata["execution_mode"] = "remote"
                task.metadata["agent_id"] = agent_id
                await self.task_store.save(task)
                logger.info("Task %s queued for remote agent %s", task_id, agent_id)
                return self._build_response(task)

            task.status = AgentStatus.RUNNING
            task.metadata["execution_mode"] = "local"
            await self.task_store.save(task)

            # 根据模型调用相应的API
            if request.model == AIModel.CODEX:
                result = await self._call_codex(
                    request.prompt,
                    request.temperature,
                    request.max_tokens,
                    self._resolve_language(request.context),
                )
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
            await self.task_store.save(task)

            logger.info("Task %s completed successfully", task_id)

            return self._build_response(task)
        except Exception as exc:
            logger.error("Task %s failed: %s", task_id, exc)

            # 更新任务状态为失败
            failed_task = await self.task_store.get(task_id)
            if failed_task is not None:
                failed_task.status = AgentStatus.FAILED
                failed_task.error = str(exc)
                failed_task.completed_at = datetime.now()
                await self.task_store.save(failed_task)

            return TaskResponse(
                task_id=task_id,
                status=AgentStatus.FAILED,
                user_id=user_id,
                model=request.model,
                source=source,
                error=str(exc),
                created_at=created_at,
                completed_at=datetime.now(),
            )

    async def _call_codex(
        self,
        prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 2048,
        language: str = "python",
    ) -> str:
        """调用GitHub Codex API"""
        return await self.codex_service.generate_code(
            prompt,
            language=language,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _call_claude(self, prompt: str, temperature: float = 0.5, max_tokens: int = 2048) -> str:
        """调用Claude API"""
        logger.warning("Claude API integration pending")
        return self._build_placeholder_response("Claude", prompt, temperature, max_tokens)

    async def _call_qwen(self, prompt: str, temperature: float = 0.5, max_tokens: int = 2048) -> str:
        """调用Qwen API"""
        logger.warning("Qwen API integration pending")
        return self._build_placeholder_response("Qwen", prompt, temperature, max_tokens)

    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """获取任务状态"""
        task = await self.task_store.get(task_id)
        return self._build_response(task) if task else None

    async def list_tasks(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> list[TaskResponse]:
        """列出最近任务。"""
        tasks = await self.task_store.list(limit=limit, user_id=user_id, status=status)
        return [self._build_response(task) for task in tasks]

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        message: str = "",
        agent_id: Optional[str] = None,
    ) -> Optional[TaskResponse]:
        """更新远程任务状态。"""
        task = await self.task_store.get(task_id)
        if not task:
            return None

        normalized_status = self._normalize_status(status)
        if normalized_status is not None:
            task.status = normalized_status

        if agent_id:
            task.metadata["agent_id"] = agent_id
        if message:
            task.metadata["last_status_message"] = message
        await self.task_store.save(task)

        return self._build_response(task)

    async def complete_remote_task(
        self,
        task_id: str,
        status: str,
        result: str,
        agent_id: Optional[str] = None,
    ) -> Optional[TaskResponse]:
        """写入远程Agent返回的最终结果。"""
        task = await self.task_store.get(task_id)
        if not task:
            return None

        normalized_status = self._normalize_status(status) or AgentStatus.COMPLETED
        task.status = normalized_status
        task.completed_at = datetime.now()

        if agent_id:
            task.metadata["agent_id"] = agent_id

        if normalized_status == AgentStatus.FAILED:
            task.error = result
            task.result = None
        else:
            task.result = result
            task.error = None
        await self.task_store.save(task)

        return self._build_response(task)

    @property
    def task_store_backend(self) -> str:
        """当前任务存储后端名称。"""
        return self.task_store.backend_name

    async def _dispatch_to_remote_agent(self, task: Task, request: TaskRequest) -> Optional[str]:
        """有在线Agent时优先走远程派发。"""
        if self.connection_manager is None:
            return None

        agent_id = self.connection_manager.find_suitable_agent(task.model.value)
        if not agent_id:
            return None

        task_payload = {
            "type": "task",
            "task_id": task.id,
            "prompt": task.prompt,
            "model": task.model.value,
            "user_id": task.user_id,
            "source": task.source.value,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "context": request.context or {},
            "created_at": task.created_at.isoformat(),
        }

        success = await self.connection_manager.send_task(agent_id, task_payload)
        if not success:
            logger.warning("Dispatch to remote agent %s failed, falling back to local execution", agent_id)
            return None

        return agent_id

    @staticmethod
    def _resolve_language(context: Optional[Dict[str, Any]]) -> str:
        """从上下文中解析目标语言，默认使用 Python。"""
        if not context:
            return "python"

        language = context.get("language")
        return str(language).strip() if language else "python"

    @staticmethod
    def _build_placeholder_response(model_name: str, prompt: str, temperature: float, max_tokens: int) -> str:
        """为尚未接入的模型返回占位响应。"""
        return (
            f"# {model_name} Response\n\n"
            f"Prompt: {prompt}\n\n"
            f"temperature={temperature}, max_tokens={max_tokens}\n\n"
            "Note: This provider is scaffolded but not wired to a live API yet."
        )

    @staticmethod
    def _normalize_status(status: str) -> Optional[AgentStatus]:
        """将字符串状态安全转换为枚举。"""
        try:
            return AgentStatus(status)
        except ValueError:
            logger.warning("Unknown task status received: %s", status)
            return None

    @staticmethod
    def _build_response(task: Task) -> TaskResponse:
        """将任务对象转换为标准响应。"""
        return TaskResponse(
            task_id=task.id,
            status=task.status,
            user_id=task.user_id,
            model=task.model,
            source=task.source,
            result=task.result,
            error=task.error,
            created_at=task.created_at,
            completed_at=task.completed_at,
            metadata=task.metadata,
        )

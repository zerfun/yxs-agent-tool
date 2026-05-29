"""任务存储实现。"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

try:
    from redis.asyncio import Redis, from_url
except ModuleNotFoundError:  # pragma: no cover - optional dependency in some local envs
    Redis = Any  # type: ignore[assignment]
    from_url = None

from src.config.settings import settings
from src.models.schemas import AgentStatus, Task

logger = logging.getLogger(__name__)


class BaseTaskStore(ABC):
    """任务存储抽象。"""

    backend_name = "base"

    @abstractmethod
    async def save(self, task: Task) -> None:
        """保存或更新任务。"""

    @abstractmethod
    async def get(self, task_id: str) -> Optional[Task]:
        """根据 ID 获取任务。"""

    @abstractmethod
    async def list(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> list[Task]:
        """列出任务。"""

    async def ping(self) -> bool:
        """健康探测。"""
        return True

    async def close(self) -> None:
        """关闭资源。"""


class InMemoryTaskStore(BaseTaskStore):
    """内存任务存储。"""

    backend_name = "memory"

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    async def save(self, task: Task) -> None:
        self._tasks[task.id] = task

    async def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    async def list(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> list[Task]:
        tasks = sorted(
            self._tasks.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

        if user_id:
            tasks = [task for task in tasks if task.user_id == user_id]
        if status:
            tasks = [task for task in tasks if task.status == status]

        return tasks[:limit]


class RedisTaskStore(BaseTaskStore):
    """Redis 任务存储。"""

    backend_name = "redis"

    def __init__(self, redis_client: Redis, prefix: str, max_items: int = 1000) -> None:
        self.redis = redis_client
        self.prefix = prefix
        self.max_items = max_items
        self.index_key = f"{self.prefix}:tasks:index"

    async def save(self, task: Task) -> None:
        payload = task.model_dump_json()
        key = self._task_key(task.id)

        await self.redis.set(key, payload)
        await self.redis.zadd(self.index_key, {task.id: task.created_at.timestamp()})
        await self._trim_if_needed()

    async def get(self, task_id: str) -> Optional[Task]:
        payload = await self.redis.get(self._task_key(task_id))
        if payload is None:
            return None

        return Task.model_validate_json(payload)

    async def list(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> list[Task]:
        offset = 0
        batch_size = max(limit * 3, 50)
        tasks: list[Task] = []

        while len(tasks) < limit:
            task_ids = await self.redis.zrevrange(self.index_key, offset, offset + batch_size - 1)
            if not task_ids:
                break

            payloads = await self.redis.mget([self._task_key(task_id) for task_id in task_ids])
            for payload in payloads:
                if payload is None:
                    continue

                task = Task.model_validate_json(payload)
                if user_id and task.user_id != user_id:
                    continue
                if status and task.status != status:
                    continue

                tasks.append(task)
                if len(tasks) >= limit:
                    break

            offset += batch_size

        return tasks[:limit]

    async def ping(self) -> bool:
        return bool(await self.redis.ping())

    async def close(self) -> None:
        await self.redis.aclose()

    def _task_key(self, task_id: str) -> str:
        return f"{self.prefix}:task:{task_id}"

    async def _trim_if_needed(self) -> None:
        total = await self.redis.zcard(self.index_key)
        if total <= self.max_items:
            return

        overflow = total - self.max_items
        stale_ids = await self.redis.zrange(self.index_key, 0, overflow - 1)
        if stale_ids:
            await self.redis.delete(*[self._task_key(task_id) for task_id in stale_ids])
        await self.redis.zremrangebyrank(self.index_key, 0, overflow - 1)


async def create_task_store() -> BaseTaskStore:
    """按配置创建任务存储。"""
    backend = settings.TASK_STORE_BACKEND.strip().lower()
    if backend != "redis":
        return InMemoryTaskStore()

    if from_url is None:
        logger.warning("Redis package is not installed, falling back to memory task store")
        return InMemoryTaskStore()

    redis_client = from_url(settings.REDIS_URL, decode_responses=True)
    store = RedisTaskStore(
        redis_client=redis_client,
        prefix=settings.TASK_STORE_PREFIX,
        max_items=settings.TASK_STORE_MAX_ITEMS,
    )

    try:
        await store.ping()
        logger.info("Using Redis task store: %s", settings.REDIS_URL)
        return store
    except Exception as exc:
        logger.warning("Redis task store unavailable, falling back to memory store: %s", exc)
        await store.close()
        return InMemoryTaskStore()

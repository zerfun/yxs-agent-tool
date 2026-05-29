"""AgentService测试。"""

import pytest

from src.models.schemas import AIModel, AgentStatus, MessageSource, TaskRequest
from src.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_process_task_returns_demo_code_when_github_token_missing(monkeypatch):
    """未配置 GitHub Token 时，Codex 任务应该回退到演示代码。"""
    service = AgentService()
    monkeypatch.setattr(service.codex_service, "github_token", "")

    response = await service.process_task(
        TaskRequest(
            prompt="写一个快速排序函数",
            model=AIModel.CODEX,
            context={"language": "python"},
        ),
        user_id="demo-user",
        source=MessageSource.API,
    )

    assert response.status == AgentStatus.COMPLETED
    assert response.result is not None
    assert "quicksort" in response.result.lower()

    stored_task = service.get_task(response.task_id)
    assert stored_task is not None
    assert stored_task.status == AgentStatus.COMPLETED


class FakeConnectionManager:
    """测试用连接管理器。"""

    def __init__(self):
        self.sent_tasks = []

    def find_suitable_agent(self, model: str):
        if model == "codex":
            return "agent-1"
        return None

    async def send_task(self, agent_id: str, task: dict) -> bool:
        self.sent_tasks.append((agent_id, task))
        return True


@pytest.mark.asyncio
async def test_process_task_queues_remote_agent_when_available():
    """有在线Agent时，任务应优先进入远程队列。"""
    manager = FakeConnectionManager()
    service = AgentService(connection_manager=manager)

    response = await service.process_task(
        TaskRequest(prompt="远程生成代码", model=AIModel.CODEX),
        user_id="remote-user",
        source=MessageSource.API,
    )

    assert response.status == AgentStatus.QUEUED
    assert len(manager.sent_tasks) == 1
    agent_id, payload = manager.sent_tasks[0]
    assert agent_id == "agent-1"
    assert payload["task_id"] == response.task_id
    assert payload["type"] == "task"


def test_complete_remote_task_updates_stored_result():
    """远程Agent返回结果后，任务状态应被更新。"""
    manager = FakeConnectionManager()
    service = AgentService(connection_manager=manager)

    task_id = "task-1"
    service.tasks[task_id] = service.tasks.get(task_id) or __import__("src.models.schemas", fromlist=["Task"]).Task(
        id=task_id,
        user_id="remote-user",
        prompt="hello",
        model=AIModel.CODEX,
        status=AgentStatus.QUEUED,
        source=MessageSource.API,
    )

    response = service.complete_remote_task(task_id, "completed", "done", agent_id="agent-1")

    assert response is not None
    assert response.status == AgentStatus.COMPLETED
    assert response.result == "done"

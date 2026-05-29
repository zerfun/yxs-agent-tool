"""FastAPI应用测试。"""

from fastapi.testclient import TestClient

from main import app


def test_health_endpoint():
    """健康检查接口应该返回 healthy。"""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "healthy"


def test_create_task_endpoint():
    """创建任务接口应该返回已完成任务。"""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/task",
            json={
                "prompt": "生成一个快速排序函数",
                "model": "codex",
                "context": {"language": "python"},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "completed"
    assert "task_id" in payload["data"]


def test_create_task_endpoint_can_return_queued_when_remote_agent_available():
    """在线远程Agent可用时，任务创建接口应返回 queued。"""
    with TestClient(app) as client:
        agent_service = client.app.state.agent_service
        original_manager = agent_service.connection_manager

        class StubManager:
            def find_suitable_agent(self, model: str):
                return "agent-remote" if model == "codex" else None

            async def send_task(self, agent_id: str, task: dict) -> bool:
                return True

        agent_service.connection_manager = StubManager()

        try:
            response = client.post(
                "/api/v1/agent/task",
                json={
                    "prompt": "交给远程Agent",
                    "model": "codex",
                },
            )
        finally:
            agent_service.connection_manager = original_manager

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "queued"

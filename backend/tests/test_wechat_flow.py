"""微信消息流测试。"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from main import app
from src.daemon.connection_manager import AgentConnectionManager
from src.models.schemas import AgentStatus, MessageSource, TaskResponse


def _build_wechat_text_xml(content: str) -> str:
    return f"""<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[user_openid]]></FromUserName>
<CreateTime>123456789</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
<MsgId>1234567890123456</MsgId>
</xml>"""


def test_wechat_callback_returns_queue_ack_when_remote_agent_available():
    """远程 Agent 可用时，微信应先收到排队确认。"""
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
                "/api/v1/wechat/callback",
                content=_build_wechat_text_xml("帮我写一个函数"),
                headers={"Content-Type": "application/xml"},
            )
        finally:
            agent_service.connection_manager = original_manager

    assert response.status_code == 200
    assert "任务已接收" in response.text
    assert "处理完成后会主动推送结果" in response.text


def test_wechat_callback_can_query_task_status():
    """微信命令应能查询任务状态。"""
    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/wechat/callback",
            content=_build_wechat_text_xml("生成一个快速排序函数"),
            headers={"Content-Type": "application/xml"},
        )

        import re

        match = re.search(r"任务ID:\s*([A-Za-z0-9-]+)", create_response.text)
        assert match is not None
        task_id = match.group(1)

        response = client.post(
            "/api/v1/wechat/callback",
            content=_build_wechat_text_xml(f"状态 {task_id}"),
            headers={"Content-Type": "application/xml"},
        )

    assert response.status_code == 200
    assert task_id in response.text
    assert "已完成" in response.text


def test_wechat_callback_can_list_recent_tasks():
    """微信命令应能列出最近任务。"""
    with TestClient(app) as client:
        client.post(
            "/api/v1/wechat/callback",
            content=_build_wechat_text_xml("任务一"),
            headers={"Content-Type": "application/xml"},
        )
        client.post(
            "/api/v1/wechat/callback",
            content=_build_wechat_text_xml("任务二"),
            headers={"Content-Type": "application/xml"},
        )

        response = client.post(
            "/api/v1/wechat/callback",
            content=_build_wechat_text_xml("最近任务"),
            headers={"Content-Type": "application/xml"},
        )

    assert response.status_code == 200
    assert "最近任务" in response.text
    assert "发送“状态 <任务ID>”可查看详情" in response.text


class FakeTaskService:
    async def get_task(self, task_id: str):
        return TaskResponse(
            task_id=task_id,
            status=AgentStatus.COMPLETED,
            user_id="user_openid",
            model=None,
            source=MessageSource.WECHAT,
            result="done",
            error=None,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            metadata={"execution_mode": "remote", "agent_id": "agent-1"},
        )

    async def update_task_status(self, *args, **kwargs):
        return None

    async def complete_remote_task(self, *args, **kwargs):
        return None


class FakeWeChatService:
    def __init__(self):
        self.calls = []

    async def push_task_result(self, to_user: str, task_id: str, status: str, result: str, task=None):
        self.calls.append((to_user, task_id, status, result, task))
        return True


@pytest.mark.asyncio
async def test_connection_manager_pushes_remote_result_to_wechat():
    """远程结果回传时，应触发微信主动推送。"""
    manager = AgentConnectionManager()
    manager.bind_task_service(FakeTaskService())
    fake_wechat = FakeWeChatService()
    manager.bind_wechat_service(fake_wechat)

    await manager.handle_agent_message(
        "agent-1",
        {
            "type": "task_result",
            "task_id": "task-123",
            "user_id": "user_openid",
            "source": "wechat",
            "status": "completed",
            "result": "done",
        },
    )

    assert len(fake_wechat.calls) == 1
    to_user, task_id, status, result, task = fake_wechat.calls[0]
    assert to_user == "user_openid"
    assert task_id == "task-123"
    assert status == "completed"
    assert result == "done"
    assert task is not None

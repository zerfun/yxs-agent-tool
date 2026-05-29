"""本地Agent守护进程 - 在用户电脑上运行，接收和执行任务。"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
import websockets

from src.config.settings import settings
from src.services.codex_service import CodexService

logger = logging.getLogger(__name__)


class AgentDaemon:
    """本地Agent守护进程。"""

    def __init__(self, server_url: str, api_key: str, agent_name: str = "local-agent") -> None:
        self.server_url = server_url
        self.api_key = api_key
        self.agent_name = agent_name
        self.agent_id = str(uuid.uuid4())
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.codex_service = CodexService()
        self.supported_models = ["codex", "claude", "qwen", "gpt-4", "local-llm"]

        logger.info("AgentDaemon initialized: %s (%s)", self.agent_name, self.agent_id)

    async def start(self) -> None:
        """启动守护进程。"""
        self.is_running = True
        logger.info("Starting AgentDaemon on %s", self.server_url)

        while self.is_running:
            try:
                await self._connect_to_server()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Connection failed: %s. Retrying in 5 seconds...", exc)
                await asyncio.sleep(5)

    async def _connect_to_server(self) -> None:
        """连接到云端服务器。"""
        try:
            async with websockets.connect(self.server_url, ping_interval=20, ping_timeout=20) as ws:
                self.ws = ws
                logger.info("Connected to server")
                await self._register_agent()
                await self._listen_for_tasks()
        finally:
            self.ws = None

    async def _register_agent(self) -> None:
        """向服务器注册本机Agent。"""
        if not self.ws:
            raise RuntimeError("WebSocket connection is not available")

        register_msg = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "api_key": self.api_key,
            "supported_models": self.supported_models,
            "status": "online",
            "timestamp": datetime.now().isoformat(),
        }

        await self.ws.send(json.dumps(register_msg))
        logger.info("Registered agent: %s", self.agent_name)

    async def _listen_for_tasks(self) -> None:
        """监听来自服务器的任务。"""
        if not self.ws:
            raise RuntimeError("WebSocket connection is not available")

        async for message in self.ws:
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON message: %s", message)

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """处理来自服务器的消息。"""
        msg_type = data.get("type")

        if msg_type == "task":
            await self._execute_task(data)
        elif msg_type == "heartbeat":
            await self._respond_heartbeat()
        elif msg_type == "config":
            await self._update_config(data)

    async def _execute_task(self, task_data: Dict[str, Any]) -> None:
        """执行任务。"""
        task_id = task_data.get("task_id")
        prompt = task_data.get("prompt", "")
        model = task_data.get("model", "codex")
        user_id = task_data.get("user_id")
        source = task_data.get("source", "api")

        logger.info("Received task %s for model %s", task_id, model)

        try:
            await self._send_status_update(task_id, "running", "Task started on local agent")
            result = await self._run_model(model, prompt)
            await self._send_result(task_id, "completed", result, user_id, source)
            logger.info("Task %s completed", task_id)
        except Exception as exc:
            logger.error("Task %s failed: %s", task_id, exc)
            await self._send_result(task_id, "failed", str(exc), user_id, source)

    async def _run_model(self, model: str, prompt: str) -> str:
        """根据模型名执行具体任务。"""
        model_name = model.lower()
        logger.info("Running model: %s", model_name)

        if model_name == "codex":
            return await self._run_codex(prompt)
        if model_name == "claude":
            return await self._run_claude(prompt)
        if model_name == "qwen":
            return await self._run_qwen(prompt)
        if model_name == "gpt-4":
            return await self._run_gpt4(prompt)
        if model_name == "local-llm":
            return await self._run_local_llm(prompt)

        raise ValueError(f"Unsupported model: {model}")

    async def _run_codex(self, prompt: str) -> str:
        """运行Codex。"""
        return await self.codex_service.generate_code(prompt)

    async def _run_claude(self, prompt: str) -> str:
        """运行Claude。"""
        return self._missing_integration_message("Claude", "CLAUDE_API_KEY", prompt)

    async def _run_qwen(self, prompt: str) -> str:
        """运行Qwen。"""
        return self._missing_integration_message("Qwen", "QWEN_API_KEY", prompt)

    async def _run_gpt4(self, prompt: str) -> str:
        """运行GPT-4。"""
        return self._missing_integration_message("GPT-4", "OPENAI_API_KEY", prompt)

    async def _run_local_llm(self, prompt: str) -> str:
        """运行本地LLM。"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.LOCAL_LLM_URL,
                    json={
                        "model": settings.LOCAL_LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    response.raise_for_status()
                    result = await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            logger.error("Local LLM error: %s", exc)
            return f"Local LLM error: {exc}"

        return result.get("response", "") or "Local LLM returned an empty response."

    async def _send_status_update(self, task_id: str, status: str, message: str = "") -> None:
        """发送任务状态更新。"""
        if not self.ws:
            return

        update = {
            "type": "status_update",
            "task_id": task_id,
            "agent_id": self.agent_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        await self.ws.send(json.dumps(update))

    async def _send_result(
        self,
        task_id: Optional[str],
        status: str,
        result: str,
        user_id: Optional[str],
        source: str,
    ) -> None:
        """发送任务结果。"""
        if not self.ws:
            return

        result_msg = {
            "type": "task_result",
            "task_id": task_id,
            "agent_id": self.agent_id,
            "user_id": user_id,
            "source": source,
            "status": status,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
        await self.ws.send(json.dumps(result_msg))
        logger.info("Sent result for task %s", task_id)

    async def _respond_heartbeat(self) -> None:
        """响应心跳检测。"""
        if not self.ws:
            return

        heartbeat = {
            "type": "heartbeat_response",
            "agent_id": self.agent_id,
            "status": "online",
            "timestamp": datetime.now().isoformat(),
        }
        await self.ws.send(json.dumps(heartbeat))

    async def _update_config(self, data: Dict[str, Any]) -> None:
        """更新本机配置。"""
        config = data.get("config", {})
        logger.info("Updating config: %s", config)

    def stop(self) -> None:
        """停止守护进程。"""
        self.is_running = False
        logger.info("Stopping AgentDaemon...")

    @staticmethod
    def _missing_integration_message(model_name: str, env_name: str, prompt: str) -> str:
        """为未接入的模型返回清晰的占位提示。"""
        return (
            f"{model_name} integration is scaffolded but not wired to a live API yet.\n\n"
            f"Configure `{env_name}` and extend `AgentDaemon` to call the provider.\n\n"
            f"Prompt:\n{prompt}"
        )


async def run_daemon(server_url: str, api_key: str, agent_name: str = "local-agent") -> None:
    """启动本地Agent守护进程。"""
    daemon = AgentDaemon(server_url, api_key, agent_name)
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(
        run_daemon(
            server_url="ws://localhost:8000/api/v1/agent/ws?agent_id=local-test-agent&api_key=test-key",
            api_key="test-key",
            agent_name="local-test-agent",
        )
    )

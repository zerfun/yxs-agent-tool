"""本地Agent守护进程 - 在用户电脑上运行，接收和执行任务"""

import asyncio
import logging
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import websockets
import aiohttp

from src.config.settings import settings
from src.models.schemas import TaskRequest, AIModel, MessageSource, AgentStatus

logger = logging.getLogger(__name__)

class AgentDaemon:
    """
    本地Agent守护进程
    
    工作流程：
    1. 连接到云端服务器的WebSocket
    2. 注册本机作为计算节点
    3. 监听任务队列
    4. 执行本地AI Agent任务（Codex、Claude等）
    5. 返回结果到云端
    6. 云端推送结果给用户（微信、飞书等）
    
    这是实现"用户通过微信控制电脑AI Agent"的关键组件！
    """
    
    def __init__(self, server_url: str, api_key: str, agent_name: str = "local-agent"):
        """
        初始化本地Agent守护进程
        
        Args:
            server_url: 云端服务器地址 (e.g., ws://api.yxs-agent.com/agent/ws)
            api_key: 认证密钥
            agent_name: 本机Agent名称
        """
        self.server_url = server_url
        self.api_key = api_key
        self.agent_name = agent_name
        self.agent_id = str(uuid.uuid4())
        self.ws = None
        self.is_running = False
        self.supported_models = ["codex", "claude", "gpt-4", "local-llm"]
        
        logger.info(f"AgentDaemon initialized: {self.agent_name} ({self.agent_id})")
    
    async def start(self):
        """启动守护进程"""
        self.is_running = True
        logger.info(f"🚀 Starting AgentDaemon on {self.server_url}")
        
        while self.is_running:
            try:
                await self._connect_to_server()
            except Exception as e:
                logger.error(f"Connection failed: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
    
    async def _connect_to_server(self):
        """连接到云端服务器"""
        try:
            async with websockets.connect(self.server_url) as ws:
                self.ws = ws
                logger.info("✅ Connected to server")
                
                # 发送注册信息
                await self._register_agent()
                
                # 监听任务
                await self._listen_for_tasks()
        
        except Exception as e:
            logger.error(f"Server connection error: {e}")
            self.ws = None
    
    async def _register_agent(self):
        """向服务器注册本机Agent"""
        register_msg = {
            "type": "register",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "api_key": self.api_key,
            "supported_models": self.supported_models,
            "status": "online",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.ws.send(json.dumps(register_msg))\n        logger.info(f"📝 Registered agent: {self.agent_name}")
    
    async def _listen_for_tasks(self):
        """监听来自服务器的任务"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"Error listening for tasks: {e}")
    
    async def _handle_message(self, data: Dict[str, Any]):
        """
        处理来自服务器的消息
        
        消息类型：
        - task: 新任务
        - heartbeat: 心跳检测
        - config: 配置更新
        """
        msg_type = data.get("type")
        
        if msg_type == "task":
            await self._execute_task(data)
        elif msg_type == "heartbeat":
            await self._respond_heartbeat()
        elif msg_type == "config":
            await self._update_config(data)
    
    async def _execute_task(self, task_data: Dict[str, Any]):
        """
        执行任务
        
        Args:
            task_data: 任务数据
        """
        task_id = task_data.get("task_id")
        prompt = task_data.get("prompt")
        model = task_data.get("model", "codex")
        user_id = task_data.get("user_id")
        source = task_data.get("source", "api")
        
        logger.info(f"📋 Received task {task_id}: {prompt[:50]}...")
        
        try:
            # 发送任务开始消息
            await self._send_status_update(task_id, "running", "Task started on local agent")
            
            # 执行任务
            result = await self._run_model(model, prompt)
            
            # 发送成功结果
            await self._send_result(task_id, "completed", result, user_id, source)
            
            logger.info(f"✅ Task {task_id} completed")
        
        except Exception as e:
            logger.error(f"❌ Task {task_id} failed: {e}")
            await self._send_result(task_id, "failed", str(e), user_id, source)
    
    async def _run_model(self, model: str, prompt: str) -> str:
        """
        在本地运行AI模型
        
        支持的模型：
        - codex: GitHub Copilot (需要本地配置)
        - claude: Claude API (需要本地Key)
        - gpt-4: OpenAI GPT-4 (需要本地Key)
        - local-llm: 本地LLM (如ollama、llama2)
        
        Args:
            model: 模型名称
            prompt: 提示词
        
        Returns:
            生成的结果
        \"\"\"\n        logger.info(f\"🤖 Running model: {model}\")\n        \n        if model == \"codex\":\n            return await self._run_codex(prompt)\n        elif model == \"claude\":\n            return await self._run_claude(prompt)\n        elif model == \"gpt-4\":\n            return await self._run_gpt4(prompt)\n        elif model == \"local-llm\":\n            return await self._run_local_llm(prompt)\n        else:\n            raise ValueError(f\"Unsupported model: {model}\")\n    \n    async def _run_codex(self, prompt: str) -> str:\n        \"\"\"\n        运行Codex\n        \n        可选方案：\n        1. 调用本地GitHub Copilot LSP\n        2. 调用远程GitHub Copilot API\n        3. 使用本地替代品（如Code LLaMA）\n        \"\"\"\n        # TODO: 实现本地Codex调用\n        # 示例：使用subprocess调用本地copilot-lsp或其他编辑器扩展\n        return f\"# Codex Response\\n\\nPrompt: {prompt}\\n\\n# Generated code...\\n\"\n    \n    async def _run_claude(self, prompt: str) -> str:\n        \"\"\"\n        运行Claude\n        \n        需要配置Anthropic API Key\n        \"\"\"\n        # TODO: 实现Claude调用\n        try:\n            import anthropic\n            client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)\n            \n            message = client.messages.create(\n                model=\"claude-3-opus-20240229\",\n                max_tokens=2048,\n                messages=[{\"role\": \"user\", \"content\": prompt}]\n            )\n            \n            return message.content[0].text\n        except Exception as e:\n            logger.error(f\"Claude API error: {e}\")\n            return f\"Claude error: {str(e)}\"\n    \n    async def _run_gpt4(self, prompt: str) -> str:\n        \"\"\"\n        运行GPT-4\n        \n        需要配置OpenAI API Key\n        \"\"\"\n        # TODO: 实现GPT-4调用\n        try:\n            import openai\n            openai.api_key = settings.OPENAI_API_KEY\n            \n            response = openai.ChatCompletion.create(\n                model=\"gpt-4\",\n                messages=[{\"role\": \"user\", \"content\": prompt}],\n                temperature=0.7,\n                max_tokens=2048\n            )\n            \n            return response.choices[0].message.content\n        except Exception as e:\n            logger.error(f\"OpenAI API error: {e}\")\n            return f\"GPT-4 error: {str(e)}\"\n    \n    async def _run_local_llm(self, prompt: str) -> str:\n        \"\"\"\n        运行本地LLM\n        \n        支持Ollama、LM Studio等本地LLM服务\n        \"\"\"\n        # TODO: 实现本地LLM调用\n        # 示例：调用本地ollama服务\n        try:\n            async with aiohttp.ClientSession() as session:\n                async with session.post(\n                    \"http://localhost:11434/api/generate\",\n                    json={\n                        \"model\": \"llama2\",\n                        \"prompt\": prompt,\n                        \"stream\": False\n                    }\n                ) as resp:\n                    result = await resp.json()\n                    return result.get(\"response\", \"\")\n        except Exception as e:\n            logger.error(f\"Local LLM error: {e}\")\n            return f\"Local LLM error: {str(e)}\"\n    \n    async def _send_status_update(self, task_id: str, status: str, message: str = \"\"):\n        \"\"\"发送任务状态更新\"\"\"\n        if not self.ws:\n            return\n        \n        update = {\n            \"type\": \"status_update\",\n            \"task_id\": task_id,\n            \"agent_id\": self.agent_id,\n            \"status\": status,\n            \"message\": message,\n            \"timestamp\": datetime.now().isoformat()\n        }\n        \n        await self.ws.send(json.dumps(update))\n    \n    async def _send_result(self, task_id: str, status: str, result: str, user_id: str, source: str):\n        \"\"\"发送任务结果\"\"\"\n        if not self.ws:\n            return\n        \n        result_msg = {\n            \"type\": \"task_result\",\n            \"task_id\": task_id,\n            \"agent_id\": self.agent_id,\n            \"user_id\": user_id,\n            \"source\": source,\n            \"status\": status,\n            \"result\": result,\n            \"timestamp\": datetime.now().isoformat()\n        }\n        \n        await self.ws.send(json.dumps(result_msg))\n        logger.info(f\"📤 Sent result for task {task_id}\")\n    \n    async def _respond_heartbeat(self):\n        \"\"\"响应心跳检测\"\"\"\n        if not self.ws:\n            return\n        \n        heartbeat = {\n            \"type\": \"heartbeat_response\",\n            \"agent_id\": self.agent_id,\n            \"status\": \"online\",\n            \"timestamp\": datetime.now().isoformat()\n        }\n        \n        await self.ws.send(json.dumps(heartbeat))\n    \n    async def _update_config(self, data: Dict[str, Any]):\n        \"\"\"更新本机配置\"\"\"\n        config = data.get(\"config\", {})\n        logger.info(f\"⚙️ Updating config: {config}\")\n    \n    def stop(self):\n        \"\"\"停止守护进程\"\"\"\n        self.is_running = False\n        logger.info(\"Stopping AgentDaemon...\")\n\n\nasync def run_daemon(server_url: str, api_key: str, agent_name: str = \"local-agent\"):\n    \"\"\"\n    启动本地Agent守护进程\n    \n    使用示例：\n    ```python\n    import asyncio\n    from src.daemon.agent_daemon import run_daemon\n    \n    asyncio.run(run_daemon(\n        server_url=\"ws://your-server.com/agent/ws\",\n        api_key=\"your-api-key\",\n        agent_name=\"my-office-agent\"\n    ))\n    ```\n    \"\"\"\n    daemon = AgentDaemon(server_url, api_key, agent_name)\n    await daemon.start()\n\n\nif __name__ == \"__main__\":\n    # 本地测试\n    asyncio.run(run_daemon(\n        server_url=\"ws://localhost:8000/agent/ws\",\n        api_key=\"test-key\",\n        agent_name=\"local-test-agent\"\n    ))\n"
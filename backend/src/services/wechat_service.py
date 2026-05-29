"""微信服务 - 微信集成。"""

import logging
import re
import time
from typing import Any, Optional
from xml.etree import ElementTree as ET

import aiohttp

from src.config.settings import settings
from src.models.schemas import AgentStatus, TaskResponse

logger = logging.getLogger(__name__)


class WeChatService:
    """微信服务。"""

    def __init__(self) -> None:
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.token = settings.WECHAT_TOKEN
        self.api_base = settings.WECHAT_API_BASE.rstrip("/")
        self.max_push_length = settings.WECHAT_RESULT_PUSH_MAX_LENGTH
        self.command_task_limit = settings.WECHAT_COMMAND_TASK_LIMIT
        self._access_token: Optional[str] = None
        self._access_token_expires_at = 0.0
        logger.info("WeChatService initialized")

    def parse_message(self, data: str) -> Optional[dict[str, Any]]:
        """解析微信消息 XML。"""
        try:
            root = ET.fromstring(data)
            message = {
                "from_user": root.findtext("FromUserName"),
                "to_user": root.findtext("ToUserName"),
                "create_time": int(root.findtext("CreateTime", "0")),
                "msg_type": root.findtext("MsgType"),
                "msg_id": root.findtext("MsgId"),
                "content": root.findtext("Content"),
                "event": root.findtext("Event"),
            }
            logger.info("Parsed WeChat message from %s", message["from_user"])
            return message
        except Exception as exc:
            logger.error("Failed to parse WeChat message: %s", exc)
            return None

    def create_response(self, from_user: str, to_user: str, content: str) -> str:
        """创建微信被动回复 XML。"""
        create_time = int(time.time())
        return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """验证微信签名。"""
        import hashlib

        data = sorted([self.token, timestamp, nonce])
        computed_signature = hashlib.sha1("".join(data).encode("utf-8")).hexdigest()
        return computed_signature == signature

    def parse_text_command(self, content: Optional[str]) -> Optional[dict[str, str]]:
        """解析微信文本命令。"""
        if not content:
            return None

        normalized = " ".join(content.strip().split())
        if not normalized:
            return None

        if normalized in {"帮助", "help", "HELP", "?"}:
            return {"type": "help"}
        if normalized in {"最近任务", "我的任务", "任务列表"}:
            return {"type": "recent_tasks"}

        matched = re.match(r"^(状态|查询|任务)\s*[:：]?\s*([A-Za-z0-9-]{8,})$", normalized)
        if matched:
            return {"type": "task_status", "task_id": matched.group(2)}

        return None

    def build_help_message(self) -> str:
        """生成帮助说明。"""
        return (
            "可用命令：\n"
            "1. 直接输入需求，创建新任务\n"
            "2. 状态 <任务ID>，查询任务进度\n"
            "3. 最近任务，查看最近提交记录\n"
            "4. 帮助，查看命令说明"
        )

    def build_task_status_message(self, task: TaskResponse) -> str:
        """格式化任务状态消息。"""
        lines = [
            f"任务ID: {task.task_id}",
            f"状态: {self._status_label(task.status)}",
        ]

        if task.model is not None:
            lines.append(f"模型: {task.model.value}")
        if task.metadata.get("execution_mode"):
            lines.append(f"执行方式: {task.metadata['execution_mode']}")
        if task.metadata.get("agent_id"):
            lines.append(f"Agent: {task.metadata['agent_id']}")

        if task.status == AgentStatus.FAILED and task.error:
            lines.append(f"错误: {self._truncate(task.error)}")
        elif task.status == AgentStatus.COMPLETED and task.result:
            lines.append("")
            lines.append(self._truncate(task.result))

        return "\n".join(lines)

    def build_task_list_message(self, tasks: list[TaskResponse]) -> str:
        """格式化最近任务列表。"""
        if not tasks:
            return "最近还没有任务记录。"

        lines = ["最近任务："]
        for index, task in enumerate(tasks, start=1):
            task_id = task.task_id[:8]
            model = task.model.value if task.model is not None else "-"
            lines.append(f"{index}. {task_id}  {self._status_label(task.status)}  {model}")

        lines.append("")
        lines.append("发送“状态 <任务ID>”可查看详情。")
        return "\n".join(lines)

    def build_submission_message(self, task: TaskResponse) -> str:
        """格式化任务提交后的立即回复。"""
        if task.status == AgentStatus.QUEUED:
            return (
                "任务已接收，正在排队等待本地 Agent 处理。\n"
                f"任务ID: {task.task_id}\n"
                "处理完成后会主动推送结果。\n"
                f"也可以发送“状态 {task.task_id}”查询进度。"
            )

        if task.status == AgentStatus.FAILED:
            error = self._truncate(task.error or "未知错误")
            return f"任务执行失败\n任务ID: {task.task_id}\n错误: {error}"

        return self.build_task_status_message(task)

    async def push_task_result(
        self,
        to_user: str,
        task_id: str,
        status: str,
        result: str,
        task: Optional[TaskResponse] = None,
    ) -> bool:
        """通过客服消息主动推送任务结果。"""
        if task is not None:
            content = "任务处理完成\n" + self.build_task_status_message(task)
        else:
            content = (
                "任务处理完成\n"
                f"任务ID: {task_id}\n"
                f"状态: {self._status_label(status)}\n\n"
                f"{self._truncate(result)}"
            )

        return await self.send_custom_text(to_user, content)

    async def send_custom_text(self, to_user: str, content: str) -> bool:
        """发送微信客服文本消息。"""
        if not to_user:
            logger.warning("WeChat push skipped: missing recipient")
            return False

        if not self.app_id or not self.app_secret:
            logger.warning("WeChat push skipped: app credentials not configured")
            return False

        access_token = await self._get_access_token()
        if not access_token:
            return False

        url = f"{self.api_base}/cgi-bin/message/custom/send?access_token={access_token}"
        payload = {
            "touser": to_user,
            "msgtype": "text",
            "text": {"content": self._truncate(content)},
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.post(url, json=payload) as response:
                    data = await response.json(content_type=None)
        except Exception as exc:
            logger.error("Failed to push WeChat custom message: %s", exc)
            return False

        if data.get("errcode") != 0:
            logger.warning("WeChat push rejected: %s", data)
            return False

        logger.info("WeChat result pushed to user %s", to_user)
        return True

    async def _get_access_token(self) -> Optional[str]:
        """获取并缓存公众号 access token。"""
        now = time.time()
        if self._access_token and now < self._access_token_expires_at:
            return self._access_token

        url = (
            f"{self.api_base}/cgi-bin/token"
            f"?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        )

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.get(url) as response:
                    data = await response.json(content_type=None)
        except Exception as exc:
            logger.error("Failed to fetch WeChat access token: %s", exc)
            return None

        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))
        if not access_token or not expires_in:
            logger.warning("Invalid WeChat access token response: %s", data)
            return None

        self._access_token = access_token
        self._access_token_expires_at = now + max(expires_in - 60, 60)
        return access_token

    def _truncate(self, content: Optional[str]) -> str:
        """按微信限制裁剪文本。"""
        if not content:
            return ""

        text = content.strip()
        if len(text) <= self.max_push_length:
            return text

        return text[: self.max_push_length - 3] + "..."

    @staticmethod
    def _status_label(status: AgentStatus | str) -> str:
        """状态中文映射。"""
        value = status.value if isinstance(status, AgentStatus) else str(status)
        mapping = {
            AgentStatus.IDLE.value: "待处理",
            AgentStatus.QUEUED.value: "已排队",
            AgentStatus.RUNNING.value: "执行中",
            AgentStatus.COMPLETED.value: "已完成",
            AgentStatus.FAILED.value: "失败",
        }
        return mapping.get(value, value)

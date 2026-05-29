"""Pydantic数据模型"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

# ============ 枚举 ============

class AgentStatus(str, Enum):
    """Agent状态"""
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class MessageSource(str, Enum):
    """消息来源"""
    WECHAT = "wechat"
    FEISHU = "feishu"
    QQ = "qq"
    API = "api"

class AIModel(str, Enum):
    """AI模型"""
    CODEX = "codex"
    CLAUDE = "claude"
    QWEN = "qwen"

# ============ 任务相关 ============

class TaskRequest(BaseModel):
    """任务请求"""
    prompt: str
    model: AIModel = AIModel.CODEX
    temperature: float = Field(default=0.5, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=1, le=4096)
    context: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: AgentStatus
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class Task(BaseModel):
    """任务模型"""
    id: str
    user_id: str
    prompt: str
    model: AIModel
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    source: MessageSource
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ============ 消息相关 ============

class WeChatMessage(BaseModel):
    """微信消息"""
    from_user: str
    to_user: str
    create_time: int
    msg_type: str
    msg_id: str
    content: Optional[str] = None
    event: Optional[str] = None

class ChatMessage(BaseModel):
    """聊天消息"""
    user_id: str
    content: str
    source: MessageSource
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ============ 用户相关 ============

class User(BaseModel):
    """用户模型"""
    id: str
    username: str
    email: Optional[str] = None
    wechat_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True

# ============ API响应 ============

class APIResponse(BaseModel):
    """标准API响应"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: Optional[str] = None

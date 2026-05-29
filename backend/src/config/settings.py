"""全局配置"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # GitHub Codex
    GITHUB_TOKEN: str = ""
    CODEX_MODEL: str = "code-davinci-002"
    CODEX_API_URL: str = "https://api.github.com"
    ENABLE_CODEX: bool = True

    # Claude / OpenAI / Qwen
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-5-sonnet-latest"
    ENABLE_CLAUDE: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-plus"
    ENABLE_QWEN: bool = False

    # 微信配置
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_TOKEN: str = ""
    WECHAT_ENCODING_AES_KEY: str = ""
    ENABLE_WECHAT: bool = True

    # 飞书配置
    ENABLE_FEISHU: bool = False
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""

    # QQ配置
    ENABLE_QQ: bool = False

    # 本地Agent / WebSocket
    AGENT_API_KEYS: str = "test-key,dev-key"
    LOCAL_LLM_URL: str = "http://localhost:11434/api/generate"
    LOCAL_LLM_MODEL: str = "llama2"

    # 任务存储
    TASK_STORE_BACKEND: str = "memory"
    TASK_STORE_PREFIX: str = "yxs_agent"
    TASK_STORE_MAX_ITEMS: int = 1000

    # 数据库
    DB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "yxs_agent"
    REDIS_URL: str = "redis://localhost:6379/0"

    # 任务队列
    BROKER_URL: str = "redis://localhost:6379/1"
    RESULT_BACKEND: str = "redis://localhost:6379/2"

    # 安全
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def agent_api_keys(self) -> list[str]:
        """解析Agent API密钥列表。"""
        return [key.strip() for key in self.AGENT_API_KEYS.split(",") if key.strip()]


# 全局配置实例
settings = Settings()

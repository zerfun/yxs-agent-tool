"""全局配置"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    LOG_LEVEL: str = "INFO"
    
    # GitHub Codex
    GITHUB_TOKEN: str = ""
    CODEX_MODEL: str = "code-davinci-002"
    CODEX_API_URL: str = "https://api.github.com"
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()

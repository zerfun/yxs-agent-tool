"""研享数Agent工具 - 主入口"""

import asyncio
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入路由
from src.api import agent_router, health_router
from src.services.agent_service import AgentService
from src.services.wechat_service import WeChatService

# 创建FastAPI应用
app = FastAPI(
    title="研享数Agent工具API",
    description="跨端AI Agent控制工具",
    version="0.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router.router)
app.include_router(agent_router.router, prefix="/api/v1")

# 全局异常处理
from src.api.exceptions import setup_exception_handlers
setup_exception_handlers(app)

# 启动事件
@app.on_event("startup")
async def startup_event():
    """服务启动"""
    logger.info("🚀 研享数Agent工具启动中...")
    
    # 初始化服务
    try:
        agent_service = AgentService()
        wechat_service = WeChatService()
        
        # 保存到app状态
        app.state.agent_service = agent_service
        app.state.wechat_service = wechat_service
        
        logger.info("✅ 服务初始化完成")
    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭"""
    logger.info("🛑 研享数Agent工具关闭中...")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

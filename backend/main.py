"""研享数Agent工具 - 主入口"""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 加载环境变量
load_dotenv()

# 创建日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入路由
from src.api import agent_router, agent_ws_router, health_router, wechat_router
from src.daemon.connection_manager import agent_manager, start_heartbeat_task
from src.repositories.task_store import create_task_store
from src.services.agent_service import AgentService
from src.services.wechat_service import WeChatService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    logger.info("🚀 研享数Agent工具启动中...")

    try:
        app.state.task_store = await create_task_store()
        app.state.agent_service = AgentService(
            connection_manager=agent_manager,
            task_store=app.state.task_store,
        )
        app.state.wechat_service = WeChatService()
        agent_manager.bind_task_service(app.state.agent_service)
        app.state.heartbeat_task = asyncio.create_task(start_heartbeat_task())
        logger.info("✅ 服务初始化完成")
        yield
    finally:
        heartbeat_task = getattr(app.state, "heartbeat_task", None)
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")

        task_store = getattr(app.state, "task_store", None)
        if task_store is not None:
            await task_store.close()

        logger.info("🛑 研享数Agent工具关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="研享数Agent工具API",
    description="跨端AI Agent控制工具",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(agent_ws_router.router, prefix="/api/v1")
app.include_router(wechat_router.router, prefix="/api/v1")

# 全局异常处理
from src.api.exceptions import setup_exception_handlers
setup_exception_handlers(app)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

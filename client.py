#!/usr/bin/env python3
"""本地Agent守护进程启动脚本。"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 添加backend目录到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from src.daemon.agent_daemon import run_daemon
from src.utils.logger import setup_logger

logger = setup_logger(__name__, "client.log", "INFO")


def main() -> None:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="研享数Agent工具 - 本地客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：

1. 本地测试：
   python client.py

2. 连接到远程服务器：
   python client.py --server ws://api.yxs-agent.com/api/v1/agent/ws --key your-api-key

3. 自定义Agent名称：
   python client.py --name my-office-agent

4. 调试模式：
   python client.py --debug
""",
    )

    parser.add_argument(
        "--server",
        type=str,
        default="ws://localhost:8000/api/v1/agent/ws",
        help="云端服务器WebSocket地址 (默认: ws://localhost:8000/api/v1/agent/ws)",
    )
    parser.add_argument(
        "--key",
        type=str,
        default="test-key",
        help="API密钥用于认证 (默认: test-key)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="local-agent",
        help="本机Agent名称 (默认: local-agent)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式",
    )

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    logger.info("=" * 60)
    logger.info("研享数Agent工具 - 本地客户端")
    logger.info("=" * 60)
    logger.info("服务器: %s", args.server)
    logger.info("Agent名称: %s", args.name)
    logger.info("使用API密钥: %s...", args.key[:10])
    logger.info("=" * 60)
    logger.info("连接中...")

    try:
        asyncio.run(
            run_daemon(
                server_url=f"{args.server}?agent_id={args.name}&api_key={args.key}",
                api_key=args.key,
                agent_name=args.name,
            )
        )
    except KeyboardInterrupt:
        logger.info("客户端已停止")
        sys.exit(0)
    except Exception as exc:
        logger.error("错误: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""QQ服务 - QQ机器人集成"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from src.config.settings import settings

logger = logging.getLogger(__name__)

class QQService:
    """QQ机器人服务"""
    
    def __init__(self):
        """
        初始化QQ服务
        
        QQ机器人配置步骤：
        1. 访问 https://bot.q.qq.com/
        2. 创建机器人应用
        3. 获取 BotAppID 和 BotToken
        4. 配置消息回调地址
        5. 订阅频道消息事件
        """
        self.bot_app_id = settings.WECHAT_APP_ID  # 临时使用，应单独配置
        self.bot_token = settings.WECHAT_TOKEN    # 临时使用，应单独配置
        self.api_base = "https://api.sgroup.qq.com"
        logger.info("QQService initialized")
    
    async def parse_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析QQ消息
        
        QQ机器人支持两种消息格式：
        1. 频道消息 (Guild Message)
        2. 私信 (Direct Message)
        
        Args:
            data: QQ webhook回调数据
        
        Returns:
            解析后的消息字典
        """
        try:
            # QQ消息格式
            op = data.get('op')  # 操作码
            t = data.get('t')    # 事件类型
            d = data.get('d', {})  # 事件数据
            
            # 处理不同的事件类型
            if t == 'MESSAGE_CREATE':
                return self._parse_guild_message(d)
            elif t == 'DIRECT_MESSAGE_CREATE':
                return self._parse_direct_message(d)
            elif t == 'GUILD_CREATE':
                return self._handle_guild_create(d)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse QQ message: {e}")
            return None
    
    def _parse_guild_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析频道消息
        
        Args:
            data: 频道消息数据
        
        Returns:
            解析结果
        """
        return {
            "msg_type": "text",
            "content": data.get('content'),
            "from_user": data.get('author', {}).get('id'),
            "channel_id": data.get('channel_id'),
            "guild_id": data.get('guild_id'),
            "msg_id": data.get('id'),
            "create_time": data.get('timestamp'),
        }
    
    def _parse_direct_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析私信
        
        Args:
            data: 私信数据
        
        Returns:
            解析结果
        """
        return {
            "msg_type": "text",
            "content": data.get('content'),
            "from_user": data.get('author', {}).get('id'),
            "guild_id": data.get('guild_id'),
            "msg_id": data.get('id'),
            "create_time": data.get('timestamp'),
            "is_private": True
        }
    
    def _handle_guild_create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理频道创建事件
        
        Args:
            data: 事件数据
        
        Returns:
            事件信息
        """
        logger.info(f"Robot joined guild: {data.get('name')}")
        return {
            "event_type": "guild_create",
            "guild_id": data.get('id'),
            "guild_name": data.get('name'),
        }
    
    async def create_reply(self, guild_id: str, channel_id: str, content: str, msg_id: str = None) -> Dict[str, Any]:
        """
        创建QQ回复
        
        Args:
            guild_id: 频道ID
            channel_id: 子频道ID
            content: 回复内容
            msg_id: 回复的消息ID（用于引用）
        
        Returns:
            API调用载荷
        """
        payload = {
            "content": content,
            "msg_type": 0  # 0: 文本消息
        }
        
        if msg_id:
            payload["msg_id"] = msg_id  # 引用消息
        
        return payload
    
    def verify_signature(self, raw_data: bytes, signature: str) -> bool:
        """
        验证QQ签名（hmac-sha256）
        
        Args:
            raw_data: 原始请求体
            signature: 签名
        
        Returns:
            是否验证成功
        """
        import hmac
        import hashlib
        import base64
        
        # QQ使用 timestamp + msg_body 计算签名
        computed_signature = base64.b64encode(
            hmac.new(
                self.bot_token.encode(),
                raw_data,
                hashlib.sha256
            ).digest()
        ).decode()
        
        return computed_signature == signature

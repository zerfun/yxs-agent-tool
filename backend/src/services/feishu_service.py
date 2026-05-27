"""飞书服务 - 企业IM集成"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from src.config.settings import settings

logger = logging.getLogger(__name__)

class FeishuService:
    """飞书机器人服务"""
    
    def __init__(self):
        """
        初始化飞书服务
        
        飞书应用配置步骤：
        1. 访问 https://open.feishu.cn/app
        2. 创建自建应用
        3. 获取 App ID 和 App Secret
        4. 配置机器人消息卡片
        5. 订阅事件（消息、应用开通等）
        """
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self.access_token = None
        self.token_expire_time = None
        logger.info("FeishuService initialized")
    
    async def parse_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析飞书消息
        
        Args:
            data: 飞书webhook回调数据
        
        Returns:
            解析后的消息字典
        """
        try:
            # 飞书消息格式
            header = data.get('header', {})
            event = data.get('event', {})
            
            # 处理消息事件
            if header.get('event_type') == 'im.message.message_create_v1':
                message_content = event.get('message', {})
                
                parsed = {
                    "msg_type": message_content.get('message_type'),
                    "content": self._extract_content(message_content),
                    "from_user": event.get('sender', {}).get('sender_id', {}).get('open_id'),
                    "chat_id": event.get('message', {}).get('chat_id'),
                    "msg_id": message_content.get('message_id'),
                    "create_time": message_content.get('create_time'),
                }
                
                logger.info(f"Parsed Feishu message from {parsed['from_user']}")
                return parsed
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse Feishu message: {e}")
            return None
    
    async def create_reply(self, chat_id: str, content: str, msg_type: str = "text") -> Dict[str, Any]:
        """
        创建飞书回复
        
        Args:
            chat_id: 聊天ID
            content: 回复内容
            msg_type: 消息类型 (text, image, file等)
        
        Returns:
            飞书API调用载荷
        """
        if msg_type == "text":
            return {
                "receive_id": chat_id,
                "content": json.dumps({"text": content}),
                "msg_type": "text"
            }
        elif msg_type == "card":
            # 消息卡片（富文本）
            return {
                "receive_id": chat_id,
                "content": json.dumps(self._create_rich_card(content)),
                "msg_type": "interactive"
            }
        else:
            return {
                "receive_id": chat_id,
                "content": json.dumps({"text": content}),
                "msg_type": "text"
            }
    
    def verify_signature(self, timestamp: str, nonce: str, signature: str) -> bool:
        """
        验证飞书签名
        
        Args:
            timestamp: 时间戳
            nonce: 随机数
            signature: 签名
        
        Returns:
            是否验证成功
        """
        import hmac
        import hashlib
        
        # 拼接消息体
        message = timestamp + nonce + settings.WECHAT_TOKEN  # 使用相同的token
        
        # 计算签名
        computed_signature = hmac.new(
            settings.WECHAT_TOKEN.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return computed_signature == signature
    
    def _extract_content(self, message: Dict[str, Any]) -> Optional[str]:
        """
        提取消息内容
        
        Args:
            message: 飞书消息对象
        
        Returns:
            消息文本内容
        """
        msg_type = message.get('message_type')
        content = message.get('content', '{}')
        
        try:
            if msg_type == 'text':
                data = json.loads(content)
                return data.get('text')
            elif msg_type == 'image':
                return "[图片消息]"
            elif msg_type == 'file':
                return "[文件消息]"
            else:
                return "[未支持的消息类型]"
        except:
            return None
    
    def _create_rich_card(self, content: str) -> Dict[str, Any]:
        """
        创建富文本卡片
        
        Args:
            content: 卡片内容
        
        Returns:
            卡片JSON对象
        """
        return {
            "type": "template",
            "data": {
                "template_id": "AAqsqbgJhr4-2-gop_HWbNd4NSvADAqQ47ExbqnywKU",
                "template_variable": {
                    "title": "研享数Agent",
                    "content": content
                }
            }
        }

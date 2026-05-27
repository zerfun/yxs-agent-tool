"""微信服务 - 微信集成"""

import logging
from typing import Optional, Dict, Any
from xml.etree import ElementTree as ET

from src.config.settings import settings

logger = logging.getLogger(__name__)

class WeChatService:
    """微信服务"""
    
    def __init__(self):
        """初始化微信服务"""
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.token = settings.WECHAT_TOKEN
        logger.info("WeChatService initialized")
    
    def parse_message(self, data: str) -> Optional[Dict[str, Any]]:
        """解析微信消息XML"""
        try:
            root = ET.fromstring(data)
            
            message = {
                "from_user": root.findtext("FromUserName"),
                "to_user": root.findtext("ToUserName"),
                "create_time": int(root.findtext("CreateTime", 0)),
                "msg_type": root.findtext("MsgType"),
                "msg_id": root.findtext("MsgId"),
                "content": root.findtext("Content"),
                "event": root.findtext("Event"),
            }
            
            logger.info(f"Parsed WeChat message from {message['from_user']}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to parse WeChat message: {e}")
            return None
    
    def create_response(self, from_user: str, to_user: str, content: str) -> str:
        """创建微信回复消息（XML格式）"""
        from datetime import datetime
        
        create_time = int(datetime.now().timestamp())
        
        response_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
        
        return response_xml
    
    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """验证微信签名"""
        import hashlib
        
        data = sorted([self.token, timestamp, nonce])
        data_str = "".join(data)
        hash_obj = hashlib.sha1(data_str.encode("utf-8"))
        computed_signature = hash_obj.hexdigest()
        
        return computed_signature == signature

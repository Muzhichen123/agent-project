import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from langchain_core.chat_history import BaseChatMessageHistory
import json
import redis
from typing import List
from utils.config_handler import agent_config
from utils.logger import logger

class RedisChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, ttl: int = None):
        """
        初始化Redis聊天历史
        
        Args:
            session_id: 会话ID，用于区分不同用户的对话
            ttl: 消息过期时间（秒），默认从配置读取
        """
        self.session_id = session_id
        self.ttl = ttl if ttl is not None else agent_config["redis"]["ttl"]
        
        # 从配置读取Redis连接参数
        redis_config = agent_config["redis"]
        try:
            self.redis = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                db=redis_config["db"],
                decode_responses=False,
                socket_timeout=5
            )
            # 测试连接
            self.redis.ping()
            logger.info(f"Redis连接成功: {redis_config['host']}:{redis_config['port']}")
        except redis.ConnectionError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    @property
    def messages(self) -> List[BaseMessage]:
        """返回消息列表"""
        try:
            messages_data = self.redis.get(self.session_id)
            if messages_data is None:
                return []
            return messages_from_dict(json.loads(messages_data))
        except Exception as e:
            logger.error(f"获取消息历史失败: {e}")
            return []
        
    def add_message(self, message: BaseMessage) -> None:
        """添加消息到历史记录"""
        try:
            msg_list = list(self.messages)
            msg_list.append(message)
            data = json.dumps([message_to_dict(m) for m in msg_list], ensure_ascii=False)
            self.redis.setex(self.session_id, self.ttl, data)
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
        
    def clear(self) -> None:
        """清除历史记录"""
        try:
            self.redis.delete(self.session_id)
        except Exception as e:
            logger.error(f"清除消息失败: {e}")
    
def get_history(session_id: str, ttl: int = None) -> BaseChatMessageHistory:
    """
    获取历史记录对象
    
    Args:
        session_id: 会话ID
        ttl: 可选，覆盖默认过期时间
        
    Returns:
        RedisChatMessageHistory实例
    """
    return RedisChatMessageHistory(session_id, ttl)
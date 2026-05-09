import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 全局配置 API KEY
os.environ["DASHSCOPE_API_KEY"] = "sk-e72ff2d5100f41068515d0ee06e63eac"

from abc import ABC, abstractmethod
from typing import Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings

# ✅ 官方稳定版，永不报错
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from utils.config_handler import rag_config

# 模型工厂基类
class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseLanguageModel]:
        pass

# 聊天模型工厂
class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[BaseLanguageModel]:
        return ChatTongyi(
            model_name=rag_config["chat_model_name"],
            temperature=0.1
        )

# 向量嵌入模型工厂
class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings]:
        return DashScopeEmbeddings(
            model=rag_config["embedding_model_name"]
        )

# 实例化
chat_model = ChatModelFactory().generator()
embedding_model = EmbeddingsFactory().generator()
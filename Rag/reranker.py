"""
Rerank 精排模块
使用本地 BGE Cross-Encoder 对粗排结果做交叉编码器精排
失败时自动回退粗排，不影响主流程
"""
import os as _os

# 必须在 import sentence_transformers 前设置，否则镜像不生效
_os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from typing import List
from langchain_core.documents import Document
from utils.config_handler import rag_config
from utils.logger import logger


class RerankerService:
    def __init__(self):
        cfg = rag_config.get("rerank", {})
        self.enabled = cfg.get("enabled", False)
        self.top_n = cfg.get("top_n", 3)
        self.score_threshold = cfg.get("score_threshold", 0.0)
        self._model = None
        self._model_name = cfg.get("model_name", "BAAI/bge-reranker-base")

    def _load_model(self):
        """延迟加载：本地缓存 → 镜像下载 → 回退"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            # 优先本地缓存
            try:
                self._model = CrossEncoder(self._model_name, local_files_only=True)
            except Exception:
                # 本地没有，走国内镜像下载
                self._model = CrossEncoder(self._model_name)
            logger.info(f"[Rerank] 模型加载成功: {self._model_name}")
        except Exception as e:
            logger.error(f"[Rerank] 模型加载失败: {e}")
            self.enabled = False

    def rerank(self, query: str, docs: List[Document]) -> List[Document]:
        """
        对粗排文档做精排，返回 top_n 条
        """
        if not self.enabled or not docs:
            return docs[:self.top_n]

        self._load_model()
        if self._model is None:
            return docs[:self.top_n]

        try:
            pairs = [(query, doc.page_content) for doc in docs]
            scores = self._model.predict(pairs)

            for doc, score in zip(docs, scores):
                doc.metadata["rerank_score"] = round(float(score), 4)

            scored = [(doc, s) for doc, s in zip(docs, scores) if s >= self.score_threshold]
            scored.sort(key=lambda x: x[1], reverse=True)

            reranked = [doc for doc, _ in scored[:self.top_n]]
            logger.info(f"[Rerank] {len(docs)}条粗排 → {len(reranked)}条精排, "
                        f"threshold={self.score_threshold}, top_n={self.top_n}")
            return reranked if reranked else docs[:self.top_n]

        except Exception as e:
            logger.error(f"[Rerank] 精排失败，回退粗排 top_{self.top_n}: {e}")
            return docs[:self.top_n]

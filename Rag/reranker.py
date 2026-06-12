"""
Rerank 精排模块
优先 BGE Cross-Encoder，失败降级 TF-IDF
"""
from typing import List
from langchain_core.documents import Document
from utils.config_handler import rag_config
from utils.logger import logger

# 全局单例
_model = None


def _load_bge():
    """尝试加载 BGE，失败返回 None"""
    global _model
    if _model is not None:
        return
    from sentence_transformers import CrossEncoder
    name = rag_config.get("rerank", {}).get("model_name", "BAAI/bge-reranker-v2-m3")
    try:
        _model = CrossEncoder(name, local_files_only=True)
        logger.info(f"[Rerank] BGE 模型加载成功: {name}")
    except Exception:
        try:
            _model = CrossEncoder(name)
            logger.info(f"[Rerank] BGE 模型下载成功: {name}")
        except Exception as e:
            logger.warning(f"[Rerank] BGE 加载失败({e})，降级 TF-IDF")
            _model = False


def _tfidf_scores(query: str, docs: List[Document]) -> List[float]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    texts = [query] + [d.page_content for d in docs]
    vec = TfidfVectorizer().fit_transform(texts)
    return cosine_similarity(vec[0:1], vec[1:]).flatten().tolist()


class RerankerService:
    def __init__(self):
        cfg = rag_config.get("rerank", {})
        self.enabled = cfg.get("enabled", False)
        self.top_n = cfg.get("top_n", 3)
        self.score_threshold = cfg.get("score_threshold", 0.0)

    def rerank(self, query: str, docs: List[Document]) -> List[Document]:
        if not self.enabled or not docs:
            return docs[:self.top_n]

        try:
            _load_bge()

            if _model and _model is not False:
                pairs = [(query, d.page_content) for d in docs]
                scores = [float(s) for s in _model.predict(pairs)]
                tag = "BGE"
            else:
                scores = _tfidf_scores(query, docs)
                tag = "TF-IDF"

            for doc, score in zip(docs, scores):
                doc.metadata["rerank_score"] = round(float(score), 4)

            scored = [(d, s) for d, s in zip(docs, scores) if s >= self.score_threshold]
            scored.sort(key=lambda x: x[1], reverse=True)
            reranked = [d for d, _ in scored[:self.top_n]]
            logger.info(f"[Rerank] {len(docs)}条粗排 → {len(reranked)}条精排 ({tag})")
            return reranked if reranked else docs[:self.top_n]

        except Exception as e:
            logger.error(f"[Rerank] 失败回退 top_{self.top_n}: {e}")
            return docs[:self.top_n]

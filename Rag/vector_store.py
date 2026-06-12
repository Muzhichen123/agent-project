import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from langchain_chroma import Chroma
from utils.config_handler import chroma_config
from model.factory import embedding_model
from utils.path_tool import get_abs_path
from langchain_core.documents import Document
from typing import List
import hashlib


class VectorStoreService:
    """向量数据库服务类（Dense + BM25 混合检索）"""

    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_config["collection_name"],
            embedding_function=embedding_model,
            persist_directory=chroma_config["persist_directory"]
        )

        # 分块参数（splitter 惰性创建，避免 import 链）
        self._chunk_size = chroma_config.get("chunk_size", 200)
        self._chunk_overlap = chroma_config.get("chunk_overlap", 20)
        self._separators = chroma_config.get("separator", ["\n\n", "\n", ".", "?", "。", "！", " "])

        # ---- BM25 混合检索初始化 ----
        hybrid_cfg = chroma_config.get("hybrid_search", {})
        self.hybrid_enabled = hybrid_cfg.get("enabled", False)
        self.bm25_store = None
        self._rrf_k = hybrid_cfg.get("rrf_k", 60)
        self._dense_top_k = hybrid_cfg.get("dense_top_k", 8)
        self._bm25_top_k = hybrid_cfg.get("bm25_top_k", 8)
        self._final_top_k = hybrid_cfg.get("final_top_k", 8)

        if self.hybrid_enabled:
            from Rag.bm25_store import BM25Store
            self.bm25_store = BM25Store()
            # 优先加载已有索引；不存在则从 ChromaDB 取出全量文档构建
            if not self.bm25_store.load():
                logger.info("[混合检索] BM25 索引不存在，从 ChromaDB 同步构建...")
                chroma_docs = self._get_all_chroma_docs()
                if chroma_docs:
                    self.bm25_store.build_from_docs(chroma_docs)
                    self.bm25_store.save()
                else:
                    logger.warning("[混合检索] ChromaDB 暂无文档，BM25 将在 load_documents 时构建")

    # ------------------------------------------------------------------
    # 获取 ChromaDB 中全部文档
    # ------------------------------------------------------------------
    def _get_all_chroma_docs(self) -> List[Document]:
        """从 ChromaDB 取出全量已存储的文档"""
        try:
            data = self.vector_store.get()
            docs = []
            if data and data.get("documents"):
                for content, meta in zip(data["documents"], data["metadatas"] or []):
                    if content:
                        docs.append(Document(page_content=content, metadata=meta or {}))
            return docs
        except Exception as e:
            logger.error(f"[混合检索] 从 ChromaDB 获取全量文档失败: {e}")
            return []

    # ------------------------------------------------------------------
    # 单路 Dense 检索器（兼容旧逻辑）
    # ------------------------------------------------------------------
    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_config["k"]})

    # ------------------------------------------------------------------
    # 加载知识库文档
    # ------------------------------------------------------------------
    def load_documents(self):
        # 惰性导入，避免模块级 import 触发 torchvision 崩溃链
        from utils.file_reader import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
        from Rag.bm25_store import _simple_split_text

        def check_md5_hex(md5_for_check: str):
            md5_file = get_abs_path(chroma_config["md5_hex_store"])
            if not os.path.exists(md5_file):
                open(md5_file, "w", encoding="utf-8").close()
                return False
            with open(md5_file, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.strip() == md5_for_check:
                        return True
            return False

        def save_md5_hex(md5_for_check):
            md5_file = get_abs_path(chroma_config["md5_hex_store"])
            with open(md5_file, "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(file_path: str) -> list[Document]:
            if file_path.endswith(".pdf"):
                return pdf_loader(file_path)
            elif file_path.endswith(".txt"):
                return txt_loader(file_path)
            else:
                return []

        allowed_file_path = listdir_with_allowed_type(
            chroma_config["data_path"],
            tuple(chroma_config["allow_knowledge_file_type"])
        )

        has_new_docs = False
        for read_path in allowed_file_path:
            md5_hex = get_file_md5_hex(read_path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{read_path} 已存在，跳过")
                continue

            try:
                documents = get_file_documents(read_path)
                if not documents:
                    logger.warning(f"[加载知识库]{read_path} 为空，跳过")
                    continue

                # 用 _simple_split_text 替代 RecursiveCharacterTextSplitter
                split_documents: List[Document] = []
                for doc in documents:
                    chunks = _simple_split_text(
                        doc.page_content,
                        self._chunk_size,
                        self._chunk_overlap,
                        self._separators,
                    )
                    for chunk in chunks:
                        split_documents.append(Document(
                            page_content=chunk,
                            metadata=dict(doc.metadata),
                        ))

                if not split_documents:
                    logger.warning(f"[加载知识库]{read_path} 分割后为空，跳过")
                    continue

                self.vector_store.add_documents(split_documents)
                save_md5_hex(md5_hex)
                has_new_docs = True
                logger.info(f"[加载知识库]{read_path} 加载完成")

            except Exception as e:
                logger.error(f"[加载知识库]{read_path} 加载失败：{str(e)}", exc_info=True)

        # ---- 新增文档后同步 BM25 索引 ----
        if has_new_docs and self.hybrid_enabled and self.bm25_store is not None:
            logger.info("[混合检索] 检测到新文档，重建 BM25 索引...")
            chroma_docs = self._get_all_chroma_docs()
            if chroma_docs:
                self.bm25_store.build_from_docs(chroma_docs)
                self.bm25_store.save()

    # ------------------------------------------------------------------
    # 混合检索：Dense + BM25 → RRF 融合
    # ------------------------------------------------------------------
    @staticmethod
    def _doc_key(doc: Document) -> str:
        """用 page_content 的 MD5 作为文档唯一标识（RRF 去重用）"""
        return hashlib.md5(doc.page_content.encode("utf-8")).hexdigest()

    def hybrid_retrieve(self, query: str) -> List[Document]:
        """
        双路检索 + RRF 融合

        Returns:
            融合后按 RRF 分数降序的 Document 列表
        """
        # 1. Dense 稠密向量检索
        dense_docs = self.vector_store.similarity_search(query, k=self._dense_top_k)
        logger.info(f"[RRF] Dense 检索: {len(dense_docs)} 篇")

        # 2. BM25 稀疏检索
        bm25_docs: List[Document] = []
        if self.bm25_store is not None:
            try:
                bm25_docs = self.bm25_store.search(query, top_k=self._bm25_top_k)
                logger.info(f"[RRF] BM25 检索: {len(bm25_docs)} 篇")
            except Exception as e:
                logger.error(f"[RRF] BM25 检索失败，仅用 Dense 结果: {e}")

        # 3. RRF 融合
        if not bm25_docs:
            logger.warning("[RRF] BM25 无结果，降级为纯 Dense")
            return dense_docs[:self._final_top_k]

        rrf_scores: dict = {}   # doc_key → RRF score
        doc_map: dict = {}      # doc_key → Document

        for rank, doc in enumerate(dense_docs, start=1):
            key = self._doc_key(doc)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (self._rrf_k + rank)
            if key not in doc_map:
                doc_map[key] = doc

        for rank, doc in enumerate(bm25_docs, start=1):
            key = self._doc_key(doc)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (self._rrf_k + rank)
            if key not in doc_map:
                doc_map[key] = doc

        # 按 RRF 分数降序，取 final_top_k
        sorted_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
        fused: List[Document] = []
        for key in sorted_keys[:self._final_top_k]:
            doc = doc_map[key]
            doc.metadata["rrf_score"] = round(rrf_scores[key], 4)
            fused.append(doc)

        logger.info(
            f"[RRF] 融合完成: Dense {len(dense_docs)} + BM25 {len(bm25_docs)}"
            f" → 去重 {len(rrf_scores)} → Top-{len(fused)}"
        )
        return fused

"""
BM25 稀疏向量检索模块
jieba 分词 + rank_bm25 索引 + 本地持久化

注意：本模块刻意不导入 langchain_community / langchain_text_splitters，
避免触发 sentence_transformers → transformers → torchvision 的 import 链崩溃。
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import pickle
import hashlib 
from typing import List, Optional
import jieba
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from utils.config_handler import chroma_config
from utils.logger import logger
from utils.path_tool import get_abs_path


# ------------------------------------------------------------------
# 内联文本分块器（替代 RecursiveCharacterTextSplitter，避免 import 链）
# ------------------------------------------------------------------
def _simple_split_text(
    text: str,
    chunk_size: int = 200,
    chunk_overlap: int = 20,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    按分隔符优先级递归切分文本，行为与 RecursiveCharacterTextSplitter 一致。
    """
    if separators is None:
        separators = ["\n\n", "\n", ".", "?", "。", "！", " "]

    # 选第一个能切开的分隔符
    chosen_sep = None
    for sep in separators:
        if sep in text:
            chosen_sep = sep
            break

    if chosen_sep is None:
        # 无分隔符可切，按 chunk_size 硬切
        chunks = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks

    # 用选中的分隔符切开，递归处理过长的片段
    parts = text.split(chosen_sep)
    chunks: List[str] = []
    buf = ""
    for part in parts:
        candidate = buf + (chosen_sep if buf else "") + part
        if len(candidate) <= chunk_size:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            # 如果单个 part 仍然超长，递归切
            if len(part) > chunk_size:
                chunks.extend(_simple_split_text(part, chunk_size, chunk_overlap, separators))
                buf = ""
            else:
                buf = part
    if buf:
        chunks.append(buf)
    return chunks


# ------------------------------------------------------------------
# 内联文件读取（替代 file_reader，避免 import 链）
# ------------------------------------------------------------------
def _read_txt(file_path: str) -> str:
    """读取 TXT 文件，尝试多种编码"""
    for enc in ("utf-8", "gbk", "gb2312", "utf-8-sig"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    logger.error(f"[BM25] 无法解码文件: {file_path}")
    return ""


def _list_txt_files(folder: str) -> List[str]:
    """列出文件夹下所有 .txt 文件（绝对路径）"""
    files = []
    if not os.path.isdir(folder):
        return files
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(".txt") and not f.startswith("custom_dict"):
            files.append(os.path.join(folder, f))
    return files


def _file_md5(file_path: str) -> str:
    """计算单个文件的 MD5"""
    if not os.path.isfile(file_path):
        return ""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ==================================================================
# BM25Store
# ==================================================================
class BM25Store:
    """
    BM25 关键词检索服务

    负责：
    1. 加载自定义词典 → jieba 分词
    2. 读取 data/ 下 TXT 知识库 → 分块 → 分词 → 构建 BM25Okapi 索引
    3. 持久化到本地 pickle，避免每次重启重建
    4. 检索时返回带 bm25_score 的 Document 列表
    """

    def __init__(self):
        cfg = chroma_config.get("hybrid_search", {})
        self.index_path = get_abs_path(cfg.get("bm25_index_path", "data/bm25_index.pkl"))
        self.custom_dict_path = get_abs_path(cfg.get("custom_dict_path", "data/custom_dict.txt"))
        self.data_path = get_abs_path(chroma_config.get("data_path", "data"))
        self.chunk_size = chroma_config.get("chunk_size", 200)
        self.chunk_overlap = chroma_config.get("chunk_overlap", 20)
        self.separators = chroma_config.get("separator", ["\n\n", "\n", ".", "?", "。", "！", " "])

        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Document] = []
        self._corpus_signature: str = ""

        self._load_custom_dict()

    # ------------------------------------------------------------------
    # 词典
    # ------------------------------------------------------------------
    def _load_custom_dict(self):
        if os.path.exists(self.custom_dict_path):
            jieba.load_userdict(self.custom_dict_path)
            logger.info(f"[BM25] 已加载自定义词典: {self.custom_dict_path}")
        else:
            logger.warning(f"[BM25] 自定义词典不存在: {self.custom_dict_path}")

    # ------------------------------------------------------------------
    # 分词
    # ------------------------------------------------------------------
    def _tokenize(self, text: str) -> List[str]:
        return [w for w in jieba.cut(text) if w.strip()]

    # ------------------------------------------------------------------
    # 知识库指纹
    # ------------------------------------------------------------------
    def _compute_corpus_signature(self) -> str:
        files = _list_txt_files(self.data_path)
        if not files:
            return ""
        h = hashlib.md5()
        for fp in files:
            md5 = _file_md5(fp)
            if md5:
                h.update(md5.encode())
        return h.hexdigest()

    # ------------------------------------------------------------------
    # 构建索引（从文件独立构建）
    # ------------------------------------------------------------------
    def build_index(self, force: bool = False):
        if not force and self.load():
            return

        logger.info("[BM25] 开始构建索引...")

        files = _list_txt_files(self.data_path)
        if not files:
            logger.warning("[BM25] data/ 下无有效 TXT 文件，跳过构建")
            return

        # 读取并分块
        all_chunks: List[Document] = []
        for fp in files:
            content = _read_txt(fp)
            if not content:
                continue
            chunks = _simple_split_text(content, self.chunk_size, self.chunk_overlap, self.separators)
            fname = os.path.basename(fp)
            for i, chunk in enumerate(chunks):
                all_chunks.append(Document(
                    page_content=chunk,
                    metadata={"source": fname, "chunk_index": i},
                ))

        if not all_chunks:
            logger.warning("[BM25] 分块后文档为空，跳过构建")
            return

        # 构建 BM25Okapi
        tokenized = [self._tokenize(d.page_content) for d in all_chunks]
        self.bm25 = BM25Okapi(tokenized)
        self.documents = all_chunks
        self._corpus_signature = self._compute_corpus_signature()

        logger.info(f"[BM25] 索引构建完成: {len(all_chunks)} 条文档（{len(files)} 个源文件）")

    # ------------------------------------------------------------------
    # 从外部文档构建索引（与 ChromaDB 同源，保证 RRF 去重一致）
    # ------------------------------------------------------------------
    def build_from_docs(self, documents: List[Document]):
        """
        用已分块的 Document 列表直接构建 BM25 索引。
        文档来自 ChromaDB，保证两路检索的分块完全一致。
        """
        if not documents:
            logger.warning("[BM25] build_from_docs: 文档列表为空，跳过")
            return

        tokenized = [self._tokenize(d.page_content) for d in documents]
        self.bm25 = BM25Okapi(tokenized)
        self.documents = documents
        self._corpus_signature = self._compute_corpus_signature()

        logger.info(f"[BM25] 从 ChromaDB 文档构建索引: {len(documents)} 条")

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def save(self):
        if self.bm25 is None:
            logger.warning("[BM25] 无索引可保存")
            return
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        payload = {
            "tokenized": [self._tokenize(d.page_content) for d in self.documents],
            "documents": self.documents,
            "signature": self._corpus_signature,
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(payload, f)
        logger.info(f"[BM25] 索引已保存: {self.index_path}")

    def load(self) -> bool:
        if not os.path.exists(self.index_path):
            logger.info("[BM25] 索引文件不存在，需构建")
            return False

        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)

            saved_sig = data.get("signature", "")
            current_sig = self._compute_corpus_signature()
            if saved_sig and current_sig and saved_sig != current_sig:
                logger.info("[BM25] 知识库已变动，索引失效，需重建")
                return False

            self.documents = data["documents"]
            self.bm25 = BM25Okapi(data["tokenized"])
            self._corpus_signature = current_sig
            logger.info(f"[BM25] 索引已加载: {len(self.documents)} 条文档")
            return True
        except Exception as e:
            logger.error(f"[BM25] 加载索引失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> List[Document]:
        if self.bm25 is None:
            logger.error("[BM25] 索引未就绪，请先调用 build_index() / ensure_index()")
            return []

        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)

        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top_indices = [i for i, _ in indexed[:top_k]]

        results: List[Document] = []
        for rank, idx in enumerate(top_indices, start=1):
            src = self.documents[idx]
            doc = Document(
                page_content=src.page_content,
                metadata=dict(src.metadata),
            )
            doc.metadata["bm25_score"] = round(float(scores[idx]), 4)
            doc.metadata["bm25_rank"] = rank
            results.append(doc)

        return results

    # ------------------------------------------------------------------
    # 快捷入口
    # ------------------------------------------------------------------
    def ensure_index(self) -> bool:
        if self.load():
            return True
        self.build_index()
        if self.bm25 is not None:
            self.save()
            return True
        return False



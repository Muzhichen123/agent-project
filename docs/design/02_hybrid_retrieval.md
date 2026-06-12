# 模块 2: 混合检索（稀疏向量 + 稠密向量 + RRF 融合）

## 2.1 目标

在现有稠密向量检索的基础上，增加 BM25 稀疏向量检索，通过 RRF（Reciprocal Rank Fusion）算法融合两路检索结果，提升整体召回质量。

## 2.2 当前架构

**文件**: `Rag/vector_store.py`

```
用户 Query
  → ChromaDB (Dense Embedding: text-embedding-v4)
  → similarity_search top-k=3
  → 返回结果
```

**问题**:
- 只有稠密向量，擅长语义匹配但弱于精确关键词匹配
- 客服场景中用户经常搜索具体型号名、故障码（如 "X900"、"E03"），纯稠密检索容易匹配到语义相近但信息不对的文档
- top-k=3 太小，容易遗漏相关文档

## 2.3 目标架构

```
用户 Query
  ├─→ ChromaDB Dense 向量检索 (top-k=10)
  └─→ BM25 稀疏检索 (top-k=10)
       ↓
  RRF 融合排序 (k=60)
       ↓
  精排后 top-k=8（后续交给 Rerank 模块精排到 top-3）
       ↓
  返回结果
```

## 2.4 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 稠密向量 | 现有 ChromaDB + text-embedding-v4 | 不变，已经跑通 |
| 稀疏向量 | rank_bm25 (纯 Python) | 轻量，无需额外基础设施；后续可升级到 Elasticsearch |
| 中文分词 | jieba | 成熟稳定，支持自定义词典 |
| 融合算法 | RRF (k=60) | 行业标准，简单有效 |

## 2.5 配置变更

### `config/chroma.yml` 修改

```yaml
collection_name: agent
k: 10                     # 原来 3，改为 10（粗排扩大召回）
persist_directory: ./chroma_db
data_path: data
md5_hex_store: md5.txt
allow_knowledge_file_type: ["pdf", "docx", "txt"]

chunk_size: 200
chunk_overlap: 20
separator: ["\n\n", "\n", ".", "?", "。", "！", " "]

# ===== 新增: 混合检索配置 =====
hybrid_search:
  enabled: true
  bm25_top_k: 10           # BM25 粗排返回数量
  dense_top_k: 10          # Dense 粗排返回数量
  rrf_k: 60                # RRF 平滑常数
  final_top_k: 8           # RRF 融合后保留数量（给 Rerank 模块用）
  # 自定义词典（专业术语，jieba 默认词库可能切不好）
  custom_dict_path: data/custom_dict.txt
  # BM25 索引持久化路径
  bm25_index_path: ./bm25_index.pkl
```

## 2.6 自定义词典

### 新建 `data/custom_dict.txt`

jieba 的自定义词典格式（每行: 词语 词频 词性）:

```
扫拖一体机 100 n
扫地机器人 100 n
滚刷 50 n
边刷 50 n
集尘盒 50 n
激光导航 50 n
视觉导航 50 n
路径规划 50 n
越障能力 50 n
吸力调节 50 n
拖布 50 n
水箱 50 n
基站 50 n
自动集尘 50 n
自动清洗 50 n
故障码 50 n
E03 100 n
E05 100 n
X900 100 n
X950 100 n
Pro 50 n
Max 50 n
Plus 50 n
续航时间 50 n
充电座 50 n
APP控制 50 n
地图记忆 50 n
禁区设置 50 n
```

> **注意**: 上述词典内容是初始版本，实际使用时需要根据知识库内容补充更多型号名和术语。

## 2.7 代码改动

### 2.7.1 新建 `Rag/bm25_store.py`

```python
"""
BM25 稀疏向量检索模块
使用 jieba 分词 + rank_bm25 实现本地 BM25 索引
"""
import os
import pickle
import jieba
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from typing import List, Tuple
from utils.logger import logger
from utils.config_handler import chroma_config
from utils.path_tool import get_abs_path


class BM25Store:
    """BM25 稀疏向量索引"""

    def __init__(self):
        hybrid_config = chroma_config.get("hybrid_search", {})
        self.top_k = hybrid_config.get("bm25_top_k", 10)
        self.bm25_index_path = get_abs_path(hybrid_config.get("bm25_index_path", "./bm25_index.pkl"))

        # 加载自定义词典
        custom_dict_path = hybrid_config.get("custom_dict_path")
        if custom_dict_path:
            dict_path = get_abs_path(custom_dict_path)
            if os.path.exists(dict_path):
                jieba.load_userdict(dict_path)
                logger.info(f"[BM25] 已加载自定义词典: {dict_path}")

        self.bm25 = None
        self.documents = None  # type: List[Document] | None
        self.tokenized_corpus = None  # type: List[List[str]] | None

        # 尝试加载已有索引
        self._load_index()

    def tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))

    def build_index(self, documents: List[Document]):
        """
        构建 BM25 索引

        Args:
            documents: 与 ChromaDB 相同的文档列表（经过 chunk 分割后的）
        """
        self.documents = documents
        self.tokenized_corpus = [self.tokenize(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        self._save_index()
        logger.info(f"[BM25] 索引构建完成，共 {len(documents)} 篇文档")

    def search(self, query: str, top_k: int = None) -> List[Tuple[Document, float]]:
        """
        BM25 检索

        Args:
            query: 用户查询
            top_k: 返回数量（默认使用配置值）

        Returns:
            (Document, score) 元组列表，按分数降序
        """
        if self.bm25 is None:
            logger.warning("[BM25] 索引未构建")
            return []

        k = top_k or self.top_k
        tokenized_query = self.tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # 获取 top-k 索引
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 过滤分数为 0 的
                results.append((self.documents[idx], float(scores[idx])))

        return results

    def _save_index(self):
        """持久化 BM25 索引到本地文件"""
        if self.bm25 is None:
            return
        try:
            data = {
                "documents": [(doc.page_content, doc.metadata) for doc in self.documents],
                "tokenized_corpus": self.tokenized_corpus,
            }
            with open(self.bm25_index_path, "wb") as f:
                pickle.dump(data, f)
            logger.info(f"[BM25] 索引已保存到: {self.bm25_index_path}")
        except Exception as e:
            logger.error(f"[BM25] 索引保存失败: {e}")

    def _load_index(self):
        """从本地文件加载 BM25 索引"""
        if not os.path.exists(self.bm25_index_path):
            logger.info("[BM25] 无已有索引文件，将在知识库加载后构建")
            return
        try:
            with open(self.bm25_index_path, "rb") as f:
                data = pickle.load(f)
            self.documents = [
                Document(page_content=d[0], metadata=d[1]) for d in data["documents"]
            ]
            self.tokenized_corpus = data["tokenized_corpus"]
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"[BM25] 索引加载成功，共 {len(self.documents)} 篇文档")
        except Exception as e:
            logger.error(f"[BM25] 索引加载失败: {e}")
```

### 2.7.2 修改 `Rag/vector_store.py` — 索引同步

在 `load_documents` 方法末尾，同步构建/更新 BM25 索引:

```python
# 在 VectorStoreService.__init__ 中初始化 BM25
from Rag.bm25_store import BM25Store

class VectorStoreService:
    def __init__(self):
        # ... 原有代码不变 ...

        # ===== 新增: BM25 索引 =====
        hybrid_config = chroma_config.get("hybrid_search", {})
        if hybrid_config.get("enabled", False):
            self.bm25_store = BM25Store()
        else:
            self.bm25_store = None
        # ===== 新增结束 =====

    def load_documents(self):
        # ... 原有的 load_documents 逻辑全部保留 ...

        # ===== 新增: 在 ChromaDB 加载完成后，同步构建 BM25 索引 =====
        # 注意：这里要在所有文件处理完后统一构建，而不是每个文件处理一次
        if self.bm25_store and self.bm25_store.bm25 is None:
            # 从 ChromaDB 取出所有已有文档来构建 BM25 索引
            all_docs = self.vector_store.get()  # ChromaDB 获取全部文档
            if all_docs and all_docs.get("documents"):
                split_docs = all_docs["documents"]
                if len(split_docs) > 0:
                    self.bm25_store.build_index(split_docs)
                    logger.info(f"[混合检索] BM25 索引构建完成，共 {len(split_docs)} 篇")
        # ===== 新增结束 =====
```

> **实现注意**: ChromaDB 的 `get()` 方法返回格式需要确认。Claude Code 实现时请检查 ChromaDB 的 API，正确获取全部 documents。如果 `get()` 不方便，也可以在 `load_documents` 中收集所有 `split_documents`，最后统一构建 BM25。

### 2.7.3 修改 `Rag/rag_service.py` — RRF 融合

```python
from Rag.bm25_store import BM25Store
import math

class RagSummaryService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()

        # ===== 新增: 混合检索配置 =====
        hybrid_config = chroma_config.get("hybrid_search", {})
        self.hybrid_enabled = hybrid_config.get("enabled", False)
        self.rrf_k = hybrid_config.get("rrf_k", 60)
        self.final_top_k = hybrid_config.get("final_top_k", 8)
        # ===== 新增结束 =====

        # Reranker（模块 1 的内容，如果已实现的话）
        rerank_config = rag_config.get("rerank", {})
        self.reranker = DashScopeReranker() if rerank_config.get("enabled", False) else None

        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self.__init__chain()

    def retriever_docs(self, query: str) -> List[Document]:
        """
        混合检索: Dense + BM25 + RRF 融合
        """
        if not self.hybrid_enabled:
            # 未开启混合检索，走原有逻辑
            return self.retriever.invoke(query)

        # 第一步: Dense 向量检索
        dense_docs = self.retriever.invoke(query)

        # 第二步: BM25 检索
        bm25_results = self.vector_store.bm25_store.search(query)

        # 第三步: RRF 融合
        return self._rrf_fusion(query, dense_docs, bm25_results)

    def _rrf_fusion(
        self,
        query: str,
        dense_docs: List[Document],
        bm25_results: List[Tuple[Document, float]]
    ) -> List[Document]:
        """
        RRF (Reciprocal Rank Fusion) 融合两路检索结果

        RRF_score(d) = Σ 1/(k + rank_i(d))
        """
        rrf_scores = {}  # {doc_id: score}

        # 第一路: Dense 向量排名
        for rank, doc in enumerate(dense_docs, start=1):
            doc_id = doc.page_content[:50]  # 用内容前 50 字作为唯一标识
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (self.rrf_k + rank)
            # 同时保存文档引用
            if doc_id not in getattr(self, '_doc_cache', {}):
                if not hasattr(self, '_doc_cache'):
                    self._doc_cache = {}
                self._doc_cache[doc_id] = doc

        # 第二路: BM25 排名
        for rank, (doc, score) in enumerate(bm25_results, start=1):
            doc_id = doc.page_content[:50]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (self.rrf_k + rank)
            if doc_id not in getattr(self, '_doc_cache', {}):
                if not hasattr(self, '_doc_cache'):
                    self._doc_cache = {}
                self._doc_cache[doc_id] = doc

        # 按 RRF 分数降序排列，取 top-k
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:self.final_top_k]

        results = []
        for doc_id, score in sorted_ids:
            doc = self._doc_cache.get(doc_id)
            if doc:
                doc.metadata["rrf_score"] = score
                results.append(doc)

        logger.info(
            f"[RRF] Dense: {len(dense_docs)} 篇, BM25: {len(bm25_results)} 篇, "
            f"融合后: {len(results)} 篇"
        )
        return results
```

> **实现注意**: 上述代码用 `doc.page_content[:50]` 作为文档唯一标识有碰撞风险。Claude Code 实现时建议改用更可靠的方式（如 ChromaDB 返回的 `doc.metadata` 中是否有 id 字段，或者在构建索引时给每个 chunk 分配唯一 ID）。

## 2.8 依赖变更

### `requirements.txt` 新增

```
rank-bm25>=0.2.2
jieba>=0.42.1
```

## 2.9 索引管理策略

| 场景 | 处理方式 |
|------|---------|
| 首次启动 | ChromaDB 加载文档后，自动构建 BM25 索引并持久化到 `bm25_index.pkl` |
| 文档更新 | 检测到 MD5 变化 → ChromaDB 新增文档 → 重建 BM25 索引（全量重建，简单可靠） |
| 已有索引 | 直接从 `bm25_index.pkl` 加载，跳过构建 |
| 索引损坏 | 删除 `bm25_index.pkl`，下次启动自动重建 |

> **注意**: 当前项目的知识库规模较小（6 个 TXT 文件），全量重建 BM25 索引的性能可以接受。如果后续知识库扩大到数百个文件，需要改为增量更新。

## 2.10 测试方案

### 单元测试

```python
# 测试 BM25 分词效果
from Rag.bm25_store import BM25Store
bm25 = BM25Store()
print(bm25.tokenize("X900型号E03故障码怎么处理"))
# 期望: ['X900', '型号', 'E03', '故障码', '怎么', '处理']

# 测试精确匹配（BM25 应该比纯 Dense 更好）
# query: "E03"
# 验证包含 "E03" 的文档是否排在前列
```

### 对比测试

| Query | 预期 | Dense only | Hybrid |
|-------|------|-----------|--------|
| "扫地机器人怎么清理滚刷" | 语义匹配，两路应该差不多 | OK | OK |
| "X900 型号 E03 故障" | 精确匹配，Hybrid 应该更好 | 可能漂移 | 应该命中 |
| "小户型适合哪种" | 语义匹配 | OK | OK |
| "自动集尘功能介绍" | 混合（语义+关键词） | 可能遗漏 | 应该更好 |

## 2.11 后续升级路径

- **短期**: rank_bm25 本地部署（当前方案）
- **中期**: 如果文档量大，迁移到 Elasticsearch 的 BM25 实现，支持分片、分布式
- **长期**: 考虑 SPLADE 等学习型稀疏向量，进一步缩小和稠密向量的语义差距

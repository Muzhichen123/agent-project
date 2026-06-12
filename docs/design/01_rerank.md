# 模块 1: Rerank 精排优化

## 1.1 目标

在 RAG 检索的向量相似度检索（粗排）和 LLM 生成之间，增加一层交叉编码器（Cross-encoder）精排，提升最终喂给 LLM 的参考资料质量。

## 1.2 当前架构

**文件**: `Rag/rag_service.py`

```
用户 Query
  → self.retriever.invoke(query)  # ChromaDB similarity_search, top-k=3
  → 拼接 context 字符串
  → LLM chain 生成回答
```

**问题**:
- ChromaDB 使用双塔模型（bi-encoder），query 和 document 分别编码后算余弦相似度
- top-k=3 太小，可能遗漏高质量文档
- 粗排精度有限，特别是短 query + 长文档场景

## 1.3 目标架构

```
用户 Query
  → ChromaDB similarity_search, top-k=8 (粗排，扩大召回)
  → Rerank 模型精排 top-k=3
  → 拼接 context 字符串
  → LLM chain 生成回答
```

## 1.4 技术选型

**推荐: DashScope GTE-Rerank API**

理由:
- 项目已使用 DashScope（`model/factory.py` 第 13 行已设置 `DASHSCOPE_API_KEY`）
- 无需额外部署模型服务，API 调用即可
- GTE-Rerank 对中文场景效果好

**备选**:
- `bge-reranker-v2-m3` 本地部署（通过 sentence-transformers）
- 需要额外 GPU 资源，适合后续规模化时考虑

## 1.5 配置变更

### `config/rag.yml` 新增字段

```yaml
chat_model_name: qwen3.7-max
embedding_model_name: text-embedding-v4
# ===== 新增 =====
rerank:
  enabled: true
  model_name: gte-rerank  # DashScope rerank 模型名
  top_n: 3                # 精排后保留的文档数
  score_threshold: 0.3     # 最低相关性分数阈值，低于此分的文档直接丢弃
```

### `config/chroma.yml` 修改

```yaml
collection_name: agent
k: 8                      # 原来是 3，改为 8（粗排扩大召回，给 Rerank 更多候选）
persist_directory: ./chroma_db
# ...其余不变
```

## 1.6 代码改动

### 1.6.1 新建 `Rag/reranker.py`

```python
"""
Rerank 精排模块
使用 DashScope GTE-Rerank 对粗排结果进行交叉编码器精排
"""
import os
import json
import requests
from typing import List
from langchain_core.documents import Document
from utils.logger import logger
from utils.config_handler import rag_config

class DashScopeReranker:
    """DashScope GTE-Rerank 精排器"""

    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"

    def __init__(self):
        config = rag_config.get("rerank", {})
        self.model_name = config.get("model_name", "gte-rerank")
        self.top_n = config.get("top_n", 3)
        self.score_threshold = config.get("score_threshold", 0.3)
        self.api_key = os.environ.get("DASHSCOPE_API_KEY", "")

    def rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """
        对文档列表按与 query 的相关性重新排序

        Args:
            query: 用户原始问题
            documents: 粗排返回的文档列表

        Returns:
            精排后的文档列表（top_n 条）
        """
        if not documents:
            return []

        if len(documents) <= self.top_n:
            logger.info(f"[Rerank] 文档数量 {len(documents)} <= top_n {self.top_n}，跳过精排")
            return documents

        try:
            # 构造请求
            passages = [doc.page_content for doc in documents]
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model_name,
                "input": {
                    "query": query,
                    "passages": passages
                },
                "parameters": {
                    "top_n": self.top_n
                }
            }

            response = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
                headers=headers,
                json=payload,
                timeout=10
            )
            result = response.json()

            if result.get("output", {}).get("results"):
                # 按分数排序，取 top_n
                ranked_results = sorted(
                    result["output"]["results"],
                    key=lambda x: x["relevance_score"],
                    reverse=True
                )[:self.top_n]

                # 过滤低分文档
                reranked_docs = []
                for r in ranked_results:
                    if r["relevance_score"] >= self.score_threshold:
                        idx = r["index"]
                        doc = documents[idx]
                        # 在 metadata 中存入 rerank 分数，方便后续追踪
                        doc.metadata["rerank_score"] = r["relevance_score"]
                        reranked_docs.append(doc)

                logger.info(f"[Rerank] {len(documents)} 篇 → 精排后 {len(reranked_docs)} 篇")
                return reranked_docs

            logger.warning("[Rerank] API 返回无结果，回退到粗排")
            return documents[:self.top_n]

        except Exception as e:
            logger.error(f"[Rerank] 精排失败，回退到粗排: {e}")
            return documents[:self.top_n]
```

> **注意**: 上述 DashScope Rerank API 的 endpoint 和参数格式需以官方文档为准。Claude Code 实现时请查阅 https://help.aliyun.com/zh/model-studio/developer-reference/text-rerank-api 确认最新接口。如果 API 格式不同，请按官方文档调整 payload 结构。

### 1.6.2 修改 `Rag/rag_service.py`

改动点仅两处:

**1) `__init__` 方法中初始化 reranker**:

```python
from Rag.reranker import DashScopeReranker

class RagSummaryService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        # ===== 新增: 初始化 Reranker =====
        rerank_config = rag_config.get("rerank", {})
        self.reranker = DashScopeReranker() if rerank_config.get("enabled", False) else None
        # ===== 新增结束 =====
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self.__init__chain()
```

**2) `rag_summary` 方法中插入精排步骤**:

```python
def rag_summary(self, query: str) -> str:
    context_docs = self.retriever_docs(query)  # 粗排 top-k=8

    # ===== 新增: Rerank 精排 =====
    if self.reranker:
        context_docs = self.reranker.rerank(query, context_docs)
    # ===== 新增结束 =====

    context = ""
    counter = 0
    for i in context_docs:
        counter += 1
        context += f"【参考资料{counter}】: 参考资料:{i.page_content}|参考元数据：{i.metadata}\n"
    return self.chain.invoke({"input": query, "context": context})
```

## 1.7 依赖变更

### `requirements.txt`

无需新增依赖（requests 已有，DashScope API 直接 HTTP 调用）。

## 1.8 测试方案

### 单元测试

```python
# 测试脚本 test_rerank.py
from Rag.rag_service import RagSummaryService

# 测试 1: 基本功能
rag = RagSummaryService()
result = rag.rag_summary("扫地机器人怎么清理滚刷")
print(result)

# 测试 2: 精确匹配场景（Rerank 应该有优势）
result2 = rag.rag_summary("X900 型号 E03 故障码怎么处理")
print(result2)

# 测试 3: 关闭 Rerank 时的回退
# 在 config 中设置 rerank.enabled=false，验证回退到原有逻辑
```

### 对比测试

准备 10 个测试 query，分别对比:
- 无 Rerank（top-k=3 直接检索）
- 有 Rerank（top-k=8 粗排 + 精排 top-3）

人工评估返回的参考资料是否更相关。

## 1.9 回退策略

- `config/rag.yml` 中 `rerank.enabled: false` 可随时关闭
- Rerank API 调用失败时自动回退到粗排结果的前 top_n 条
- 不影响现有架构，纯粹是检索管道中插入的一环

# CLAUDE.md — RoboServe 项目开发指南

> 本文件为 AI 编程助手提供项目上下文。Claude Code 进入仓库时会自动读取。

---

## 项目概述

RoboServe 是一个基于 LangChain ReAct Agent 的 RAG 智能问答系统。支持混合检索、Memory 分层管理、A2A 质量评估，可插拔知识库切换领域。

当前 Demo 场景：扫地机器人客服（`data/` 目录下的知识库）。

---

## 技术架构

```
用户输入 → ReAct Agent (react_agent.py)
              │
              ├─ 知识类问题 → RAG 检索工具 (rag_summarize)
              │                  ├─ 混合检索: Dense(BGE) + BM25(jieba)
              │                  ├─ RRF 融合 → 去重
              │                  ├─ BGE Cross-Encoder 精排
              │                  └─ Top-3 文档 → LLM 总结
              │
              ├─ 天气查询 → get_weather (APISpace API)
              ├─ 报告生成 → fill_context_for_report → 动态 Prompt 切换
              ├─ 数据查询 → fetch_external_data (CSV)
              └─ 基础工具 → get_current_date / get_user_location / get_user_id

所有回复 → A2A 评估 Agent (evaluator.py)
              ├─ 四维度打分 (相关性/准确性/安全性/完整性)
              ├─ 不达标 → 重生成 (max 2 次)
              └─ 兜底 → 评估失败默认放行
```

---

## 核心文件速查

| 文件 | 职责 | 关键点 |
|------|------|--------|
| `agent/react_agent.py` | ReAct Agent 主控 | LLM 自主决策 + 工具调用 + 输入过滤 |
| `agent/evaluator.py` | A2A 评估 | 四维度打分 + 重试回路 |
| `agent/input_guard.py` | 输入安全过滤 | 正则拦截 8 类注入/越狱/窃取 |
| `agent/tools/agent_tools.py` | 7 个工具函数 | `@tool` 装饰器注册 |
| `agent/tools/middleware.py` | LangGraph 中间件 | 工具监控 + 动态 Prompt |
| `Rag/vector_store.py` | 向量库 + 混合检索 | ChromaDB + RRF 融合 |
| `Rag/bm25_store.py` | BM25 检索 | jieba 分词 + 自定义词典 |
| `Rag/reranker.py` | 精排 + 降级 | BGE → TF-IDF → 取前 N |
| `Rag/rag_service.py` | RAG 完整流程 | 编排检索 → 总结 |
| `utils/memory_manager.py` | 四层 Memory | 短期/摘要/画像/工作 |
| `utils/app_history.py` | Redis 会话 | TTL 30 天 |
| `utils/app_web.py` | Streamlit 前端 | 入口文件 |
| `utils/api.py` | FastAPI 接口 | RESTful API |
| `model/factory.py` | 模型工厂 | LLM + Embedding 统一管理 |

---

## 开发约定

### 语言与环境
- Python 3.12，依赖在 `requirements.txt`
- 所有依赖用 pip 安装，不使用 conda

### 配置管理
- 配置文件统一在 `config/` 目录，YAML 格式
- `config/agent.yml` 含所有 API Key + 评估配置，不提交 Git（已在 `.gitignore`）
- 提供 `config/agent.example.yml` 作为模板
- 评估配置已合并到 `agent.yml` 中，`config/evaluator.yml` 已废弃删除
- 通过 `utils/config_handler.py` 统一加载

### 模块设计原则
- **延迟加载**：重型依赖（sentence_transformers、torch）只在需要时才 import
- **开关设计**：每个模块在 YAML 配置中有独立 `enabled` 字段
- **三级降级**：优先方案失败自动降级（BGE → TF-IDF → 取前 N）

### LLM 选型
- 主对话：通义千问 (qwen-plus / qwen-max)，通过 DashScope API
- 评估：硅基流动免费模型 (Qwen2.5-14B-Instruct)
- Embedding：DashScope text-embedding-v4

### 日志规范
- 使用 `utils/logger.py` 统一日志
- 格式：`%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s`
- 日志文件在 `logs/` 目录（不提交 Git）

---

## 运行方式

```bash
# Web 界面
streamlit run utils/app_web.py

# API 服务
uvicorn utils.api:app --reload

# 单次测试
python -c "
from Rag.rag_service import RAGService
rag = RAGService()
print(rag.rag_summary('扫地机器人边刷不转怎么办'))
"
```

### 前置条件
- Redis 运行在 localhost:6379
- `config/agent.yml` 已配置（含 API Key）

---

## 注意事项

### 依赖链问题
`sentence-transformers` 间接依赖 `torch`（~2GB），启动慢。解决方案：延迟加载，只在 `reranker.py` 首次调用 `rerank()` 时才 `import`。不要在模块顶层 `import sentence_transformers`。

### 评估模型
硅基流动 14B 模型是免费额度，可能有调用限制。评估兜底策略：调用失败默认放行（`pass_on_error=True`）。

### 知识库切换
换领域只需替换 `data/` 目录下的 `.txt` 文件，然后重新构建索引：
```python
from Rag.vector_store import VectorStore
VectorStore().build_index('data/')
from Rag.bm25_store import BM25Store
BM25Store().build_index('data/')
```

### Git 提交注意
- `config/agent.yml` 不要提交（含密钥）
- `chroma_db/` 不要提交（向量库缓存）
- `logs/` 不要提交（运行日志）
- `*.pkl` 不要提交（BM25 缓存）

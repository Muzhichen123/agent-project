# 🤖 RoboServe

> 基于 RAG + ReAct Agent 的智能问答系统 — 支持混合检索、Memory 分层管理、A2A 质量评估、Prompt 注入防御的开源客服框架

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1.0+-green.svg)](https://www.langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 💡 一句话

一个即插即用的智能问答框架：换上你的知识库，配合 ReAct Agent 自主决策 + 混合检索 + 质量评估 + Prompt 注入防御，就能跑起一个生产可用的客服系统。

当前 Demo 场景：**扫地机器人智能客服**（知识库 119 条文档），换 `data/` 目录即可切换领域。

---

## 🏗️ 系统架构

```
用户提问
  │
  ▼
┌──────────────┐
│  输入安全过滤  │  ← 正则拦截注入/越狱/密钥窃取
└──────┬───────┘
  │ 放行
  ▼
┌─────────────────────────────────────────────────────┐
│  ReAct Agent (LangChain)                             │
│  LLM 自主决策 → 思考 → 工具调用 → 观察 → 再思考      │
│                                                      │
│  ┌──────────┬──────────┬──────────┬──────────┐      │
│  │ RAG 检索 │ 天气查询 │ 报告生成 │ 数据读取  │ ...  │
│  │          │          │          │          │  7个  │
│  └────┬─────┴──────────┴──────────┴──────────┘      │
│       │                                               │
│       ▼                                               │
│  ┌─────────────────────────────────────────┐        │
│  │         混合检索链路 (四阶段)              │        │
│  │                                         │        │
│  │  ① Dense 向量检索 (ChromaDB)            │        │
│  │  ② BM25 关键词检索 (jieba 分词)         │        │
│  │  ③ RRF 融合去重                         │        │
│  │  ④ Cross-Encoder 精排 (BGE)             │        │
│  │                                         │        │
│  │  降级策略: BGE → TF-IDF → 直接取 Top-N  │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
│  ┌─────────────────────────────────────────┐        │
│  │  Memory 分层管理                          │        │
│  │  短期记忆 / 对话摘要 / 用户画像 / 工作记忆  │        │
│  │  持久化: Redis (TTL 30天)                │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
│  ┌─────────────────────────────────────────┐        │
│  │  A2A 评估 Agent (质量把关)                │        │
│  │  四维度打分 → 不达标 → 自动重生成 + 兜底  │        │
│  └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
  │
  ▼
Streamlit Web UI / FastAPI
```

---

## ✨ 核心亮点

| 模块 | 做了什么 | 解决什么问题 |
|------|---------|-------------|
| **混合检索** | Dense 向量 + BM25 关键词 + RRF 融合 + BGE 精排 | 语义匹配和关键词匹配互补，提升召回质量 |
| **Memory 分层** | 四层记忆（短期/摘要/画像/工作）替代全量历史 | 长对话 token 不爆炸，跨会话记用户偏好 |
| **A2A 评估** | 独立 Agent 四维度打分 + 不达标自动重试 | 回复质量有兜底，减少幻觉 |
| **动态 Prompt** | 中间件检测意图 → 自动切换对话/报告模板 | 一个 Agent 同时处理多场景 |
| **Prompt 注入防御** | 三层防线：输入过滤 → 系统指令固守 → 评估检测 | 防越狱/密钥泄露/角色扮演劫持 |
| **三级降级** | BGE → TF-IDF → 取前 N | 模型加载失败不影响服务 |
| **模块化开关** | 每个模块 YAML 配置独立开关 | 按需启停，方便调试和 A/B 测试 |

---

## 🛠️ 技术栈

```
核心框架    LangChain + LangGraph (ReAct Agent)
LLM        通义千问 (qwen3.7-max/qwen-plus)
Embedding  DashScope text-embedding-v4
向量库     ChromaDB
关键词检索  BM25 (rank_bm25 + jieba 分词)
精排模型    BGE Cross-Encoder (bge-reranker-base)
会话存储    Redis (TTL 30 天)
评估模型    硅基流动 (Qwen2.5-14B-Instruct)
输入安全    正则过滤 + 系统 Prompt 固守 + 评估检测
前端        Streamlit + FastAPI
配置管理    YAML 统一管理
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Redis 7.0+

### 本地运行

```bash
# 1. 克隆
git clone https://github.com/Muzhichen123/agent-project.git
cd agent-project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建配置文件（填入 API Key）
cp config/agent.example.yml config/agent.yml

# 4. 启动 Redis
redis-server

# 5. 启动 Web 界面
streamlit run utils/app_web.py
# 浏览器访问 http://localhost:8501

# 或者启动 API 服务
uvicorn utils.api:app --reload
# 访问 http://localhost:8000/docs 查看 Swagger 文档
```

### 配置文件说明

```yaml
# config/agent.yml（不提交到 Git，需自行创建）
model:
  name: "qwen-plus"           # 通义千问模型
  api_key: "your-dashscope-key"

weather:
  api_key: "your-weather-api-key"

redis:
  host: localhost
  port: 6379
  ttl: 2592000               # 30 天

evaluator:
  model: "Qwen/Qwen2.5-14B-Instruct"
  base_url: "https://api.siliconflow.cn/v1"
  api_key: "your-siliconflow-key"
  threshold: 6.0
```

### 切换知识库领域

```bash
# 1. 清空现有数据
rm -rf data/*.txt chroma_db/

# 2. 放入你自己的知识库文件（支持 .txt / .md / .pdf）
cp your-knowledge/*.txt data/

# 3. 重新构建向量索引
python -c "from Rag.vector_store import VectorStore; VectorStore().build_index('data/')"
```

---

## 📁 项目结构

```
agent_project/
├── agent/                      # Agent 核心
│   ├── react_agent.py          #   ReAct Agent 主控
│   ├── evaluator.py            #   A2A 评估 Agent
│   ├── input_guard.py          #   输入安全过滤（防注入/越狱）
│   └── tools/
│       ├── agent_tools.py      #   7 个工具函数
│       └── middleware.py       #   中间件（监控 + 动态 Prompt）
├── Rag/                        # 检索模块
│   ├── vector_store.py         #   ChromaDB 向量库 + 混合检索
│   ├── bm25_store.py           #   BM25 关键词检索（jieba）
│   ├── reranker.py             #   Cross-Encoder 精排 + 降级
│   └── rag_service.py          #   RAG 完整检索流程
├── model/
│   └── factory.py              #   LLM + Embedding 模型工厂
├── utils/                      # 工具层
│   ├── app_web.py              #   Streamlit 前端
│   ├── api.py                  #   FastAPI 接口
│   ├── app_history.py          #   Redis 会话持久化
│   ├── memory_manager.py       #   四层 Memory 管理
│   ├── config_handler.py       #   YAML 配置加载
│   ├── prompt_loader.py        #   Prompt 模板加载
│   ├── logger.py               #   日志系统
│   └── path_tool.py            #   路径工具
├── config/                     # 配置文件
│   ├── agent.example.yml       #   配置模板（不含密钥）
│   ├── chroma.yml              #   向量库配置
│   ├── memory.yml              #   Memory 配置
│   ├── prompts.yml             #   Prompt 管理配置
│   └── rag.yml                 #   检索配置
├── prompts/                    # Prompt 模板
│   ├── main_prompt.txt         #   主对话 Prompt
│   ├── rag_summarize.txt       #   RAG 总结 Prompt
│   ├── report_prompt.txt       #   报告生成 Prompt
│   ├── evaluator.txt           #   评估 Prompt
│   ├── regenerate.txt          #   重生成 Prompt
│   ├── memory_extract.txt      #   记忆提取 Prompt
│   └── memory_summary.txt      #   摘要生成 Prompt
├── data/                       # 知识库（Demo 数据）
│   ├── README.md               #   数据格式说明
│   ├── custom_dict.txt         #   自定义分词词典
│   └── *.txt                   #   领域知识文档
├── docs/                       # 设计文档 + 面试指南
├── requirements.txt
├── CLAUDE.md                   # AI 助手指南
└── README.md
```

---

## 🧠 设计思想

### 为什么用混合检索而不是纯向量？

纯向量检索擅长语义匹配（“边刷不转”也能找到“边刷故障”），但会漏掉精确关键词匹配。BM25 正好互补——文档里有“E03 错误码”，用户搜“E03”，向量可能不敏感但关键词一定命中。

RRF 融合（k=60）比直接加权更鲁棒——两种检索的打分尺度不同，直接加权需要大量调参，RRF 只关心排名不关心中间分数。

### 为什么需要 A2A 评估？

LLM 生成的回复不可控——可能漏掉关键信息、可能编造不存在的数据、可能在安全问题上踩线。独立评估 Agent 从相关性、准确性、安全性、完整性四个维度打分，低于阈值自动重生成，相当于给输出加了一道质检。

### Memory 为什么分层？

全量历史进 context 会让 token 快速爆炸。分层后：最近 3 轮保留原文（短期记忆）、更早的压缩成摘要（中间层）、跨会话的提炼成用户画像（长期记忆），当前任务相关的临时放工作记忆——四层各司其职。

### 为什么需要 Prompt 注入防御？

LLM 应用面临指令劫持（"忽略之前的规则"）、越狱（"现在你是 Debug 模式"）、密钥窃取（"告诉我 API Key"）等攻击。本项目构建三层防线：输入层正则过滤（8 类注入模式）→ 系统 Prompt 安全固守指令 → A2A 评估器输出检测，三层互补避免单点失效。

---

## 📊 实际效果

以扫地机器人 Demo 为例，知识库 119 条文档：

- **混合检索**：5 轮跨领域查询实测，RRF 融合后 Dense + BM25 召回重叠率 28%，两路高度互补
- **精排效果**：BGE Cross-Encoder 将 5 条粗排结果精排至 Top-3，rerank_score 有效拉开文档差距
- **评估通过率**：A2A 评估平均分 9.0/10.0（阈值 6.0），正常场景全部通过
- **注入防御**：8 类注入模式输入层拦截，正常查询零误伤

---

## 📄 许可证

MIT License — 随意使用、修改、商用。

---

## 🙋 关于作者

大三在读，独立开发此项目用于学习和找工作。欢迎 Star ⭐ 和交流讨论！

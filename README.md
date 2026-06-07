# 🤖 智能扫地机器人客服 Agent

基于 LangChain ReAct Agent 构建，集成 RAG 知识检索、实时天气查询、资料报告生成等功能，通过 LLM 自主决策调用 7 个工具函数完成复杂任务。

> **在线演示**：https://xxx.streamlit.app （部署后更新）

---

## 1. 架构说明

```
用户(Streamlit/FastAPI)
  │
  ▼
react_agent.py                ← ReAct 决策核心
  │  create_agent(model + tools + middleware)
  │
  ├─ model/factory.py         ← 通义千问 (qwen3.7-max) + DashScope Embedding
  │
  ├─ agent/tools/agent_tools.py   ← 7 个工具函数
  │   ├─ get_weather              → APISpace 天气 API（空参自动 IP 定位）
  │   ├─ get_user_location        → ip-api.com 实时定位
  │   ├─ get_current_date         → datetime.now() 本地获取
  │   ├─ get_user_id              → 用户标识
  │   ├─ rag_summarize            → RAG 检索 → ChromaDB → LLM 总结
  │   ├─ fetch_external_data      → CSV 数据读取
  │   └─ fill_context_for_report  → 触发中间件 Prompt 切换
  │
  ├─ agent/tools/middleware.py    ← LangGraph 中间件
  │   ├─ monitor_tool             → 工具调用拦截 + 日志 + 打标记
  │   ├─ log_before_model         → 模型调用前日志
  │   └─ report_prompt_switch     → 对话/报告双场景动态 Prompt 切换
  │
  ├─ Rag/rag_service.py           ← RAG 检索服务
  │   └─ Rag/vector_store.py      ← ChromaDB 向量存储
  │
  └─ utils/app_history.py         ← Redis 会话持久化（TTL 30天）
```

**数据流**：用户提问 → Redis 取历史 → 拼消息列表 → Agent 决策（思考→工具调用→观察→再思考）→ 流式输出 → 存回 Redis

---

## 2. 关键 Prompt 与 Vibe Coding 思路

### Prompt 分层策略

| 场景 | Prompt 文件 | 用途 |
|------|------------|------|
| 日常对话 | `prompts/main_prompt.txt` | 客服角色 + 7 工具描述 + 输出规则 |
| 报告生成 | `prompts/report_prompt.txt` | 报告写手角色 + 数据查询工具 + Markdown 输出 |
| RAG 总结 | `prompts/rag_summarize.txt` | 基于参考资料总结，不编造 |

### 动态 Prompt 切换机制

用户说"生成报告" → 模型调 `fill_context_for_report` → `monitor_tool` 中间件打标记 → 下一轮 `dynamic_prompt` 读到标记 → 自动切换为报告专用模板。

核心思路：**不让同一个 Prompt 同时处理对话和报告两种场景**，通过中间件在运行时动态切换角色。

### Vibe Coding 思路

该项目采用 AI 辅助开发，使用 Claude Code 进行代码生成、调试和 Prompt 迭代。实践中体会到：

- **Prompt 是软约束，代码是硬约束**：模型曾忽视 Prompt 规则自行猜测城市名，最终在 `get_weather` 代码层增加空参自动定位逻辑兜底。
- **外部 API 不可靠时优先用本地方案**：`get_current_date` 曾调用 timeapi.io，国内网络不稳定后改用 `datetime.now()`。
- **LLM 知识截止问题**：模型默认使用 2023 年训练数据回答日期问题，需在 Prompt 开头明确声明"训练数据已过时，必须调工具"。

---

## 3. AI 调用逻辑

### Function Calling

7 个工具通过 LangChain `@tool` 装饰器注册，模型根据用户意图自动选择并填入参数。工具间支持依赖链调用，例如天气查询场景：`get_user_location → get_weather`。

### 流式输出

采用 `agent.stream(stream_mode="values")` 实现流式输出。输出过滤逻辑：仅保留 `type="ai"` 且不含 `tool_calls` 的最终回复，屏蔽用户消息复读、工具执行结果和模型中间推理。详见 `react_agent.py` 第 52-57 行。

### 会话管理

继承 `BaseChatMessageHistory` 自定义 Redis 存储后端，`session_id` 作 key，JSON 序列化消息列表，`setex` 原子设置 30 天 TTL。每次请求先取历史拼入消息列表，回复后再写回。

---

## 4. 部署步骤

### 环境要求

- Python 3.10+
- Redis 7.0+

### 本地部署

```bash
# 1. 克隆
git clone https://github.com/Muzhichen123/agent-project.git
cd agent-project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建 config/agent.yml（填入 API Key，模板见下方）
# 4. 启动 Redis
redis-server

# 5. 启动 Streamlit 前端
streamlit run utils/app_web.py
# 访问 http://localhost:8501

# 或启动 FastAPI 接口
uvicorn utils.api:app --reload
# 访问 http://localhost:8000/docs
```

### config/agent.yml 模板

```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  ttl: 2592000

weather:
  api_key: "你的APISpace天气API密钥"
  base_url: "https://eolink.o.apispace.com/456456/weather/v001/now"

model:
  name: "qwen-plus"
  api_key: "你的通义千问API密钥"

external_data_path: "data/external/records.csv"
```

### 在线部署（Streamlit Cloud）

1. Fork 本项目到你的 GitHub
2. 打开 [share.streamlit.io](https://share.streamlit.io)
3. 连接 GitHub，选择本仓库，入口文件填 `utils/app_web.py`
4. 在 Secrets 中配置 `config/agent.yml` 的内容
5. 部署，获得 `https://xxx.streamlit.app` 在线地址

---

## 📁 项目结构

```
agent_project/
├── agent/
│   ├── react_agent.py          # ReAct Agent 核心
│   └── tools/
│       ├── agent_tools.py      # 7 个工具函数
│       └── middleware.py       # 中间件（监控 + 动态 Prompt）
├── Rag/
│   ├── rag_service.py          # RAG 检索服务
│   └── vector_store.py         # ChromaDB 向量库管理
├── model/
│   └── factory.py              # 模型工厂（Chat + Embedding）
├── utils/
│   ├── app_web.py              # Streamlit 前端
│   ├── api.py                  # FastAPI 接口
│   ├── app_history.py          # Redis 历史会话
│   ├── config_handler.py       # YAML 配置管理
│   ├── prompt_loader.py        # Prompt 加载
│   ├── logger.py               # 日志系统
│   └── path_tool.py            # 路径工具
├── prompts/
│   ├── main_prompt.txt         # 系统提示词
│   ├── report_prompt.txt       # 报告生成提示词
│   └── rag_summarize.txt       # RAG 总结提示词
├── config/                     # 配置文件（agent.yml 在 .gitignore）
├── chroma_db/                  # 向量数据库文件
├── requirements.txt
└── README.md
```

---

## 📄 许可证

MIT License

# 🤖 智扫通机器人智能客服

基于大语言模型的智能客服系统，专注于扫地机器人领域的专业咨询服务。

---

## ✨ 功能特性

- **智能对话**：支持多轮对话，具备上下文理解能力
- **实时天气查询**：接入真实天气API，获取准确天气信息
- **文档检索**：基于RAG技术的知识库问答
- **会话持久化**：使用Redis存储会话历史
- **工具调用**：自动选择并调用合适的工具

---

## 🛠️ 技术栈

| 分类 | 技术 | 用途 |
|------|------|------|
| **框架** | LangChain | Agent框架 |
| **前端** | Streamlit | Web界面 |
| **大模型** | 通义千问 | 对话生成 |
| **数据库** | Redis | 会话存储 |
| **向量存储** | Chroma | RAG检索 |
| **语言** | Python | 后端开发 |

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Redis 7.0+

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置文件
修改 `config/agent.yml`：
```yaml
redis:
  host: localhost
  port: 6379
  db: 0
```

### 启动应用
```bash
streamlit run utils/app_web.py
```

### 访问地址
- 本地：http://localhost:8501

---

## 📁 项目结构

```
agent_project/
├── agent/                    # Agent核心模块
│   ├── react_agent.py        # React模式Agent
│   └── tools/
│       ├── agent_tools.py    # 工具函数
│       └── middleware.py     # 中间件
├── Rag/                      # RAG模块
│   ├── rag_service.py        # RAG服务
│   └── vector_store.py       # 向量存储
├── model/                    # 模型管理
│   └── factory.py            # 模型工厂
├── utils/                    # 工具模块
│   ├── app_web.py            # Streamlit前端
│   ├── app_history.py        # Redis会话历史
│   └── config_handler.py     # 配置管理
├── config/                   # 配置文件
├── data/                     # 数据文件
└── README.md                 # 项目说明
```

---

## 📝 使用示例

### 对话示例
```
用户：深圳天气怎么样？
AI：深圳天气:晴，温度:26℃

用户：我住在哪里？
AI：您之前提到过您住在深圳。

用户：扫地机器人怎么保养？
AI：根据参考资料，扫地机器人保养建议如下：...
```

---

## 📊 核心功能

### 1. Agent智能对话
- React模式思考-行动-观察循环
- 自动工具选择和调用
- 中间件监控和日志

### 2. 工具集
| 工具 | 功能 |
|------|------|
| `get_weather` | 实时天气查询 |
| `rag_summarize` | 文档检索总结 |
| `get_user_location` | 获取用户位置 |
| `fetch_external_data` | 获取用户使用记录 |

### 3. 会话管理
- Redis持久化存储
- 支持上下文理解
- 30天自动清理策略

---

## 📄 许可证

MIT License

---

## 📧 联系方式

- GitHub: [@Muzhichen123](https://github.com/Muzhichen123)

---

*项目持续开发中，欢迎Star和PR！* ⭐
# 模块 4: Memory 机制（替代全量上下文）

> 优先级编号为 4 但这是架构改动最大的模块，建议在 Rerank 和混合检索之后实施。

## 4.1 目标

用结构化的 Memory 层替代当前的全量历史消息加载，解决:
1. **Token 爆炸**: 长对话历史撑满模型上下文窗口
2. **注意力稀释**: 模型在长上下文中找不到关键信息（lost in the middle）
3. **幻觉风险**: 大量无关历史内容干扰模型判断
4. **成本浪费**: 每轮对话重复发送大量无用历史 token

## 4.2 当前架构

**文件**: `utils/app_history.py` + `agent/react_agent.py`

```
ReactAgent.execute_stream(query):
  1. self.history.messages  # 从 Redis 取出全部历史消息（可能是几百轮）
  2. 全量拼接到 messages 列表
  3. 追加当前 query
  4. 送给 Agent
  5. Agent 回复后，HumanMessage + AIMessage 存回 Redis
```

**问题**:
- `RedisChatMessageHistory.messages` 返回的是**全部**历史消息
- TTL 30 天（2592000 秒），长对话期间消息不断累积
- 没有 token 限制检查
- 没有摘要/压缩机制

## 4.3 目标架构

```
用户 Query
  ↓
MemoryManager.get_context(session_id, current_query):
  ├─ 短期记忆: 最近 N 轮的原始对话（滑动窗口）
  ├─ 对话摘要: 更早的对话的压缩摘要
  ├─ 用户画像: 设备型号、常见问题、偏好
  └─ 工作记忆: 当前任务的上下文（如"正在帮用户排查 E03 故障"）
  ↓
拼接成 context 字符串，替代全量历史
  ↓
送给 Agent
  ↓
Agent 回复后 → MemoryManager.update_memory(session_id, query, response)
  ├─ 更新短期记忆（追加当前轮）
  ├─ 更新对话摘要（超出窗口时压缩最早的对话）
  ├─ 提取关键信息更新用户画像
  └─ 更新/清除工作记忆
```

## 4.4 Memory 分层设计

### 4.4.1 Memory 数据结构

```json
{
  "session_id": "session_12345",
  "short_term": [
    {"role": "user", "content": "我的扫地机器人报了 E03 错误"},
    {"role": "assistant", "content": "E03 错误通常表示滚刷卡住..."},
    {"role": "user", "content": "清理了还是有问题"},
    {"role": "assistant", "content": "如果清理后仍然报错..."}
  ],
  "summary": "用户有一台扫地机器人，之前询问过 E03 故障（滚刷卡住），已建议清理滚刷但问题未解决。",
  "user_profile": {
    "device_model": "未知",
    "known_issues": ["E03 滚刷卡住（未解决）"],
    "preferences": [],
    "first_seen": "2026-06-09",
    "query_count": 4
  },
  "working_memory": {
    "active_task": "E03 故障排查",
    "task_context": "用户已尝试清理滚刷但问题未解决，下一步需要检查滚刷电机"
  }
}
```

### 4.4.2 各层职责

| 层级 | 内容 | 存储位置 | 生命周期 | 更新频率 |
|------|------|---------|---------|---------|
| **短期记忆** | 最近 N 轮原始对话 | Redis (hash) | 滑动窗口 | 每轮追加 |
| **对话摘要** | 窗口外对话的压缩摘要 | Redis (hash) | 持久 | 窗口溢出时更新 |
| **用户画像** | 设备型号、问题类型、偏好 | Redis (hash) | 持久 | 每 N 轮或关键信息出现时 |
| **工作记忆** | 当前任务上下文 | Redis (hash) | 任务级 | 任务开始/结束/推进时 |

### 4.4.3 参数配置

```yaml
# config/memory.yml (新建)
memory:
  enabled: true

  # 短期记忆（滑动窗口）
  short_term:
    window_size: 6         # 保留最近 6 轮对话（3 轮问 + 3 轮答）

  # 对话摘要
  summary:
    enabled: true
    max_summary_length: 300 # 摘要最大长度（字符）
    trigger_interval: 1    # 每溢出 1 轮就更新一次摘要

  # 用户画像
  user_profile:
    enabled: true
    extract_interval: 3    # 每 3 轮对话提取一次用户画像

  # 工作记忆
  working_memory:
    enabled: true
    max_idle_turns: 5       # 超过 5 轮没有相关提及则自动清除
```

## 4.5 配置变更

### 新建 `config/memory.yml`

```yaml
memory:
  enabled: true
  short_term:
    window_size: 6
  summary:
    enabled: true
    max_summary_length: 300
    trigger_interval: 1
  user_profile:
    enabled: true
    extract_interval: 3
  working_memory:
    enabled: true
    max_idle_turns: 5
```

### 修改 `config/prompts.yml` — 新增 prompt 映射

```yaml
# 新增以下条目
memory_summary_prompt: prompts/memory_summary.txt
memory_extract_prompt: prompts/memory_extract.txt
```

### 新建 `prompts/memory_summary.txt`

```
你是一个对话摘要助手。请将以下多轮对话压缩为一段简洁的摘要。

### 要求
1. 保留所有关键事实：设备型号、故障码、已尝试的解决方案、未解决的问题
2. 保留用户的核心意图和当前状态
3. 删除寒暄、重复、无关内容
4. 使用第三人称描述（"用户..."），不超过 300 字
5. 仅输出摘要文本，不要有任何其他格式

### 待摘要的对话
{conversation}
```

### 新建 `prompts/memory_extract.txt`

```
你是一个用户画像提取助手。请从以下最新一轮对话中提取关键信息。

### 提取维度
1. device_model: 用户提到的设备型号（如 "X900"、"扫拖一体机 Pro"），未提及则为 "未知"
2. known_issues: 用户遇到的问题或故障（如 ["E03 滚刷卡住"]）
3. preferences: 用户的使用偏好或需求（如 ["需要定时清扫功能"]）
4. active_task: 当前正在处理的任务（如 "E03 故障排查"），无则为空

### 约束
- 仅提取对话中明确提及的信息，不推断
- 以 JSON 格式输出，严格按照以下结构：
{"device_model": "...", "known_issues": [...], "preferences": [...], "active_task": "..."}

### 最新一轮对话
用户: {user_message}
助手: {assistant_message}
```

## 4.6 代码改动

### 4.6.1 新建 `utils/memory_manager.py`

```python
"""
Memory 管理模块
用结构化的 Memory 层替代全量历史消息，减少 token 消耗和幻觉风险
"""
import json
import redis
from typing import List, Dict, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from model.factory import chat_model
from utils.logger import logger
from utils.config_handler import agent_config

# Memory 配置暂时硬编码在这里，或从 config 加载
MEMORY_CONFIG = {
    "short_term_window": 6,
    "summary_max_length": 300,
    "profile_extract_interval": 3,
    "working_memory_idle_turns": 5,
}


class MemoryManager:
    """Memory 管理器"""

    REDIS_PREFIX = "memory:"

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.redis_key = f"{self.REDIS_PREFIX}{session_id}"
        self.redis = self._get_redis()
        self.turn_count = 0

    def _get_redis(self):
        """获取 Redis 连接（复用现有配置）"""
        import os
        redis_config = agent_config["redis"]
        redis_host = os.environ.get("REDIS_HOST", redis_config["host"])
        return redis.Redis(
            host=redis_host,
            port=redis_config["port"],
            db=redis_config["db"],
            decode_responses=True,  # Memory 存储用字符串即可
            socket_timeout=5,
        )

    def _load(self) -> Dict:
        """加载 Memory 数据"""
        try:
            data = self.redis.get(self.redis_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"[Memory] 加载失败: {e}")
        return self._default_memory()

    def _save(self, data: Dict):
        """保存 Memory 数据"""
        try:
            ttl = agent_config["redis"]["ttl"]
            self.redis.setex(self.redis_key, ttl, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"[Memory] 保存失败: {e}")

    def _default_memory(self) -> Dict:
        return {
            "short_term": [],
            "summary": "",
            "user_profile": {
                "device_model": "未知",
                "known_issues": [],
                "preferences": [],
                "active_task": "",
            },
            "working_memory": {
                "active_task": "",
                "task_context": "",
                "idle_turns": 0,
            },
            "turn_count": 0,
        }

    def get_context(self, current_query: str) -> List[Dict]:
        """
        获取压缩后的上下文，替代全量历史

        Returns:
            消息字典列表 [{"role": "user/assistant", "content": "..."}]
        """
        memory = self._load()
        messages = []

        # 第一部分: 对话摘要（如果有）
        if memory["summary"]:
            messages.append({
                "role": "assistant",
                "content": f"[对话历史摘要] {memory['summary']}"
            })

        # 第二部分: 工作记忆（如果有活跃任务）
        wm = memory.get("working_memory", {})
        if wm.get("active_task") and wm.get("idle_turns", 0) < MEMORY_CONFIG["working_memory_idle_turns"]:
            messages.append({
                "role": "assistant",
                "content": f"[当前任务] {wm['active_task']}: {wm.get('task_context', '')}"
            })

        # 第三部分: 短期记忆（最近 N 轮）
        for msg in memory.get("short_term", []):
            messages.append(msg)

        return messages

    def update_memory(self, query: str, response: str):
        """
        每轮对话后更新 Memory

        Args:
            query: 用户输入
            response: AI 回复
        """
        memory = self._load()
        memory["turn_count"] += 1

        # 1. 追加到短期记忆
        memory["short_term"].append({"role": "user", "content": query})
        memory["short_term"].append({"role": "assistant", "content": response})

        # 2. 检查短期记忆是否超出窗口
        window = MEMORY_CONFIG["short_term_window"]
        while len(memory["short_term"]) > window * 2:  # 2 条 = 1 轮（问+答）
            # 溢出的对话移到摘要中
            overflow = memory["short_term"][:2]  # 取最早的一轮
            old_summary = memory.get("summary", "")
            new_summary = self._update_summary(old_summary, overflow)
            memory["summary"] = new_summary
            memory["short_term"] = memory["short_term"][2:]

        # 3. 定期提取用户画像
        if memory["turn_count"] % MEMORY_CONFIG["profile_extract_interval"] == 0:
            profile = self._extract_profile(query, response, memory.get("user_profile", {}))
            memory["user_profile"] = self._merge_profile(memory.get("user_profile", {}), profile)

        # 4. 更新工作记忆
        self._update_working_memory(memory, query, response)

        self._save(memory)
        logger.info(f"[Memory] 第 {memory['turn_count']} 轮对话记忆已更新")

    def _update_summary(self, old_summary: str, overflow_messages: List[Dict]) -> str:
        """
        使用 LLM 将溢出的对话合并到摘要中

        Args:
            old_summary: 现有摘要
            overflow_messages: 溢出的消息列表（一轮问+答）

        Returns:
            更新后的摘要
        """
        conversation = ""
        for msg in overflow_messages:
            role = "用户" if msg["role"] == "user" else "助手"
            conversation += f"{role}: {msg['content']}\n"

        prompt = f"""请将以下旧摘要和新对话合并为一段简洁的摘要。
保留所有关键事实（设备型号、故障码、解决方案、未解决问题），删除冗余和寒暄，不超过 300 字。
仅输出摘要文本。

旧摘要: {old_summary or '（无）'}

新对话:
{conversation}"""

        try:
            result = chat_model.invoke(prompt)
            return result.content.strip()
        except Exception as e:
            logger.error(f"[Memory] 摘要更新失败: {e}")
            return old_summary

    def _extract_profile(self, query: str, response: str, existing_profile: Dict) -> Dict:
        """使用 LLM 从最新一轮对话中提取用户画像"""
        prompt = f"""从以下对话中提取用户信息，以 JSON 格式返回。
提取维度: device_model(设备型号), known_issues(遇到的问题列表), preferences(偏好列表)
仅提取明确提及的信息，不推断。空值用空字符串或空列表。

用户: {query}
助手: {response}"""

        try:
            result = chat_model.invoke(prompt)
            import re
            json_match = re.search(r'\{[^}]+\}', result.content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"[Memory] 画像提取失败: {e}")
        return {}

    def _merge_profile(self, existing: Dict, new_info: Dict) -> Dict:
        """合并用户画像，去重"""
        merged = existing.copy()

        if new_info.get("device_model") and new_info["device_model"] != "未知":
            merged["device_model"] = new_info["device_model"]

        if new_info.get("known_issues"):
            existing_issues = set(merged.get("known_issues", []))
            for issue in new_info["known_issues"]:
                if issue and issue not in existing_issues:
                    merged.setdefault("known_issues", []).append(issue)

        if new_info.get("preferences"):
            existing_prefs = set(merged.get("preferences", []))
            for pref in new_info["preferences"]:
                if pref and pref not in existing_prefs:
                    merged.setdefault("preferences", []).append(pref)

        return merged

    def _update_working_memory(self, memory: Dict, query: str, response: str):
        """更新工作记忆（当前任务上下文）"""
        wm = memory.get("working_memory", {"active_task": "", "task_context": "", "idle_turns": 0})

        # 检查当前对话是否涉及活跃任务
        if wm.get("active_task"):
            # 简单关键词匹配判断是否仍在处理同一任务
            task_keywords = wm["active_task"].split()
            query_lower = query.lower()
            related = any(kw in query_lower for kw in task_keywords if len(kw) > 1)

            if related:
                wm["idle_turns"] = 0
                # 更新任务上下文
                wm["task_context"] = response[:200]  # 取回复前 200 字作为任务上下文
            else:
                wm["idle_turns"] += 1
                if wm["idle_turns"] >= MEMORY_CONFIG["working_memory_idle_turns"]:
                    # 超时清除工作记忆
                    wm = {"active_task": "", "task_context": "", "idle_turns": 0}
                    logger.info("[Memory] 工作记忆已超时清除")
        else:
            # 检测是否开始新任务（简单启发式：如果对话中提到了故障码或设备问题）
            import re
            fault_match = re.search(r'[A-Z]\d{2,}', query)  # 如 E03
            if fault_match:
                wm["active_task"] = f"{fault_match.group()} 故障排查"
                wm["task_context"] = f"用户首次提及 {fault_match.group()} 问题"
                wm["idle_turns"] = 0
                logger.info(f"[Memory] 新工作记忆: {wm['active_task']}")

        memory["working_memory"] = wm

    def clear(self):
        """清除全部 Memory"""
        self.redis.delete(self.redis_key)
        logger.info(f"[Memory] 会话 {self.session_id} 记忆已清除")
```

### 4.6.2 修改 `agent/react_agent.py` — 核心改动

```python
# 新增导入
from utils.memory_manager import MemoryManager

class ReactAgent():
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id

        # ===== 改动: 用 MemoryManager 替代全量历史 =====
        self.memory = MemoryManager(session_id)
        # self.history = get_history(session_id)  # 原有方式，保留备用
        # ===== 改动结束 =====

        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, get_weather, get_user_id, get_user_location,
                   get_current_date, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch]
        )

    def execute_stream(self, query: str):
        """
        执行流式回答，使用 Memory 机制管理上下文
        """
        # ===== 改动: 从 Memory 获取压缩后的上下文，替代全量历史 =====
        memory_messages = self.memory.get_context(query)
        messages = list(memory_messages)  # Memory 返回的历史上下文
        messages.append({"role": "user", "content": query})
        # ===== 改动结束 =====

        input_dict = {"messages": messages}

        # 流式返回结果（逻辑不变）
        response_chunks = []
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content and latest_message.type == "ai":
                if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                    continue
                response_chunks.append(latest_message.content.strip())
                yield latest_message.content.strip() + "\n"

        full_response = "".join(response_chunks)

        # ===== 改动: 更新 Memory 而非全量存 Redis =====
        self.memory.update_memory(query, full_response)
        # ===== 改动结束 =====

    def clear_history(self):
        """清除当前会话的记忆"""
        self.memory.clear()
```

## 4.7 兼容性处理

Memory 机制可以通过配置开关控制，不开启时走原有逻辑:

```python
# react_agent.py 中的开关逻辑
MEMORY_ENABLED = chroma_config.get("memory", {}).get("enabled", False)  # 默认关闭

class ReactAgent():
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        if MEMORY_ENABLED:
            self.memory = MemoryManager(session_id)
        else:
            self.history = get_history(session_id)  # 原有方式
        # ... 其余不变 ...

    def execute_stream(self, query: str):
        if MEMORY_ENABLED:
            messages = self.memory.get_context(query)
        else:
            history_messages = self.history.messages
            messages = [{"role": "user" if m.type == "human" else "assistant",
                         "content": m.content} for m in history_messages]
        messages.append({"role": "user", "content": query})
        # ... 其余不变 ...
```

## 4.8 Token 预估

| 场景 | 全量历史（当前） | Memory 机制（优化后） |
|------|-----------------|---------------------|
| 10 轮对话 | ~4000 token | ~2000 token |
| 50 轮对话 | ~20000 token | ~2500 token |
| 100 轮对话 | ~40000+ token（可能超限） | ~2800 token |
| 200 轮对话 | 无法处理 | ~3000 token |

Memory 的上下文大小基本恒定，不随对话轮数增长。

## 4.9 依赖变更

无新增依赖（复用现有的 redis、langchain）。

## 4.10 测试方案

### 单元测试

```python
# 测试 Memory 基本功能
mm = MemoryManager("test_session")

# 模拟 10 轮对话
for i in range(10):
    mm.update_memory(f"用户问题 {i}", f"助手回复 {i}")

# 验证上下文长度是否受控
ctx = mm.get_context("新问题")
print(f"上下文消息数: {len(ctx)}")  # 应该 <= 10 左右，而非 20

# 验证摘要是否生成
memory = mm._load()
print(f"摘要: {memory['summary']}")  # 应该有非空摘要
```

### 回归测试

| 场景 | 验证点 |
|------|--------|
| 日常对话 | 连续 20 轮闲聊，检查 Memory 是否正常压缩 |
| 故障排查 | 连续对话排查 E03 故障，检查工作记忆是否跟踪任务 |
| 报告生成 | 触发报告生成流程，检查 Memory 是否影响中间件标记 |
| 模型切换 | report_prompt_switch 中间件是否在 Memory 模式下正常工作 |
| 新会话 | 新 session_id 是否从空白 Memory 开始 |

### 对比测试

用相同的对话序列，分别测试:
1. 全量历史模式（当前）
2. Memory 模式

对比:
- 回复质量是否下降
- 模型是否能记住之前的对话内容
- 上下文 token 数的差异

## 4.11 已知局限

1. **Memory 更新需要一次额外 LLM 调用**（摘要更新 + 画像提取），增加约 1-2 秒延迟。可以改为异步更新（先返回回复，后台更新 Memory）
2. **摘要质量依赖 LLM**，可能丢关键细节。需要反复调 prompt，特别是 `memory_summary.txt`
3. **用户画像提取** 用的是正则 + LLM 混合方案，不完美。后续可以升级为结构化提取
4. **工作记忆的 idle 检测** 目前是简单的关键词匹配，不够智能。后续可以用 LLM 判断任务是否仍在进行

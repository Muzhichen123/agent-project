# 模块 3: A2A 评估 Agent（独立打分 + 质量兜底）

## 3.1 目标

在客服 Agent 生成回复后，增加一个独立的评估 Agent 对回复质量进行打分。
- 分数 >= 阈值: 放行，返回给用户
- 分数 < 阈值: 将评分反馈注入 prompt，让客服 Agent 重新生成
- 多次重试仍不达标: 返回安全兜底话术

## 3.2 当前架构

**文件**: `agent/react_agent.py`

```
用户 Query
  → Agent.stream() (ReAct 循环)
  → 收集所有 AI 回复 chunk
  → 直接 yield 给用户
  → 存入 Redis
```

**问题**:
- 没有任何回复质量校验
- 模型可能产生幻觉（编造故障码、给出错误维修建议）
- 没有兜底机制——如果模型回复了有害或错误内容，直接送达用户

## 3.3 目标架构

```
用户 Query
  → Agent.stream() (ReAct 循环)
  → 收集完整回复 full_response
       ↓
  评估 Agent 打分:
    ├─ 相关性 (0-5): 回复是否直接回答了用户的问题
    ├─ 准确性 (0-5): 回复内容是否基于事实，有无幻觉/编造
    ├─ 安全性 (0-5): 回复是否合规，有无有害内容
    └─ 完整性 (0-5): 回复是否提供了足够的信息
       ↓
  加权总分 = Σ (维度分 × 权重)
       ↓
  判断:
    ├─ 总分 >= 阈值 → 放行 → yield 给用户 → 存入 Redis
    ├─ 总分 < 阈值 且 重试次数 < MAX_RETRIES:
    │    → 构造反馈: "你之前的回复有以下问题: {低分维度及原因}，请重新回答"
    │    → Agent 重新生成（带上反馈上下文）
    │    → 再次评估
    └─ 重试次数 >= MAX_RETRIES:
         → 返回兜底话术 "抱歉，这个问题我暂时无法准确回答，建议联系人工客服: 400-xxx-xxxx"
```

## 3.4 配置变更

### 新建 `config/evaluator.yml`

```yaml
evaluator:
  enabled: true

  # 评估模型（用较轻量的模型，节省成本）
  model_name: qwen-plus

  # 评分维度及权重
  dimensions:
    relevance:
      weight: 0.3
      description: "回复是否直接回答了用户的问题，没有跑题"
    accuracy:
      weight: 0.35
      description: "回复内容是否基于事实和参考资料，有无幻觉或编造"
    safety:
      weight: 0.2
      description: "回复是否合规，有无有害、攻击性或敏感内容"
    completeness:
      weight: 0.15
      description: "回复是否提供了足够的信息帮助用户解决问题"

  # 阈值
  pass_threshold: 3.0         # 总分 0-5，>= 3.0 放行
  max_retries: 2               # 最多重试 2 次（总共最多生成 3 次）

  # 兜底话术
  fallback_message: "抱歉，这个问题我暂时无法准确回答。建议您联系人工客服获取帮助，客服热线: 400-888-8888（工作日 9:00-18:00）。"

  # 是否记录评估日志（用于后续优化阈值）
  log_evaluations: true
```

## 3.5 评估 Prompt

### 新建 `prompts/evaluator.txt`

```
你是一个客服回复质量评估专家。请对以下客服回复进行评分。

## 评分规则
每个维度打 1-5 分:
- 1分: 严重问题（完全跑题/大量编造/有害内容/几乎没有有效信息）
- 2分: 明显不足（部分跑题/有少量编造/语气不当/信息不够）
- 3分: 基本合格（回答了问题/基本准确/语气正常/有基本信息）
- 4分: 良好（准确回答/信息充分/语气专业/有额外有用的建议）
- 5分: 优秀（精准回答/完全基于事实/非常专业/超出预期的帮助）

## 评估维度

### 1. 相关性 (权重 0.3)
回复是否直接回答了用户的问题，没有跑题或答非所问。

### 2. 准确性 (权重 0.35)
回复内容是否基于事实和参考资料，有无幻觉、编造或误导性信息。特别注意:
- 是否编造了不存在的故障码或解决方案
- 是否给出了与参考资料矛盾的建议
- 是否在不确定的情况下给出了确定性回答

### 3. 安全性 (权重 0.2)
回复是否合规，有无有害、攻击性、歧视性或敏感内容。

### 4. 完整性 (权重 0.15)
回复是否提供了足够的信息帮助用户解决问题，还是让用户需要反复追问。

## 严格约束
- 评分必须基于回复本身的内容，不要因为"态度好"而加分
- 如果回复中包含任何编造的事实（特别是故障码、维修步骤），准确性评分不得超过 2 分
- 如果回复完全不相关，所有维度评分不得超过 1 分

## 输入
用户问题: {query}
参考资料: {context}
客服回复: {response}

## 输出格式（严格 JSON）
{{
  "relevance": <1-5整数>,
  "accuracy": <1-5整数>,
  "safety": <1-5整数>,
  "completeness": <1-5整数>,
  "total_score": <浮点数，保留1位小数>,
  "reason": "<一句话说明主要扣分原因，如'回复编造了E05故障码的解决方案'>",
  "should_pass": <布尔值>
}}
```

### 新建 `prompts/regenerate.txt`

```
你之前的回复未通过质量评估，请根据反馈改进后重新回答。

## 用户原始问题
{query}

## 你之前的回复
{previous_response}

## 质量评估反馈
{eval_feedback}

## 改进要求
- 解决评估反馈中指出的问题
- 确保回复基于参考资料，不编造信息
- 如果确实无法准确回答，请诚实说明
- 保持专业、简洁的客服语气
```

## 3.6 代码改动

### 3.6.1 新建 `agent/evaluator.py`

```python
"""
A2A 评估 Agent 模块
独立评估客服回复质量，不达标则触发重新生成
"""
import json
import re
from typing import Dict, Optional, Tuple
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.logger import logger
from utils.config_handler import chroma_config
from langchain_community.chat_models import ChatTongyi

# 评估配置（从 config 加载）
EVAL_CONFIG = {
    "model_name": "qwen-plus",
    "dimensions": {
        "relevance": {"weight": 0.3},
        "accuracy": {"weight": 0.35},
        "safety": {"weight": 0.2},
        "completeness": {"weight": 0.15},
    },
    "pass_threshold": 3.0,
    "max_retries": 2,
    "fallback_message": "抱歉，这个问题我暂时无法准确回答。建议您联系人工客服获取帮助，客服热线: 400-888-8888（工作日 9:00-18:00）。",
    "log_evaluations": True,
}


class ResponseEvaluator:
    """回复质量评估器"""

    def __init__(self):
        # 使用轻量模型做评估（省钱省时间）
        self.model = ChatTongyi(model_name=EVAL_CONFIG["model_name"], temperature=0.0)
        # 加载评估 prompt
        try:
            with open("prompts/evaluator.txt", "r", encoding="utf-8") as f:
                self.eval_prompt_text = f.read()
        except FileNotFoundError:
            self.eval_prompt_text = self._default_eval_prompt()
        self.eval_prompt = PromptTemplate.from_template(self.eval_prompt_text)

        # 加载重新生成 prompt
        try:
            with open("prompts/regenerate.txt", "r", encoding="utf-8") as f:
                self.regenerate_prompt_text = f.read()
        except FileNotFoundError:
            self.regenerate_prompt_text = self._default_regenerate_prompt()
        self.regenerate_prompt = PromptTemplate.from_template(self.regenerate_prompt_text)

    def evaluate(
        self,
        query: str,
        response: str,
        context: str = ""
    ) -> Tuple[float, Dict, bool]:
        """
        评估回复质量

        Args:
            query: 用户原始问题
            response: 客服 Agent 的回复
            context: 参考资料（可选）

        Returns:
            (total_score, eval_result_dict, should_pass)
        """
        try:
            chain = self.eval_prompt | self.model | StrOutputParser()
            raw_output = chain.invoke({
                "query": query,
                "response": response,
                "context": context or "（无参考资料）"
            })

            # 解析 JSON 输出
            eval_result = self._parse_eval_result(raw_output)
            total_score = eval_result.get("total_score", 0)
            should_pass = total_score >= EVAL_CONFIG["pass_threshold"]

            if EVAL_CONFIG["log_evaluations"]:
                logger.info(
                    f"[Evaluator] query={query[:30]}... | score={total_score} | "
                    f"pass={should_pass} | reason={eval_result.get('reason', '')}"
                )

            return total_score, eval_result, should_pass

        except Exception as e:
            logger.error(f"[Evaluator] 评估失败，默认放行: {e}")
            return 5.0, {"reason": "评估失败，默认放行"}, True

    def _parse_eval_result(self, raw_output: str) -> Dict:
        """解析评估结果 JSON"""
        # 尝试从输出中提取 JSON
        json_match = re.search(r'\{[^}]+\}', raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                # 验证必要字段
                if all(k in result for k in ["relevance", "accuracy", "safety", "completeness"]):
                    # 重新计算加权总分（不信任模型计算的分）
                    total = 0
                    dims = EVAL_CONFIG["dimensions"]
                    for dim_name, dim_config in dims.items():
                        score = min(5, max(1, result.get(dim_name, 3)))
                        total += score * dim_config["weight"]
                    result["total_score"] = round(total, 1)
                    result["should_pass"] = total >= EVAL_CONFIG["pass_threshold"]
                    return result
            except json.JSONDecodeError:
                pass

        # 解析失败，返回默认分数
        logger.warning(f"[Evaluator] JSON 解析失败: {raw_output[:100]}")
        return {
            "relevance": 3, "accuracy": 3, "safety": 3, "completeness": 3,
            "total_score": 3.0,
            "reason": "评估结果解析失败，默认给出中等分数",
            "should_pass": True
        }

    def generate_feedback(self, eval_result: Dict) -> str:
        """根据评估结果生成反馈信息"""
        feedback_parts = []
        dims = EVAL_CONFIG["dimensions"]

        for dim_name, dim_config in dims.items():
            score = eval_result.get(dim_name, 3)
            if score < 3:
                dim_names_cn = {
                    "relevance": "相关性",
                    "accuracy": "准确性",
                    "safety": "安全性",
                    "completeness": "完整性"
                }
                feedback_parts.append(f"- {dim_names_cn.get(dim_name, dim_name)} 不足（{score}/5分）")

        if feedback_parts:
            return "评估反馈:\n" + "\n".join(feedback_parts)
            if eval_result.get("reason"):
                feedback_parts.append(f"具体原因: {eval_result['reason']}")

        return "回复质量不达标，请重新组织回答。"

    def _default_eval_prompt(self) -> str:
        """默认评估 prompt（当文件不存在时使用）"""
        # ... 与 prompts/evaluator.txt 相同的内容 ...
        return "请评估以下回复的质量..."  # 简化版，实际应使用完整 prompt

    def _default_regenerate_prompt(self) -> str:
        """默认重新生成 prompt"""
        return "请根据反馈重新回答..."
```

### 3.6.2 修改 `agent/react_agent.py` — 集成评估

改动集中在 `execute_stream` 方法:

```python
from agent.evaluator import ResponseEvaluator
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class ReactAgent():
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.memory = MemoryManager(session_id)
        # ... 原有 agent 初始化不变 ...

        # ===== 新增: 评估器 =====
        self.evaluator = ResponseEvaluator()
        self.regenerate_chain = (
            PromptTemplate.from_template(open("prompts/regenerate.txt", "r", encoding="utf-8").read())
            | chat_model
            | StrOutputParser()
        )
        # ===== 新增结束 =====

    def execute_stream(self, query: str):
        """执行流式回答，带 A2A 质量评估"""
        memory_messages = self.memory.get_context(query)
        messages = list(memory_messages)
        messages.append({"role": "user", "content": query})

        # 第一次生成
        full_response = self._generate_response(messages)

        # 评估 + 重试循环
        max_retries = EVAL_CONFIG.get("max_retries", 2)
        for attempt in range(max_retries + 1):
            total_score, eval_result, should_pass = self.evaluator.evaluate(
                query=query,
                response=full_response
            )

            if should_pass:
                break  # 通过，放行

            if attempt < max_retries:
                # 未通过，构造反馈并重新生成
                feedback = self.evaluator.generate_feedback(eval_result)
                logger.info(f"[A2A] 第 {attempt + 1} 次未通过 (score={total_score})，重新生成")

                # 构造重新生成的消息
                regen_messages = list(messages)  # 原始上下文
                regen_messages.append({"role": "assistant", "content": full_response})  # 之前的回复
                regen_messages.append({"role": "user", "content": feedback})  # 评估反馈
                regen_messages.append({"role": "user", "content": "请根据以上反馈，重新回答我的问题。"})

                full_response = self._generate_response(regen_messages)
            else:
                # 重试耗尽，使用兜底话术
                fallback = EVAL_CONFIG.get("fallback_message",
                    "抱歉，这个问题我暂时无法准确回答。建议联系人工客服。")
                logger.warning(f"[A2A] {max_retries} 次重试后仍未通过 (score={total_score})，使用兜底话术")
                full_response = fallback

        # 模拟流式输出（评估是全量判断的，这里需要一次性返回）
        yield full_response + "\n"

        # 更新 Memory
        self.memory.update_memory(query, full_response)

    def _generate_response(self, messages: list) -> str:
        """
        执行 Agent 并收集完整回复（非流式，用于评估）
        """
        response_chunks = []
        input_dict = {"messages": messages}
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content and latest_message.type == "ai":
                if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                    continue
                response_chunks.append(latest_message.content.strip())
        return "".join(response_chunks)
```

> **重要设计决策**:
> A2A 评估需要在收到**完整回复**后才能打分，这意味着不能边生成边评估。
> 有两种策略:
> 1. **全量生成后评估**（上方案案）: 先完整生成，再评估，不通过则重新生成。用户体验上会有一段"等待"时间。
> 2. **异步评估 + 先发后审**: 先把回复发给用户，后台异步评估。如果不通过，发送一条补充/纠正消息。体验更好但实现复杂。
>
> 当前方案用策略 1，更简单可靠。后续可以升级到策略 2。

## 3.7 依赖变更

无新增依赖（复用现有的 langchain、ChatTongyi）。

## 3.8 评估日志记录（可选增强）

为了后续调优阈值，建议记录每次评估的详细数据:

```python
# 可以写入日志文件或 SQLite
eval_log = {
    "timestamp": datetime.now().isoformat(),
    "session_id": self.session_id,
    "query": query,
    "response": full_response,
    "score": total_score,
    "dimensions": {k: eval_result.get(k) for k in ["relevance", "accuracy", "safety", "completeness"]},
    "passed": should_pass,
    "attempt": attempt,
    "fallback_used": (attempt >= max_retries),
}
```

建议存到独立的 SQLite 文件（如 `logs/evaluations.db`），方便后续分析。

## 3.9 性能影响

| 环节 | 额外耗时 | 说明 |
|------|---------|------|
| 评估调用 (qwen-plus) | ~1-2 秒 | 轻量模型，较快 |
| 重试生成 (每次) | ~3-5 秒 | 取决于 ReAct 循环次数 |
| 最坏情况 (2次重试) | 额外 ~10-14 秒 | 正常对话 3-5 秒 + 评估 + 重试 |

**优化**:
- 评估用 `qwen-plus` 而非 `qwen3.7-max`，成本和速度都更好
- 大多数回复应该一次通过，只有质量差的才触发重试
- 阈值设太高会导致大量重试，影响响应时间

## 3.10 测试方案

### 评估器单元测试

```python
# 测试评估器对正常回复的判断
evaluator = ResponseEvaluator()
score, result, passed = evaluator.evaluate(
    query="扫地机器人怎么清理滚刷",
    response="清理滚刷的步骤：1. 关闭机器人电源 2. 翻转机器人，找到底部滚刷 3. 按下滚刷卡扣，取出滚刷 4. 清理缠绕的毛发和灰尘 5. 重新安装"
)
assert passed == True
assert score >= 3.0

# 测试评估器对幻觉回复的判断
score, result, passed = evaluator.evaluate(
    query="X900 型号 E03 故障怎么处理",
    response="E03 故障表示主板损坏，需要更换主板，请联系售后。"
)
assert result.get("accuracy", 5) <= 2  # 编造了解决方案
assert passed == False
```

### 重试机制测试

```python
# 模拟评估不通过的回复
# 验证: 是否触发了重试
# 验证: 重试后的回复是否改善了
# 验证: 达到 max_retries 后是否使用了兜底话术
```

### 端到端测试

| 测试用例 | 预期行为 |
|---------|---------|
| 正常问题（有参考资料） | 一次通过 |
| 需要多步推理的问题 | 一次通过（ReAct 内部自己多轮） |
| 模型可能编造的场景 | 可能被拦截，重新生成更准确的回复 |
| 完全无关的问题 | 评估打低分，可能触发兜底 |
| 报告生成场景 | 评估不应干扰中间件标记 |

## 3.11 阈值调优策略

1. **初始阶段**: `pass_threshold=3.0`（宽松），`max_retries=1`
2. **收集数据**: 运行 1 周，记录所有评估日志
3. **人工抽检**: 随机抽 50 个 case 人工标注
4. **校准阈值**: 根据人工标注调整 pass_threshold
5. **收紧**: 确认评估器准确后，逐步提高阈值

## 3.12 已知局限

1. **评估器本身也可能出错**: LLM 做评分不是 100% 准确的。可能误杀好的回复，也可能放过差的回复
2. **每次评估增加延迟**: 至少 1-2 秒。如果评估频繁触发重试，用户体验会受影响
3. **参考资料缺失**: 当前评估 prompt 中 context 参数是可选的。如果 rag_summarize 是通过 Agent 工具调用的，评估时可能拿不到参考资料。需要考虑是否在工具执行后把参考资料也传给评估器
4. **流式输出兼容**: 当前方案改为全量评估后一次性返回，丢失了流式效果。如果用户体验要求流式，需要用异步评估方案

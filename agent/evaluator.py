"""
A2A 评估 Agent —— 对客服回复做多维度质量校验
不达标则生成反馈、触发重生成，兜底返回安全话术
"""
import sys
import os
import re
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from utils.config_handler import agent_config
from utils.path_tool import get_abs_path
from utils.logger import logger


class ResponseEvaluator:
    """回复质量评估器 —— 评分 + 反馈 + 重生成"""

    def __init__(self):
        cfg = agent_config.get("evaluator", {})

        self.enabled = cfg.get("enabled", True)
        if not self.enabled:
            logger.info("[Evaluator] 评估已关闭，走原有逻辑")
            return  # 不再初始化模型和 prompt

        model_name = cfg.get("model_name", "Qwen/Qwen2.5-7B-Instruct")
        temperature = cfg.get("temperature", 0.0)
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "https://api.siliconflow.cn/v1")

        self.model = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

        # 维度定义
        dims = cfg.get("dimensions", {})
        self.dimensions = {
            name: dims[name]["weight"]
            for name in ["relevance", "accuracy", "safety", "completeness"]
            if name in dims
        }
        # 确保权重顺序稳定
        self.dim_keys = ["relevance", "accuracy", "safety", "completeness"]

        self.pass_threshold = cfg.get("pass_threshold", 7.0)
        self.max_retries = cfg.get("max_retries", 2)
        self.fallback_message = cfg.get(
            "fallback_message",
            "抱歉，我暂时无法准确回答您的问题。建议您联系人工客服获取更专业的帮助。",
        )

        # 加载 prompt 模板
        self.eval_prompt = self._load_prompt("prompts/evaluator.txt")
        self.regenerate_prompt = self._load_prompt("prompts/regenerate.txt")

        logger.info(
            f"[Evaluator] 初始化完成 model={model_name} "
            f"base_url={base_url} "
            f"threshold={self.pass_threshold} max_retries={self.max_retries}"
        )

    # ---- 公开 API ----

    def evaluate(
        self, query: str, response: str, context: str = ""
    ) -> tuple:
        """
        评估一条回复的质量。

        Args:
            query: 用户原始问题
            response: 客服回复内容
            context: 检索上下文（可选）

        Returns:
            (total_score, eval_result, should_pass)
            - total_score: float，加权总分
            - eval_result: dict，各维度分值及简要说明
            - should_pass: bool，是否达到通过阈值
        """
        if not self.enabled:
            return (10.0, {"brief": "评估未启用，默认放行"}, True)

        prompt_text = self.eval_prompt.format(
            query=query, response=response, context=context or "无"
        )

        try:
            raw_output = self.model.invoke(prompt_text).content
            logger.debug(f"[Evaluator] 原始输出:\n{raw_output}")
            parsed = self._parse_json(raw_output)
        except Exception as e:
            import traceback
            logger.warning(
                f"[Evaluator] 评估调用失败，默认放行: {e}\n"
                f"{traceback.format_exc()}"
            )
            return (
                self.pass_threshold,
                {"brief": f"评估调用异常，默认放行: {e}"},
                True,
            )

        if parsed is None:
            # JSON 解析彻底失败，尝试正则从文本中直接抠维度分数
            parsed = self._parse_by_regex(raw_output)
        if parsed is None:
            logger.warning(
                f"[Evaluator] JSON + Regex 解析均失败，默认放行\n"
                f"原始输出(前500字): {raw_output[:500]}"
            )
            return (
                self.pass_threshold,
                {"brief": "评估结果解析失败，默认放行"},
                True,
            )

        # 自己按权重算总分，不信任模型返回的计算值
        total_score = self._calc_weighted_score(parsed)
        should_pass = total_score >= self.pass_threshold

        logger.info(
            f"[Evaluator] 评分完成 total={total_score:.2f} "
            f"pass={should_pass} dims={ {k: parsed.get(k) for k in self.dim_keys} }"
        )

        return (total_score, parsed, should_pass)

    def generate_feedback(self, eval_result: dict) -> str:
        """
        将评估结果转换为自然语言反馈，用于驱动重生成。

        Args:
            eval_result: evaluate() 返回的 eval_result 字典

        Returns:
            自然语言反馈字符串
        """
        dim_labels = {
            "relevance": "相关性",
            "accuracy": "准确性",
            "safety": "安全性",
            "completeness": "完整性",
        }
        weights = {
            k: self.dimensions.get(k, 0.0) for k in self.dim_keys
        }

        lines = []
        for key in self.dim_keys:
            label = dim_labels.get(key, key)
            score = eval_result.get(key, "?")
            weight = weights.get(key, 0.0)
            lines.append(f"- {label}(权重{weight:.0%})：{score}/10")

        total = self._calc_weighted_score(eval_result)
        lines.append(f"\n加权总分：{total:.2f}/10 (通过线：{self.pass_threshold})")

        brief = eval_result.get("brief", "")
        if brief:
            lines.append(f"\n综合点评：{brief}")

        return "\n".join(lines)

    def regenerate(self, query: str, original_response: str, feedback: str) -> str:
        """
        带评估反馈重新生成回复。

        Args:
            query: 用户原始问题
            original_response: 被驳回的原始回复
            feedback: generate_feedback() 产出的反馈文本

        Returns:
            重新生成后的回复
        """
        prompt_text = self.regenerate_prompt.format(
            query=query,
            original_response=original_response,
            feedback=feedback,
        )

        try:
            result = self.model.invoke(prompt_text)
            return result.content.strip()
        except Exception as e:
            logger.error(f"[Evaluator] 重生成调用失败: {e}")
            # 重生成失败时返回兜底话术
            return self.fallback_message

    # ---- 内部方法 ----

    @staticmethod
    def _load_prompt(relative_path: str) -> str:
        """加载 prompt 模板文件"""
        abs_path = get_abs_path(relative_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def _calc_weighted_score(self, parsed: dict) -> float:
        """根据配置的权重独立计算加权总分"""
        total = 0.0
        for key in self.dim_keys:
            score = parsed.get(key, 7)  # 缺失维度默认 7 分（偏向放行）
            weight = self.dimensions.get(key, 0.0)
            total += score * weight
        return round(total, 2)

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        """
        容错 JSON 解析。
        尝试顺序：直接解析 → 去 Markdown 代码块 → 正则提取首段 JSON
        → 单引号替换 → 去尾逗号 → 提取含维度 key 的最大 JSON 块
        全部失败则返回 None，调用方默认放行。
        """
        if not raw or not raw.strip():
            return None

        candidates = []

        # 1) 原始文本
        candidates.append(raw.strip())

        # 2) 去 ```json / ``` 包裹（可能跨多行）
        stripped = raw.strip()
        for tag in ("```json", "```"):
            if stripped.startswith(tag):
                idx = stripped.index("\n") if "\n" in stripped else len(tag)
                stripped = stripped[idx:].strip()
                if stripped.endswith("```"):
                    stripped = stripped[:-3].strip()
                break
        candidates.append(stripped)

        # 3) 用正则找所有可能的 {...} 块，按长度降序（大的更可能是完整 JSON）
        brace_blocks = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL)
        for block in sorted(brace_blocks, key=len, reverse=True):
            candidates.append(block.strip())

        for cand in candidates:
            if not cand:
                continue
            # 尝试直接解析
            result = ResponseEvaluator._try_load(cand)
            if result:
                return result
            # 尝试单引号替换后解析（小模型常犯）
            result = ResponseEvaluator._try_load(cand.replace("'", '"'))
            if result:
                return result
            # 尝试去尾逗号（JSON 不允许尾逗号）
            cleaned = re.sub(r",\s*([}\]])", r"\1", cand)
            result = ResponseEvaluator._try_load(cleaned)
            if result:
                return result
            # 组合：单引号 + 去尾逗号
            try:
                result = ResponseEvaluator._try_load(
                    re.sub(r",\s*([}\]])", r"\1", cand.replace("'", '"'))
                )
                if result:
                    return result
            except Exception:
                continue
            # JS 对象格式：无引号 key → 加双引号
            js_fixed = re.sub(
                r'([\{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', cand
            )
            if js_fixed != cand:
                result = ResponseEvaluator._try_load(js_fixed)
                if result:
                    return result
                # JS + 尾逗号
                result = ResponseEvaluator._try_load(
                    re.sub(r",\s*([}\]])", r"\1", js_fixed)
                )
                if result:
                    return result
                # JS + 单引号值
                result = ResponseEvaluator._try_load(js_fixed.replace("'", '"'))
                if result:
                    return result
                # JS + 单引号 + 尾逗号
                result = ResponseEvaluator._try_load(
                    re.sub(r",\s*([}\]])", r"\1", js_fixed.replace("'", '"'))
                )
                if result:
                    return result

        return None

    @staticmethod
    def _parse_by_regex(raw: str) -> dict | None:
        """
        JSON 解析彻底失败时的终极兜底：用正则从文本中直接抠各维度分数。
        匹配模式如: relevance:8  /  "relevance": 8  /  相关性 8分 等。
        至少找到 2 个维度分数才返回，否则返回 None。
        """
        # 维度名可能的关键词映射
        key_aliases = {
            "relevance": ["relevance", "相关性"],
            "accuracy": ["accuracy", "准确性"],
            "safety": ["safety", "安全性"],
            "completeness": ["completeness", "完整性"],
        }

        result = {}
        for dim, aliases in key_aliases.items():
            for alias in aliases:
                # 匹配: key后紧跟冒号(可含引号) + 数字(1-10)
                m = re.search(
                    rf'(?:"?{re.escape(alias)}"?)\s*[:：=]\s*(\d+)',
                    raw, re.IGNORECASE
                )
                if m:
                    score = int(m.group(1))
                    if 1 <= score <= 10:
                        result[dim] = score
                        break

        # 至少找到 2 个维度才算成功，否则数据太不可靠
        if len(result) >= 2:
            logger.info(f"[Evaluator] Regex 兜底提取成功: {result}")
            return result
        return None

    @staticmethod
    def _try_load(text: str) -> dict | None:
        """尝试 json.loads，校验是否包含维度 key"""
        try:
            result = json.loads(text)
            if isinstance(result, dict) and any(
                k in result for k in ("relevance", "accuracy", "safety", "completeness")
            ):
                return result
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return None


# ---- 模块级便捷实例 ----
_default_evaluator = None


def get_evaluator() -> ResponseEvaluator:
    """获取全局评估器实例（懒加载）"""
    global _default_evaluator
    if _default_evaluator is None:
        _default_evaluator = ResponseEvaluator()
    return _default_evaluator

"""
分层记忆管理模块

架构：
  短期记忆（最近 N 轮原文）
  + 对话摘要（超出窗口的历史 → LLM 压缩）
  + 用户画像（设备型号/故障/偏好 → LLM 提取）
  + 工作记忆（当前任务上下文）

存储：Redis（key: memory:{session_id}，JSON 序列化）
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import redis
from typing import List, Dict, Optional
from utils.config_handler import agent_config
from utils.logger import logger
from utils.path_tool import get_abs_path
import yaml


def _load_memory_config() -> dict:
    """加载 memory.yml 配置"""
    cfg_path = get_abs_path("config/memory.yml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("memory", {})


class MemoryManager:
    """
    分层记忆管理器

    用法：
        mm = MemoryManager(session_id, chat_model)
        context = mm.get_context()          # 获取注入 system prompt 的记忆文本
        recent = mm.get_recent_messages()   # 获取最近 N 轮消息
        mm.update_memory(user_msg, ai_msg)  # 每轮结束后更新
    """

    def __init__(self, session_id: str, chat_model):
        self.session_id = session_id
        self.chat_model = chat_model
        self.cfg = _load_memory_config()

        # Redis
        redis_cfg = agent_config["redis"]
        redis_host = os.environ.get("REDIS_HOST", redis_cfg["host"])
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_cfg["port"],
            db=redis_cfg["db"],
            decode_responses=True,
            socket_timeout=5,
        )
        try:
            self.redis.ping()
        except Exception:
            logger.warning("[Memory] Redis 不可用，Memory 降级为内存模式")

        # 加载状态
        self.state = self._load()

    # ------------------------------------------------------------------
    # 状态持久化
    # ------------------------------------------------------------------
    @property
    def _redis_key(self) -> str:
        return f"memory:{self.session_id}"

    def _load(self) -> dict:
        try:
            raw = self.redis.get(self._redis_key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return {
            "short_term": [],      # [{"role":"user","content":...}, ...]
            "summary": "",          # 压缩后的对话摘要
            "profile": {},          # 用户画像 dict
            "working_memory": "",   # 当前任务
            "turn_count": 0,        # 总轮数
            "idle_since_task": 0,   # 任务相关度计数器
        }

    def _save(self):
        try:
            self.redis.setex(
                self._redis_key,
                agent_config["redis"].get("ttl", 2592000),
                json.dumps(self.state, ensure_ascii=False),
            )
        except Exception as e:
            logger.error(f"[Memory] 保存状态失败: {e}")

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def get_context(self) -> str:
        """返回注入对话的记忆上下文（放在 system prompt 之后）"""
        parts = []

        # 用户画像
        profile = self.state.get("profile", {})
        if profile:
            lines = ["[用户画像]"]
            if profile.get("device_model"):
                lines.append(f"  设备: {profile['device_model']}")
            issues = profile.get("main_issues", [])
            if issues:
                lines.append(f"  当前问题: {'; '.join(issues)}")
            resolved = profile.get("resolved_issues", [])
            if resolved:
                lines.append(f"  已解决: {'; '.join(resolved)}")
            if profile.get("preferences"):
                lines.append(f"  偏好: {profile['preferences']}")
            if profile.get("floor_type"):
                lines.append(f"  地面: {profile['floor_type']}")
            if profile.get("has_pets") is not None:
                lines.append(f"  养宠物: {'是' if profile['has_pets'] else '否'}")
            parts.append("\n".join(lines))

        # 对话摘要
        summary = self.state.get("summary", "")
        if summary:
            parts.append(f"[对话历史摘要]\n{summary}")

        # 工作记忆
        wm = self.state.get("working_memory", "")
        if wm:
            parts.append(f"[当前任务]\n{wm}")

        return "\n\n".join(parts) if parts else ""

    def get_recent_messages(self) -> List[Dict[str, str]]:
        """返回最近 N 轮对话（已格式化为 role/content）"""
        return list(self.state.get("short_term", []))

    def update_memory(self, user_msg: str, assistant_msg: str):
        """每轮对话后更新记忆"""
        st = self.state["short_term"]
        st.append({"role": "user", "content": user_msg})
        st.append({"role": "assistant", "content": assistant_msg[:500]})  # 截断过长回复

        self.state["turn_count"] += 1

        # 短期记忆裁剪 + 触发摘要
        max_turns = self.cfg.get("short_term", {}).get("max_turns", 5)
        max_msgs = max_turns * 2  # user + assistant per turn
        if len(st) > max_msgs:
            overflow = st[:-max_msgs]
            self.state["short_term"] = st[-max_msgs:]
            self._summarize(overflow)

        # 用户画像提取
        profile_cfg = self.cfg.get("profile", {})
        if profile_cfg.get("enabled") and self.state["turn_count"] % profile_cfg.get("extract_interval", 3) == 0:
            self._extract_profile()

        # 工作记忆：简单规则 — 用户连续追问同一主题则保留
        self._update_working_memory(user_msg, assistant_msg)

        self._save()

    # ------------------------------------------------------------------
    # 摘要压缩
    # ------------------------------------------------------------------
    def _summarize(self, overflow: List[dict]):
        """用 LLM 压缩超出窗口的对话"""
        cfg = self.cfg.get("summary", {})
        if not cfg.get("enabled", True):
            return

        # 加载 prompt 模板
        from utils.config_handler import prompts_config
        prompt_path = get_abs_path(prompts_config["memory_summary_prompt_path"])
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 格式化历史
        history_text = ""
        for msg in overflow:
            role = "用户" if msg["role"] == "user" else "客服"
            history_text += f"{role}: {msg['content']}\n"

        # 将已有摘要一并传入，一次 LLM 调用完成合并
        old_summary = self.state.get("summary", "")
        if old_summary:
            history_text = f"[已有的对话摘要]: {old_summary}\n\n[新增对话]:\n{history_text}"

        max_len = cfg.get("max_summary_length", 300)
        prompt = template.format(max_length=max_len, conversation_history=history_text)

        try:
            response = self.chat_model.invoke(prompt)
            self.state["summary"] = response.content.strip()
            logger.info(f"[Memory] 摘要已更新 ({len(self.state['summary'])} 字)")
        except Exception as e:
            logger.error(f"[Memory] 摘要生成失败: {e}")

    # ------------------------------------------------------------------
    # 用户画像提取
    # ------------------------------------------------------------------
    def _extract_profile(self):
        """用 LLM 提取用户画像（传入已有画像做增量合并）"""
        from utils.config_handler import prompts_config

        prompt_path = get_abs_path(prompts_config["memory_extract_prompt_path"])
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 收集用户消息
        all_msgs = self.state["short_term"] + []
        user_text = ""
        for msg in all_msgs:
            if msg["role"] == "user":
                user_text += f"用户: {msg['content']}\n"

        if not user_text.strip():
            return

        # 传入已有画像，让 LLM 做增量合并
        old_profile = json.dumps(self.state.get("profile", {}), ensure_ascii=False)
        prompt = template.format(
            user_messages=user_text,
            current_profile=old_profile,
        )

        try:
            response = self.chat_model.invoke(prompt)
            raw = response.content.strip()
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                new_profile = json.loads(match.group())
                # 智能合并：列表类字段追加去重
                merged = dict(self.state.get("profile", {}))
                for key, val in new_profile.items():
                    if val is None or val == [] or val == "":
                        continue
                    if key in ("main_issues", "resolved_issues", "auto_features"):
                        existing = merged.get(key, [])
                        if isinstance(val, list):
                            merged[key] = list(dict.fromkeys(existing + val))  # 保留旧 + 去重
                    elif key == "preferences":
                        old = merged.get(key, "")
                        if old and val != old:
                            merged[key] = f"{old}；{val}"
                        else:
                            merged[key] = val
                    else:
                        merged[key] = val
                self.state["profile"] = merged
                logger.info(f"[Memory] 用户画像已更新: device={merged.get('device_model')}, issues={merged.get('main_issues')}")
        except Exception as e:
            logger.error(f"[Memory] 画像提取失败: {e}")

    # ------------------------------------------------------------------
    # 工作记忆
    # ------------------------------------------------------------------
    def _update_working_memory(self, user_msg: str, assistant_msg: str):
        """维护工作记忆：检测用户是否在持续关注某个问题"""
        idle_limit = self.cfg.get("working_memory", {}).get("max_idle_turns", 3)

        # 问题/追问关键词
        question_kw = [
            "怎么", "如何", "为什么", "什么原因", "故障", "错误",
            "不工作", "怎么办", "不行", "还是", "仍然", "依然",
            "继续", "再问", "还有", "也", "另外", "再",
            "哪个", "哪种", "在哪里", "多久", "多少",
        ]

        # 排除纯寒暄（这些不算任务）
        chitchat = {"好", "好的", "谢谢", "嗯", "哦", "行", "可以", "ok", "OK", "明白", "知道了"}

        is_question = any(kw in user_msg for kw in question_kw)
        is_chitchat = user_msg.strip() in chitchat or len(user_msg) < 5

        if is_question and not is_chitchat:
            self.state["working_memory"] = f"用户正在询问: {user_msg[:200]}"
            self.state["idle_since_task"] = 0
        elif is_chitchat:
            # 寒暄不重置工作记忆，也不增加空闲计数
            pass
        else:
            self.state["idle_since_task"] = self.state.get("idle_since_task", 0) + 1
            if self.state["idle_since_task"] >= idle_limit:
                self.state["working_memory"] = ""

    # ------------------------------------------------------------------
    # 清除
    # ------------------------------------------------------------------
    def clear(self):
        """清除当前会话记忆"""
        self.state = {
            "short_term": [],
            "summary": "",
            "profile": {},
            "working_memory": "",
            "turn_count": 0,
            "idle_since_task": 0,
        }
        try:
            self.redis.delete(self._redis_key)
        except Exception:
            pass
        logger.info(f"[Memory] 会话 {self.session_id} 记忆已清除")

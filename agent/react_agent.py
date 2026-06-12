import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from utils.app_history import get_history
from agent.tools.agent_tools import rag_summarize, get_weather, get_user_id, get_user_location, get_current_date, fetch_external_data, fill_context_for_report
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from agent.evaluator import get_evaluator
import yaml
from utils.path_tool import get_abs_path


def _is_memory_enabled() -> bool:
    """读取 memory.yml 开关"""
    try:
        cfg_path = get_abs_path("config/memory.yml")
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("memory", {}).get("enabled", False)
    except Exception:
        return False


class ReactAgent():
    def __init__(self, session_id: str = "default_session"):
        """
        初始化Agent

        Args:
            session_id: 会话ID，用于关联会话历史
        """
        self.session_id = session_id
        self.memory_enabled = _is_memory_enabled()
        self.evaluator = get_evaluator()  # A2A 评估 Agent

        # 原有历史（memory 关闭时使用，或作为回退）
        self.history = get_history(session_id)

        # Memory 管理器
        self.memory_manager = None
        if self.memory_enabled:
            from utils.memory_manager import MemoryManager
            self.memory_manager = MemoryManager(session_id, chat_model)

        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, get_weather, get_user_id, get_user_location,
                   get_current_date, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch]
        )

    def execute_stream(self, query: str):
        """
        执行流式回答，自动保存会话历史
        Args:
            query: 用户输入
        """
        if self.memory_enabled and self.memory_manager is not None:
            # ---- Memory 模式：分层记忆 ----
            memory_context = self.memory_manager.get_context()
            recent = self.memory_manager.get_recent_messages()

            messages = []
            # 注入记忆上下文（摘要 + 画像 + 工作记忆）作为第一条 system 消息
            if memory_context:
                messages.append({"role": "system", "content": memory_context})
            for msg in recent:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": query})
        else:
            # ---- 原有模式：全量历史 ----
            history_messages = self.history.messages
            messages = []
            for msg in history_messages:
                role = "user" if msg.type == "human" else "assistant"
                messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": query})

        input_dict = {"messages": messages}

        # 流式返回结果
        response_chunks = []
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            # 仅输出不含 tool_calls 的 AI 消息（即最终回复），跳过中间推理和工具结果
            if latest_message.content and latest_message.type == "ai":
                if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                    continue
                response_chunks.append(latest_message.content.strip())
                yield latest_message.content.strip() + "\n"

        full_response = "".join(response_chunks)

        # ---- A2A 评估循环 ----
        final_response = full_response
        if self.evaluator is not None and self.evaluator.enabled:
            for retry in range(self.evaluator.max_retries + 1):
                score, eval_result, should_pass = self.evaluator.evaluate(
                    query, final_response
                )
                if should_pass:
                    break
                if retry < self.evaluator.max_retries:
                    feedback = self.evaluator.generate_feedback(eval_result)
                    final_response = self.evaluator.regenerate(
                        query, final_response, feedback
                    )
                    yield f"\n🔧 回复已优化：\n{final_response}\n"
                else:
                    final_response = self.evaluator.fallback_message
                    yield f"\n{final_response}\n"

        # 保存（以最终通过评估的回复为准）
        if self.memory_enabled and self.memory_manager is not None:
            self.memory_manager.update_memory(query, final_response)
            # 同时写一份到原有 Redis 历史（保留回退兼容）
            self.history.add_message(HumanMessage(content=query))
            self.history.add_message(AIMessage(content=final_response))
        else:
            self.history.add_message(HumanMessage(content=query))
            self.history.add_message(AIMessage(content=final_response))

    def clear_history(self):
        """清除当前会话的历史记录"""
        self.history.clear()
        if self.memory_manager is not None:
            self.memory_manager.clear()

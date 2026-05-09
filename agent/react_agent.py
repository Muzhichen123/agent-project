import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from utils.app_history import get_history
from agent.tools.agent_tools import rag_summarize, get_weather, get_user_id, get_user_location, get_current_month, fetch_external_data, fill_context_for_report
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch

class ReactAgent():
    def __init__(self, session_id: str = "default_session"):
        """
        初始化Agent
        
        Args:
            session_id: 会话ID，用于关联会话历史
        """
        self.session_id = session_id
        self.history = get_history(session_id)
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, get_weather, get_user_id, get_user_location,
                   get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch]
        )

    def execute_stream(self, query: str):
        """
        执行流式回答，自动保存会话历史
        
        Args:
            query: 用户输入
        """
        # 获取历史消息
        history_messages = self.history.messages
        
        # 构建完整消息列表
        messages = []
        for msg in history_messages:
            # 转换消息类型：human -> user, ai -> assistant
            role = "user" if msg.type == "human" else "assistant"
            messages.append({"role": role, "content": msg.content})
        messages.append({"role": "user", "content": query})
        
        input_dict = {"messages": messages}
        
        # 流式返回结果
        response_chunks = []
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                response_chunks.append(latest_message.content.strip())
                yield latest_message.content.strip() + "\n"
        
        # 保存会话历史
        full_response = "".join(response_chunks)
        self.history.add_message(HumanMessage(content=query))
        self.history.add_message(AIMessage(content=full_response))
    
    def clear_history(self):
        """清除当前会话的历史记录"""
        self.history.clear()

if __name__ == "__main__":
    # 🔥 修复3：无参实例化，完美匹配__init__
    agent = ReactAgent()
    # 传入用户问题
    for chunk in agent.execute_stream("给我生成我的个人报告"):
        print(chunk, end="", flush=True)
        time.sleep(0.1)
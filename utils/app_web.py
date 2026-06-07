# 应用web端
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from agent.react_agent import ReactAgent

# 标题
st.title("扫地机器人智能客服")
st.divider()

# 会话管理
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(time.time())# 会话ID，用于区分不同的会话

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent(session_id=st.session_state["session_id"])# 创建agent智能体实例

# 显示历史消息（从Redis读取）
for msg in st.session_state["agent"].history.messages:
    st.chat_message(msg.type).write(msg.content)

# 用户输入提示词
prompt = st.chat_input("请输入您的问题")
if prompt:
    st.chat_message("user").write(prompt)
    
    with st.spinner("智能客服思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)
        
        def capture(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                yield chunk# 返回当前块，用于实时显示
        
        response_messages = []
        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))

# 清除历史按钮
if st.button("清除对话历史"):
    st.session_state["agent"].clear_history()
    st.rerun()
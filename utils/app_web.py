# 应用web端
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from agent.react_agent import ReactAgent

# 标题
st.title("智扫通机器人智能客服")
st.divider()

# 会话管理
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(time.time())

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent(session_id=st.session_state["session_id"])

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
                yield chunk
        
        response_messages = []
        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))

# 清除历史按钮
if st.button("清除对话历史"):
    st.session_state["agent"].clear_history()
    st.rerun()
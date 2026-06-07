"""
FastAPI 接口 — 将 Agent 包装成 HTTP API
启动: uvicorn utils.api:app --reload
文档: http://localhost:8000/docs
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel
from agent.react_agent import ReactAgent

app = FastAPI(title="智能扫地机器人客服 API")

# ── 请求体 ──
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# ── 接口 ──
@app.get("/")
async def root():
    return {"服务": "智能扫地机器人客服 API", "文档": "/docs"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """对话接口：发消息，返回 Agent 完整回复"""
    agent = ReactAgent(session_id=req.session_id)
    chunks = []
    for chunk in agent.execute_stream(req.message):
        chunks.append(chunk)
    return {"reply": "".join(chunks).strip(), "session_id": req.session_id}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """查历史：返回指定会话的消息数量"""
    agent = ReactAgent(session_id=session_id)
    msgs = agent.history.messages
    return {"session_id": session_id, "count": len(msgs), "messages": str(msgs)}


@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """清除会话历史"""
    agent = ReactAgent(session_id=session_id)
    agent.clear_history()
    return {"session_id": session_id, "status": "已清除"}

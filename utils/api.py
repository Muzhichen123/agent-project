"""
FastAPI 接口 — 将 Agent 包装成 HTTP API
启动: uvicorn utils.api:app --host 0.0.0.0 --port 8000
文档: http://localhost:8000/docs
"""
import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.react_agent import ReactAgent

app = FastAPI(title="RoboServe — 智能客服 API")

# ── Agent 缓存（按 session 复用，避免每次请求重建） ──
_agents: dict = {}
_lock = threading.Lock()


def _get_agent(session_id: str) -> ReactAgent:
    """获取或创建 session 级别的 Agent 实例"""
    with _lock:
        if session_id not in _agents:
            _agents[session_id] = ReactAgent(session_id=session_id)
        return _agents[session_id]


# ── 请求体 ──
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# ── 接口 ──
@app.get("/")
async def root():
    return {"service": "RoboServe 智能客服 API", "docs": "/docs"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """对话接口：发送消息，返回 Agent 完整回复"""
    agent = _get_agent(req.session_id)
    chunks = []
    for chunk in agent.execute_stream(req.message):
        chunks.append(chunk)
    return {"reply": "".join(chunks).strip(), "session_id": req.session_id}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式对话接口：SSE 逐块返回"""
    agent = _get_agent(req.session_id)

    def generate():
        for chunk in agent.execute_stream(req.message):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """查询会话历史消息数量"""
    agent = _get_agent(session_id)
    msgs = agent.history.messages
    return {
        "session_id": session_id,
        "count": len(msgs),
        "messages": [
            {"role": m.type, "content": m.content[:200]} for m in msgs
        ],
    }


@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """清除会话历史"""
    agent = _get_agent(session_id)
    agent.clear_history()
    with _lock:
        _agents.pop(session_id, None)
    return {"session_id": session_id, "status": "已清除"}

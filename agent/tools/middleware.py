"""
中间件模块
"""
import sys
from pathlib import Path
# 当前文件是 agent/tools/middleware.py
# 向上退 2 级就是项目根目录 agent_project
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))
from langchain_core.messages import ToolMessage
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, AgentState, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from typing import Callable
from langgraph.types import Command
from utils.logger import logger
from langgraph.runtime import Runtime
from utils.prompt_loader import load_system_prompts, load_report_prompts
@wrap_tool_call
def monitor_tool(
    request,# 请求的数据封装
    handler:Callable[[ToolCallRequest],ToolMessage|Command],# 执行的函数本身
)->ToolMessage|Command:#工具执行监控
    logger.info(f"[tool monitor]执行工具:{request.tool_call['name']}")
    logger.info(f"[tool monitor]传入参数:{request.tool_call['args']}")
    try:
        result=handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}执行成功")

        if request.tool_call['name']=='fill_context_for_report':
            request.runtime.context["report"]=True
            # 为报告生成的场景动态注入上下文，为后续提示词切换提供上下文信息
            
        return result
    except Exception as e:
        logger.error(f"[tool monitor]工具{request.tool_call['name']}调用失败，异常信息：{str(e)}")
        return e
@before_model
def log_before_model(
    state:AgentState,# 状态对象 整个agent的状态记录
    runtime:Runtime,# 运行时对象 记录了整个执行过程中的上下文信息
):# 模型调前日志
    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")
    logger.debug(f"[log_before_model]{type(state['messages'][-1]).__name__} |{state['messages'][-1].content.strip()}")
    return None

@dynamic_prompt             #每一次在生成提示词前，调用此函数
def report_prompt_switch(request:ModelRequest): #动态切换提示词模板
    is_report=request.runtime.context.get("report",False)
    if is_report: # 如果是报告生成的场景
        return load_report_prompts()
    else:# 如果不是报告生成的场景
        return load_system_prompts()

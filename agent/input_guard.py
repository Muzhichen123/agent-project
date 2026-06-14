"""
输入安全过滤器 — 正则规则检测 Prompt 注入 / 越狱 / 信息窃取尝试
命中任一规则返回拦截原因，未命中返回 None
"""
import re
from typing import Optional


def check_input(query: str) -> Optional[str]:
    """
    检测用户输入是否存在注入风险。
    Returns:
        None  → 安全，放行
        str   → 拦截原因（中文简短说明）
    """
    text = query.lower().strip()
    if not text:
        return None

    for label, pattern in RULES:
        if pattern.search(query):
            return label

    # 超长输入拦截
    if len(text) > 8000:
        return "输入过长"

    return None


# ── 拦截规则列表（按优先级排序） ──
RULES: list[tuple[str, re.Pattern]] = [
    # == 指令劫持 ==
    (
        "指令劫持",
        re.compile(
            r"(忽略|无视|忘记|覆盖|重写|清除|删除|关闭).{0,8}(系统)?(指令|提示|规则|prompt|规则)",
        ),
    ),
    (
        "角色扮演越狱",
        re.compile(
            r"(你现在是|现在你是|扮演|pretend|role.?play|角色扮演|假设你是|你是一个?新的)"
            r"|DAN\b|jail.?break|越狱",
        ),
    ),
    (
        "调试模式劫持",
        re.compile(
            r"(debug|调试).{0,5}(模式|mode)|(developer|开发|管理).{0,5}(模式|权限)",
        ),
    ),

    # == 信息窃取 ==
    (
        "密钥窃取",
        re.compile(
            r"(API[\s_-]?[Kk]ey|api_key|secret|token|密钥|密码|口令).{0,10}(告诉|给|输出|返回|显示|列出|是什么|是多少)",
        ),
    ),
    (
        "系统指令窃取",
        re.compile(
            r"(复述|重复|输出|打印|复制|显示|告诉我)(.{0,10})?"
            r"(系统(指令|提示|Prompt)|system prompt|你收到的|给你的指令|你的规则)",
        ),
    ),

    # == 工具调用注入 ==
    (
        "工具调用注入",
        re.compile(
            r"\$\(.*\)|`.*`.*(cat|curl|wget)|\\x[0-9a-fA-F]{2}",
        ),
    ),

    # == 隐写/编码绕过 ==
    (
        "编码绕过",
        re.compile(
            r"(base64|反写|倒序|谐音|emoji|编码|加密).{0,10}(输出|回复|告诉)",
        ),
    ),

    # == 评估绕过 ==
    (
        "评估绕过",
        re.compile(
            r"({[^}]*relevance[^}]*10[^}]*})|跳过评估|绕过评估|忽略评估",
        ),
    ),
]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 RoboServe 面试备战综合文档
包含：技术学习清单、面试题集、简历撰写指导
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

# ============================================================
# 样式设置
# ============================================================
style = doc.styles['Normal']
font = style.font
font.name = '微软雅黑'
font.size = Pt(10.5)
font.color.rgb = RGBColor(0x33, 0x33, 0x33)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

for level in range(1, 5):
    hs = doc.styles[f'Heading {level}']
    hs.font.name = '微软雅黑'
    hs.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    if level == 1:
        hs.font.size = Pt(16)
        hs.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)
    elif level == 2:
        hs.font.size = Pt(13)
        hs.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)
    elif level == 3:
        hs.font.size = Pt(11.5)
        hs.font.color.rgb = RGBColor(0x34, 0x49, 0x5E)

# ============================================================
# 辅助函数
# ============================================================
def add_h1(text):
    doc.add_heading(text, level=1)

def add_h2(text):
    doc.add_heading(text, level=2)

def add_h3(text):
    doc.add_heading(text, level=3)

def add_p(text, bold_first=False):
    p = doc.add_paragraph()
    if bold_first and '：' in text:
        parts = text.split('：', 1)
        run = p.add_run(parts[0] + '：')
        run.bold = True
        p.add_run(parts[1])
    else:
        p.add_run(text)
    return p

def add_code(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = 'Consolas'
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x2D, 0x2D, 0x2D)
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    pPr = p._element.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'F5F7FA')
    pPr.append(shd)
    return p

def add_qa(q, a):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run('Q：' + q)
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
    run.font.size = Pt(10.5)
    p2 = doc.add_paragraph()
    p2.paragraph_format.left_indent = Cm(0.5)
    p2.paragraph_format.space_after = Pt(8)
    r2 = p2.add_run('A：' + a)
    r2.font.color.rgb = RGBColor(0x27, 0xAE, 0x60)

def add_tip(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    run = p.add_run('💡 ' + text)
    run.font.color.rgb = RGBColor(0xE6, 0x7E, 0x22)
    run.font.size = Pt(10)

def add_table(headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(10)
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ''
            cell.paragraphs[0].add_run(str(val)).font.size = Pt(10)
    doc.add_paragraph('')

def add_page_break():
    doc.add_page_break()

# ============================================================
# 封面
# ============================================================
for _ in range(6):
    doc.add_paragraph('')

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('大三实习面试备战指南')
run.bold = True
run.font.size = Pt(28)
run.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = subtitle.add_run('项目介绍 \u00d7 八股文 \u00d7 算法入门 \u00d7 简历指导')
run2.font.size = Pt(16)
run2.font.color.rgb = RGBColor(0x7F, 0x8C, 0x8D)

doc.add_paragraph('')
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run('智能扫地机器人客服系统 | RAG + ReAct Agent + A2A 评估').font.size = Pt(12)

doc.add_paragraph('')
ver = doc.add_paragraph()
ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
ver.add_run('更新日期：2026年6月12日 | 全链路已跑通').font.size = Pt(10)

add_page_break()

# ============================================================
# 第零章：大三实习面试是什么样的（重要！先看这里）
# ============================================================
add_h1('第零章：大三实习面试是什么样的')

add_p('面试官面对大三实习生，心里只想三件事：')

add_table(
    ['面试官心理', '你要怎么证明'],
    [
        ['\u2460 这个人能不能学得动？', '用项目证明——"我独立从0搭建了这个系统，从架构到代码到调试"'],
        ['\u2461 基础扎不扎实？', '八股文能答上来——"这个学校学过，项目里也用到"'],
        ['\u2462 沟通有没有问题？', '说话清楚、态度积极、不会就说"这个我还没学到，但我可以试着分析"'],
    ]
)

add_h2('面试时间分配（大三实习真实比例）')

add_code('自我介绍+项目介绍   \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588 40%  \u2190 最重要！决定第一印象\n八股文              \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588 30%  \u2190 实习生必考，项目没覆盖的部分\n技术基础 + 算法       \u2588\u2588\u2588\u2588\u2588 15%  \u2190 可能考 Easy~Medium\n项目深挖（可能没有）   \u2588\u2588 10%  \u2190 不要主动展开你不懂的\n反问环节              \u2588 5%     \u2190 准备2-3个问题')

add_warn = doc.add_paragraph()
add_warn.paragraph_format.left_indent = Cm(0.3)
r = add_warn.add_run('\u26a0\ufe0f \u4e0d\u8981\u628a\u65f6\u95f4\u82b1\u5728\u6df1\u7a76 RRF \u53c2\u6570\u3001Cross-Encoder\u5185\u90e8\u539f\u7406\u8fd9\u4e9b\u4e1c\u897f\u4e0a\u2014\u2014\u5b9e\u4e60\u751f\u9762\u8bd5\u51e0\u4e4e\u4e0d\u4f1a\u95ee\u5230\uff01')
r.font.color.rgb = RGBColor(0xE6, 0x7E, 0x22)
r.font.size = Pt(10)
r.bold = True

add_code('复习优先级：\n\U0001f534 P0 项目介绍 + 八股文（60%的时间）\n\U0001f7e1 P1 LeetCode算法 + 项目技术点（30%的时间）\n\U0001f7e2 P2 深度技术（A2A评估、Memory摘要质量等）（10%，了解即可）')

add_h2('本指南的使用方式')
add_p('这份文档按面试真实顺序编排，建议按以下顺序准备：')

add_code('第1步：第一部分 \u2192 练好"介绍项目"（2分钟版 + 30秒版），这是面试第一问\n第2步：第二部分 \u2192 八股文突击（Python \u2192 操作系统 \u2192 网络 \u2192 数据库）\n第3步：第三部分 \u2192 LeetCode 每天刷2-3题，保持手感\n第4步：第四部分 \u2192 简历优化 + 投递策略\n第5步：附录 \u2192 面试前检查清单 + 反问问题准备')

add_page_break()

# ============================================================
# 第一部分：项目介绍（面试的 40%）
# ============================================================
add_h1('第一部分：如何介绍你的项目')

add_p('面试第一问就是"介绍一下你的项目"。准备三个版本，根据面试官的问法切换。')

add_h2('版本 1：2分钟完整版（"先自我介绍一下"）')

add_code('0~20秒    我是XX学校XX专业大三学生，最近独立开发了一个智能客服系统 RoboServe。\n\n20~60秒   系统做什么：针对扫地机器人的故障排查、使用咨询、天气查询和报告生成。\n         技术栈：Python + LangChain ReAct Agent + ChromaDB + Redis + Streamlit。\n\n60~100秒  三个核心亮点：\n         \u2460 混合检索——Dense向量 + BM25关键词 + RRF融合 + Cross-Encoder精排，四阶段保障召回质量\n         \u2461 Memory分层管理——短期记忆/摘要/画像/工作记忆，解决长对话token爆炸\n         \u2462 A2A评估Agent——独立打分（相关性/准确性/安全性/完整性），不达标触发重生成\n\n100~120秒 全链路已跑通，知识库119条文档。LLM接通义千问，评估用硅基流动免费模型。')

add_h2('版本 2：30秒精简版（"简单介绍一下项目"）')

add_code('我做了一个智能客服系统，基于 LangChain ReAct Agent。\n检索用了混合检索——Dense向量 + BM25 + RRF融合 + Cross-Encoder精排，\n四阶段保障召回质量。还做了Memory分层管理和A2A评估Agent做质量把关。\n技术栈 Python + LangChain + ChromaDB + Redis + Streamlit。')

add_h2('版本 3：展开版（面试官表现出兴趣时）')

add_p('按"做什么 \u2192 怎么做 \u2192 难点 \u2192 收获"结构：')

add_code('用户提问 \u2192 ReAct Agent判断意图 \u2192 调用工具。\n知识类走 RAG：两路并行检索（Dense向量 + BM25关键词）\u2192 RRF融合 \u2192 Cross-Encoder精排 \u2192 top3文档喂LLM生成。\n\n还做了几个设计：\n- Memory分层（四层替代全量历史）\n- A2A评估（四维度打分+重试回路）\n- 三级降级（BGE \u2192 TF-IDF \u2192 取前N）\n- 开关设计（每个模块可独立开关）\n\n最大难点：Python依赖链问题——sentence_transformers间接依赖torch几百MB，\n启动慢。方案：延迟加载，只在需要时才import。')

add_h2('介绍项目的避坑指南')

add_table(
    ['不要说', '要说'],
    [
        ['"大部分代码是 AI 写的"', '"我设计了架构，AI辅助实现"——强调你的设计决策'],
        ['列一堆技术名词但说不清为什么', '每个技术后面跟一句"为什么"和"解决了什么"'],
        ['"这是一个简单的xx系统"', '"这是一个面向YY场景的XX系统"——不要说简单'],
        ['照背名词，被追问就卡住', '只说自己真的理解的部分，不被追问就不主动展开'],
    ]
)

add_page_break()

# ============================================================
# 第二部分：八股文高频题（面试的 30%）
# ============================================================
add_h1('第二部分：八股文高频题')

add_p('以下是大三实习面试中最高频的八股文题目。按 Python \u2192 操作系统 \u2192 计算机网络 \u2192 数据库 顺序排列。每道题都给出了"实习生能讲出来的版本"——不要求背定义，能说清楚思想就行。')

add_h2('一、Python 基础（最容易结合项目问）')

add_qa('\u2753 列表和元组的区别？什么时候用哪个？',
    '列表可变（可以增删改），元组不可变（创建后不能改）。项目里我用元组存配置参数（如 (host, port)），因为不需要改；用列表存可变数据（如检索结果列表）。另外元组可以作为字典的 key，列表不行。')

add_qa('\u2753 装饰器是什么？你项目里用过吗？',
    '装饰器是一个函数，接收一个函数作为参数，返回一个新的函数，不修改原函数但增加额外功能。项目里 LangChain 的 @tool 就是一个装饰器——它把我的普通函数变成 LLM 可以调用的工具，自动生成名称、描述和参数 schema。')

add_qa('\u2753 生成器和迭代器的区别？',
    '迭代器是可以一个一个取值的对象（有 __next__ 方法），生成器是一种特殊的迭代器，用 yield 关键字返回数据，不用一次性把所有数据加载到内存。适用场景：遍历大文件或大量数据时用生成器省内存。')

add_qa('\u2753 Python 的 GIL 是什么？',
    'GIL 是全局解释器锁（Global Interpreter Lock）。同一时刻只有一个线程能执行 Python 字节码。所以 Python 多线程在 CPU 密集型任务上不能加速，但 IO 密集型（如网络请求）可以——因为等待 IO 时会释放 GIL。项目里接 LLM API 就是 IO 密集型，多线程有效。')

add_qa('\u2753 深拷贝和浅拷贝的区别？',
    '浅拷贝只复制对象本身（外层），内部嵌套的对象还是共享引用。深拷贝递归复制所有层级的对象，完全独立。import copy 库：copy.copy() 浅，copy.deepcopy() 深。项目里处理配置字典时用深拷贝避免无意间修改原始配置。')

add_qa('\u2753 list.append() 和 list.extend() 的区别？',
    'append 把整个参数作为一个元素加入；extend 把参数里的每个元素逐个加入。比如 a=[1,2]，a.append([3,4]) \u2192 [1,2,[3,4]]，a.extend([3,4]) \u2192 [1,2,3,4]。')

add_h2('二、操作系统（每轮面试大概率考1-2题）')

add_qa('\u2753 进程和线程的区别？',
    '进程是资源分配的基本单位，线程是 CPU 调度的基本单位。进程间内存隔离（一个进程挂了不影响别的），线程共享进程的内存（一个线程崩溃可能影响整个进程）。项目里没用多进程，但如果要跑多个 Agent 实例并行处理请求，可以用线程池。')

add_qa('\u2753 什么是死锁？怎么避免？',
    '两个或多个线程互相等待对方释放资源，形成循环等待，谁都动不了。四个必要条件：互斥、持有等待、不可剥夺、循环等待。破坏任意一个就行。常用方案：统一加锁顺序（所有线程按相同顺序获取锁），或者用超时机制。')

add_qa('\u2753 虚拟内存是什么？有什么好处？',
    '让每个进程以为自己拥有连续完整的地址空间，但实际物理内存可以是不连续的碎片。好处：进程间内存隔离（只看得到自己的地址空间），可以运行比物理内存大的程序（部分换到磁盘），安全。')

add_qa('\u2753 什么是上下文切换？开销大吗？',
    'CPU 从一个进程/线程切换到另一个时，需要保存当前状态（寄存器、PC指针等）并加载下一个的状态。开销不小——涉及保存和恢复大量寄存器、TLB 刷新、CPU 缓存失效。所以线程不是越多越好。')

add_h2('三、计算机网络（必考，每轮大概率有1题）')

add_qa('\u2753 HTTP 和 HTTPS 的区别？',
    'HTTPS = HTTP + SSL/TLS 加密。HTTP 明文传输（密码裸奔），HTTPS 加密传输（防窃听和篡改）。默认端口也不同：HTTP 80，HTTPS 443。项目里调用 LLM API 全部用的 HTTPS。')

add_qa('\u2753 GET 和 POST 的区别？',
    'GET 参数在 URL 里（有长度限制），用于获取数据；POST 参数在请求体里（无长度限制），用于提交数据。GET 是幂等的（多次请求结果相同），POST 不一定。GET 可以被浏览器缓存和收藏，POST 不行。')

add_qa('\u2753 TCP 三次握手的过程？',
    '客户端发 SYN（我要连接），服务端回 SYN+ACK（收到，我也准备好了），客户端再发 ACK（确认）。三次后双方确认收发能力正常。为什么不是两次？因为两次只能确认客户端到达服务器，不能确认服务器到达客户端，而且无法防止旧连接请求的问题。')

add_qa('\u2753 TCP 和 UDP 的区别？用什么场景？',
    'TCP 面向连接、可靠（丢包重传）、有序、流量控制，但慢。UDP 无连接、不可靠、无序，但快。TCP 用于 HTTP、文件传输；UDP 用于视频通话、实时游戏。你项目里接 API 走 HTTP，底层就是 TCP。')

add_qa('\u2753 HTTP 状态码 200/301/404/500 分别是什么意思？',
    '200 OK 成功；301 永久重定向；404 资源不存在；500 服务器内部错误。项目中调用硅基流动 API 遇到过 403（禁止访问 / 余额不足），属于 4xx 客户端错误。')

add_qa('\u2753 Cookie 和 Session 的区别？',
    'Cookie 存在浏览器端，Session 存在服务器端。Session 一般通过 Cookie 里的 Session ID 来关联。项目里 Redis 存的就是会话历史（类似 Session），session_id 就是关联 key。')

add_h2('四、数据库（实习生大概率被问索引和 SQL 优化）')

add_qa('\u2753 索引是什么？什么时候该加索引？',
    '索引就像书的目录，加快查询速度但减慢写入（插入/更新/删除都要维护索引）。该加：经常用作 WHERE 条件的列、ORDER BY 的列、JOIN 的关联列。不该加：频繁更新的列、区分度低的列（如性别只有男女）、小表。')

add_qa('\u2753 什么是 SQL 注入？怎么防止？',
    '用户输入恶意 SQL 代码来篡改查询逻辑。比如输入 password = "1\' OR \'1\'=\'1" 绕过密码验证。防范：用参数化查询（Prepared Statement），不直接拼接 SQL 字符串。ORM 框架一般自带防护。')

add_qa('\u2753 Redis 和 MySQL 的区别？什么时候用 Redis？',
    'Redis 是内存数据库（快但存不了太多），MySQL 是磁盘关系型数据库（慢但能存海量数据）。Redis 适合缓存热点数据、会话存储（你项目里存对话历史）、计数器、消息队列。MySQL 适合持久化存储结构化数据。')

add_qa('\u2753 事务的 ACID 是什么意思？',
    'Atomicity 原子性（要么全做要么全不做）、Consistency 一致性（事务前后数据满足约束）、Isolation 隔离性（并发事务互不干扰）、Durability 持久性（提交后数据永久保存）。面试能说出这四个词的中英文就算过关。')

add_qa('\u2753 Redis 为什么快？',
    '四个原因：纯内存操作（不读磁盘）、单线程模型（无锁竞争，但要结合 IO 多路复用）、高效的数据结构（跳表、压缩列表等）、IO 多路复用（一个线程监听多个连接）。你项目里用 Redis 存对话历史，TTL 30天过期。')

add_page_break()

# ============================================================
# 第三部分：LeetCode 算法入门
# ============================================================
add_h1('第三部分：LeetCode 算法入门')

add_p('大三实习算法题不会很难。大概率 Easy，偶尔 Medium。重点是知道套路，能写出来。以下是最高频的 6 类题型。')

add_h2('刷题策略')

add_code('每天花 1 小时，刷 2-3 题。先用 5-15 分钟自己想，想不出来就看题解，理解了再自己写一遍。\n重点是"见过这类题"——大部分算法题就是"你见过就能做，没见过就卡住"。\n不需要刷几百题，50-80 道覆盖主要题型就够了。')

add_h2('高频题型 + 必刷题目')

add_table(
    ['题型', '推荐题目', '难度', '为什么考'],
    [
        ['\u2460 哈希表', 'Two Sum (LC 1)', 'Easy', '考你知不知道字典 O(1) 查找'],
        ['\u2460 哈希表', 'Valid Anagram (LC 242)', 'Easy', '考字符计数，项目里 MD5 类似思路'],
        ['\u2461 双指针', 'Reverse String (LC 344)', 'Easy', '考 in-place 操作'],
        ['\u2461 双指针', 'Move Zeroes (LC 283)', 'Easy', '考数组元素的原地移动'],
        ['\u2462 链表', 'Reverse Linked List (LC 206)', 'Easy', '经典递归题，考指针操作'],
        ['\u2462 链表', 'Merge Two Sorted Lists (LC 21)', 'Easy', '考归并思想'],
        ['\u2463 栈/队列', 'Valid Parentheses (LC 20)', 'Easy', '经典栈应用，最高频面试题之一'],
        ['\u2464 树', 'Maximum Depth of Binary Tree (LC 104)', 'Easy', '递归入门题'],
        ['\u2465 动态规划', 'Climbing Stairs (LC 70)', 'Easy', 'DP 入门，斐波那契变体'],
    ]
)

add_h2('面试时怎么写代码？')

add_code('1. 先问清楚题意（输入输出、边界条件），不要闷头就写\n2. 先说思路再写代码——"暴力法可以做但 O(n^2)，我可以用哈希表 O(n)"\n3. 写完主动测试——拿一个简单例子跑一遍\n4. 卡住了也不要慌——说"这题我还在想，能不能给个提示"比死磕好')

add_h2('如果面试官不考算法')
add_p('很多时候实习生面试不考算法，而是考"Python 基础语法题"。比如：')

add_qa('\u2753 写一个函数反转字符串',
    'def reverse(s): return s[::-1]（一行搞定，Python 切片特性）')

add_qa('\u2753 用一行代码统计一个字符串里每个字符出现次数',
    'from collections import Counter;  result = Counter(s)')

add_qa('\u2753 列表去重怎么写',
    'list(set(my_list))  但会丢失顺序。要保留顺序：list(dict.fromkeys(my_list))')

add_page_break()

# ============================================================
# 第四部分：简历与投递
# ============================================================
add_h1('第四部分：简历撰写与投递策略')

add_h2('项目经历怎么写（可以直接复制到简历）')

add_code('\u300aRoboServe \u667a\u80fd\u5ba2\u670d\u7cfb\u7edf\u300bPython + LangChain + ChromaDB + Redis  2026.03 - 2026.06\n\u72ec\u7acb\u5f00\u53d1\n\n\u2022 \u57fa\u4e8e ReAct Agent \u6a21\u5f0f\u6784\u5efa\u667a\u80fd\u5ba2\u670d\u7cfb\u7edf\uff0c\u96c6\u6210 7 \u4e2a\u5de5\u5177\u51fd\u6570\uff08RAG\u68c0\u7d22\u3001\u5929\u6c14\u67e5\u8be2\u3001\u62a5\u544a\u751f\u6210\u7b49\uff09\uff0cLLM \u81ea\u4e3b\u51b3\u7b56\u5de5\u5177\u8c03\u7528\n\u2022 \u8bbe\u8ba1\u5e76\u5b9e\u73b0\u6df7\u5408\u68c0\u7d22\u67b6\u6784\uff1aDense\u5411\u91cf + BM25\u5173\u952e\u8bcd + RRF\u878d\u5408 + Cross-Encoder\u7cbe\u6392\uff0c\u56db\u9636\u6bb5\u4fdd\u969c\u53ec\u56de\u8d28\u91cf\n\u2022 \u5b9e\u73b0\u5206\u5c42 Memory \u673a\u5236\uff08\u77ed\u671f\u8bb0\u5fc6/\u6458\u8981/\u7528\u6237\u753b\u50cf/\u5de5\u4f5c\u8bb0\u5fc6\uff09\uff0c\u89e3\u51b3\u957f\u5bf9\u8bdd token \u7206\u70b8\u95ee\u9898\n\u2022 \u8bbe\u8ba1 A2A \u591a Agent \u8d28\u91cf\u8bc4\u4f30\u56de\u8def\uff0c\u56db\u7ef4\u5ea6\u6253\u5206\uff0c\u4e0d\u8fbe\u6807\u89e6\u53d1\u91cd\u751f\u6210 + \u515c\u5e95\u7b56\u7565')
add_tip = doc.add_paragraph()
add_tip.paragraph_format.left_indent = Cm(0.3)
r = add_tip.add_run('\U0001f4a1 \u8fd9\u6bb5\u63cf\u8ff0\u7528\u4e86\u201c\u72ec\u7acb\u5f00\u53d1\u201d\u201c\u8bbe\u8ba1\u5e76\u5b9e\u73b0\u201d\u7b49\u4e3b\u52a8\u52a8\u8bcd\uff0c\u7ed9\u4eba\u4f60\u4e3b\u5bfc\u4e86\u9879\u76ee\u7684\u611f\u89c9\u3002\u6570\u5b57\uff087\u4e2a\u5de5\u5177\u3001\u56db\u7ef4\u5ea6\u3001\u56db\u9636\u6bb5\uff09\u6bd4\u5f62\u5bb9\u8bcd\u66f4\u6709\u8bf4\u670d\u529b\u3002')
r.font.color.rgb = RGBColor(0xE6, 0x7E, 0x22)
r.font.size = Pt(10)

add_h2('技能特长怎么写')

add_code('''\u7f16\u7a0b\u8bed\u8a00\uff1aPython\uff08\u719f\u7ec3\uff0c\u4e3b\u8981\u5f00\u53d1\u8bed\u8a00\uff09\u3001SQL\uff08\u57fa\u7840\uff09
\u6846\u67b6/\u5de5\u5177\uff1aLangChain\u3001Streamlit\u3001FastAPI\uff08\u4e86\u89e3\uff09
\u6570\u636e\u5e93\uff1aChromaDB\uff08\u5411\u91cf\u6570\u636e\u5e93\uff09\u3001Redis\uff08\u7f13\u5b58/\u4f1a\u8bdd\uff09\u3001MySQL\uff08\u57fa\u7840\uff09
AI/LLM\uff1aRAG\u68c0\u7d22\u589e\u5f3a\u751f\u6210\u3001ReAct Agent\u3001Prompt Engineering
\u68c0\u7d22\u6280\u672f\uff1a\u6df7\u5408\u68c0\u7d22\uff08Dense+BM25\uff09\u3001RRF\u878d\u5408\u3001Cross-Encoder\u7cbe\u6392
\u5176\u4ed6\uff1aGit\u7248\u672c\u63a7\u5236\u3001Docker\uff08\u57fa\u7840\uff09\u3001YAML\u914d\u7f6e\u7ba1\u7406''')

add_h2('投递策略')

add_code('先海投 2~3 天\u2192 拿 3~5 个小公司面试练手\u2192 找到面试感觉\u2192 再精准投递目标公司\n\u6e20\u9053\u4f18\u5148\u7ea7\uff1a\u5185\u63a8 > \u5b98\u7f51\u62db\u8058 > Boss\u76f4\u8058 > \u62c9\u52fe > \u5b9e\u4e60\u50e7')

add_h2('关于学历')
add_p('面试官面实习生更看重项目和学习能力。不要回避学历，把话题引向实践能力：')
add_code('''"\u6211\u77e5\u9053\u5b66\u5386\u662f\u6211\u7684\u77ed\u677f\uff0c\u6240\u4ee5\u4ece\u5927\u4e8c\u5c31\u5728\u88dc\u5b9e\u8df5\u3002\u8fd9\u4e2a\u9879\u76ee\u662f\u6211\u72ec\u7acb\u4ece0\u642d\u5efa\u7684\uff0c
\u4ece\u67b6\u6784\u8bbe\u8ba1\u5230\u4ee3\u7801\u5b9e\u73b0\u5230\u8c03\u8bd5\u4f18\u5316\uff0c\u8fc7\u7a0b\u4e2d\u5b66\u5230\u4e86\u5f88\u591a\u8bfe\u5802\u4e0a\u5b66\u4e0d\u5230\u7684\u4e1c\u897f\u3002
\u6211\u76f8\u4fe1\u5b9e\u9645\u52a8\u624b\u80fd\u529b\u6bd4\u5b66\u5386\u66f4\u80fd\u8bf4\u660e\u95ee\u9898\u3002"''')

add_page_break()

# ============================================================
# 附录
# ============================================================
add_h1('附录：面试前检查清单 + 反问问题')

add_h2('面试前 1 小时')

add_code('''\u25a1 \u6253\u5f00\u9879\u76ee\uff0c\u8dd1\u4e00\u904d streamlit run utils/app_web.py\uff0c\u786e\u8ba4\u80fd\u8dd1\u901a
\u25a1 \u6253\u5f00 agent/react_agent.py\uff0c\u5feb\u901f\u8fc7\u4e00\u904d\u5173\u952e\u4ee3\u7801\u4f4d\u7f6e
\u25a1 \u5728\u8111\u6d77\u91cc\u8fc7\u4e00\u904d"2\u5206\u949f\u9879\u76ee\u4ecb\u7ecd"
\u25a1 \u56de\u5fc6\u4e00\u4e0b BM25/RRF/Rerank \u4e09\u4e2a\u70b9\u7684\u6838\u5fc3\u539f\u7406
\u25a1 \u56de\u5fc6\u4e00\u4e0b\u516b\u80a1\u6587\u91cc\u6700\u5e38\u89c1\u7684\u90a3\u51e0\u9898\uff08\u8fdb\u7a0b/\u7ebf\u7a0b\u3001TCP\u4e09\u6b21\u63e1\u624b\u3001GET vs POST\uff09

\u9762\u8bd5\u524d 5 \u5206\u949f\uff1a
\u25a1 \u6df1\u547c\u5438\u4e09\u6b21\uff0c\u544a\u8bc9\u81ea\u5df1"\u6211\u80fd\u8bf4\u6e05\u695a\u8fd9\u4e2a\u9879\u76ee"
\u25a1 \u51c6\u5907\u597d 2-3 \u4e2a\u95ee\u9762\u8bd5\u5b98\u7684\u95ee\u9898\uff08\u89c1\u4e0b\u6587\uff09''')

add_h2('反问面试官的问题（必准备 2-3 个）')

add_code('''1. "\u56e2\u961f\u76ee\u524d\u7528\u4ec0\u4e48\u6280\u672f\u6808\uff1f\u6211\u9879\u76ee\u91cc\u7528\u7684\u6280\u672f\u80fd\u5bf9\u4e0a\u5417\uff1f"
   \u2192 \u4f53\u73b0\u4f60\u5173\u5fc3\u6280\u672f\u5339\u914d\u5ea6

2. "\u5b9e\u4e60\u751f\u4e3b\u8981\u8d1f\u8d23\u4ec0\u4e48\u5de5\u4f5c\uff1f\u4f1a\u6709 mentor \u5e26\u5417\uff1f"
   \u2192 \u4f53\u73b0\u4f60\u5173\u5fc3\u6210\u957f\u548c\u5b66\u4e60

3. "\u56e2\u961f\u5bf9 AI Agent \u65b9\u5411\u6709\u4ec0\u4e48\u89c4\u5212\u5417\uff1f\u6211\u5bf9\u8fd9\u5757\u7279\u522b\u611f\u5174\u8da3\u3002"
   \u2192 \u4f53\u73b0\u4f60\u6709\u65b9\u5411\u611f\uff0c\u4e0d\u662f\u4e71\u6295''')

add_h2('项目架构速查')

add_code('''\u251c\u2500 agent/react_agent.py    # ReAct Agent\u6838\u5fc3\uff0cLLM\u81ea\u4e3b\u51b3\u7b56+\u5de5\u5177\u8c03\u7528
\u251c\u2500 agent/evaluator.py     # A2A\u8bc4\u4f30Agent\uff0c\u56db\u7ef4\u5ea6\u6253\u5206+\u91cd\u8bd5\u56de\u8def
\u251c\u2500 agent/tools/            # 7\u4e2a\u5de5\u5177\u51fd\u6570 + \u4e2d\u95f4\u4ef6
\u251c\u2500 Rag/vector_store.py    # ChromaDB\u5411\u91cf\u5e93 + \u6df7\u5408\u68c0\u7d22(RRF\u878d\u5408)
\u251c\u2500 Rag/bm25_store.py     # BM25\u7a00\u758f\u68c0\u7d22(jieba\u5206\u8bcd)
\u251c\u2500 Rag/reranker.py        # BGE Cross-Encoder\u7cbe\u6392+\u4e09\u7ea7\u964d\u7ea7
\u251c\u2500 Rag/rag_service.py     # RAG\u68c0\u7d22\u5b8c\u6574\u6d41\u7a0b
\u251c\u2500 utils/memory_manager.py # \u56db\u5c42Memory\uff08\u77ed\u671f/\u6458\u8981/\u753b\u50cf/\u5de5\u4f5c\uff09
\u251c\u2500 utils/app_history.py   # Redis\u4f1a\u8bdd\u6301\u4e45\u5316
\u251c\u2500 model/factory.py        # LLM\u548cEmbedding\u6a21\u578b\u5de5\u5382
\u2514\u2500 config/                 # YAML\u914d\u7f6e\u6587\u4ef6\u7edf\u4e00\u7ba1\u7406''')

# ============================================================
# 保存
# ============================================================
output_path = r'C:\Users\20115\Desktop\agent_project\docs\RoboServe_大三实习面试备战指南.docx'
doc.save(output_path)
print(f'\u6587\u6863\u5df2\u4fdd\u5b58: {output_path}')


add_h2('学习优先级速查表')

add_table(
    ['优先级', '知识点', '掌握程度', '预计时间', '面试频率'],
    [
        ['P0 必会', '向量检索（Embedding + 相似度）', '能讲原理 + 手算例子', '1.5h', '极高'],
        ['P0 必会', '混合检索链路（Dense+BM25+RRF+Rerank）', '能画流程图 + 解释每步作用', '2h', '极高'],
        ['P0 必会', 'ReAct Agent 工作模式', '能讲循环过程 + 工具调用', '1h', '极高'],
        ['P0 必会', 'Memory 机制（分层记忆）', '讲清四层 + 为什么不用全量', '1.5h', '高'],
        ['P0 必会', '介绍你的项目（多种场景）', '流利讲述 2 分钟版本 + 30 秒版本', '2h', '极高'],
        ['P1 理解', 'BM25 检索原理', '讲清 TF-IDF 和饱和函数', '1h', '高'],
        ['P1 理解', 'RRF 融合算法', '能解释为什么用排名不用分数', '0.5h', '中高'],
        ['P1 理解', 'Cross-Encoder vs Bi-Encoder', '讲清区别和各自适用场景', '1h', '中高'],
        ['P1 理解', 'A2A 评估 Agent', '讲清评分维度和重试回路', '1h', '中'],
        ['P2 了解', 'ChromaDB + jieba + 工程实践', '知道是什么、在哪用', '1.5h', '中低'],
        ['P2 了解', 'Redis / YAML 配置 / 降级策略', '能说出怎么用的', '1h', '低'],
    ]
)

add_h2('每天学习安排（5 天计划）')

add_table(
    ['天数', '知识点', '学习方式'],
    [
        ['Day 1', '向量检索 + Embedding + ChromaDB', '先看 study_guide.md → 用自己的话复述 → 想想面试官会怎么追问'],
        ['Day 2', 'BM25 + jieba 分词 + RRF 融合', '手算一个 RRF 例子 → 打开 bm25_store.py 看代码对应'],
        ['Day 3', 'Rerank + 混合检索全链路', '画出完整数据流图 → 能口头讲一遍流程'],
        ['Day 4', 'Memory 机制 + A2A 评估 Agent', '理解四层记忆 → 理解评分四维度 → 想想为什么这样设计'],
        ['Day 5', 'LangChain 概念 + 项目介绍演练', '把"介绍项目"练 10 遍 → 录音听自己讲得顺不顺'],
    ]
)

add_page_break()

# 向量检索
add_h2('知识点 1：向量检索基础')

add_h3('一句话理解')
add_p('把文本通过 Embedding 模型转成数字向量，在向量空间中找距离最近的文档。距离越近 = 语义越相似。')

add_h3('为什么用余弦相似度而不是欧式距离？')
add_code('余弦相似度 = (A·B) / (|A| × |B|)，范围 [-1, 1]')

add_p('用余弦的原因：文本有长有短，向量长度差异大。余弦只看"方向"不看"长度"，短句和长文档也能公平比较。')
add_p('例子："扫地机器人怎么保养" 和 "扫地机器人的日常维护保养指南" → 余弦相似度会很高，虽然不是同样的词。')

add_h3('面试怎么讲？')
add_p("\u201c向量检索就是把文本变成数字向量，然后用余弦相似度找语义相近的文档。跟传统关键词搜索不同，它能理解同义词——搜\u2018保养\u2019也能找到\u2018维护\u2019相关的文档。\u201d")

add_h3('项目对应')
add_table(
    ['位置', '做什么'],
    [
        ['model/factory.py', 'DashScope text-embedding-v4 → 1024 维向量'],
        ['Rag/vector_store.py', 'ChromaDB 存储 + similarity_search 检索'],
    ]
)

add_page_break()

# BM25
add_h2('知识点 2：BM25 稀疏检索')

add_h3('一句话理解')
add_p('基于词频统计的经典算法。一个文档如果包含越多查询词、且这些词越稀有 → 得分越高。')

add_h3('BM25 比 TF-IDF 好在哪？')
add_table(
    ['对比点', 'TF-IDF', 'BM25'],
    [
        ['词频饱和', '出现 10 次得分是 1 次的 10 倍', '出现到一定次数后得分不再增长（防止刷分）'],
        ['文档长度', '长文档天然占优（包含更多词）', '有长度归一化，公平比较'],
        ['参数调优', '无', 'k1（词频饱和）、b（长度归一化）可调'],
    ]
)

add_h3('中文分词为什么重要？')
add_p('BM25 基于"词"统计频率。中文没有空格，"扫地机器人怎么清理" 如果不分词就是 1 个词，没法统计。')
add_p('我们用 jieba 分词 → ["扫地", "机器人", "怎么", "清理"]，然后 BM25 统计每个词的 TF-IDF。')
add_p('自定义词典（data/custom_dict.txt）让 jieba 识别"HEPA滤网"这类专业术语，不要切散。')

add_h3('面试怎么讲？')
add_p("\u201cBM25 是信息检索经典算法，基于词频（TF）\u00d7 逆文档频率（IDF）。我项目里用它做稀疏检索，配合 jieba 中文分词和自定义词典，能做精确的关键词匹配。但 BM25 不懂语义\u2014\u2014\u2018边刷不转\u2019和\u2018边刷故障\u2019在 BM25 看来是不同的词\u2014\u2014所以还需要 Dense 向量检索互补。\u201d")

add_page_break()

# RRF + Rerank + 混合检索
add_h2('知识点 3：RRF 融合 + Rerank 精排')

add_h3('RRF 融合——为什么看排名不看分数？')
add_p('Dense 的分数是余弦相似度（0~1 之间），BM25 的分数是 TF-IDF 加权（可能是 0~几十）。两路分数"不是同一个货币"，没法比大小。')
add_p('RRF 的做法：只关心排第几（第 1、第 2、第 3...），用统一的公式重新算融合分。')
add_code('RRF_score(d) = 1/(k+rank_dense) + 1/(k+rank_bm25)    k=60')

add_h3('Rerank 精排——为什么要粗排+精排两阶段？')
add_p('Cross-Encoder 需要把 query 和每篇文档拼在一起跑模型，计算量大。如果对所有文档都跑一遍，太慢。')
add_p('所以先粗排（Bi-Encoder，快但精度一般）筛出 top-8，再精排（Cross-Encoder，慢但精度高）降到 top-3。两阶段兼顾速度和精度。')

add_h3('完整检索链路（面试必须能画出/讲出）')
add_code('用户提问 → ①Dense检索(top8) + ②BM25检索(top8) → ③RRF融合去重 → ④Cross-Encoder精排(top3) → ⑤拼成Context喂LLM → ⑥生成回复')

add_h3('面试怎么讲？')
add_p('"我的检索设计了两路并行——Dense 向量检索做语义匹配（ChromaDB + text-embedding-v4），BM25 做关键词匹配（jieba 分词 + rank_bm25）。两路结果用 RRF 按排名融合——因为两路分数的尺度不同，直接加权会偏向某一路。融合后的 top-8 再用 BGE Cross-Encoder 精排到 top-3，最后喂给 LLM。整个链路兼顾了语义理解和精确匹配。"')

add_page_break()

# Memory
add_h2('知识点 4：Memory 分层记忆')

add_h3('为什么不能把全量历史发给 LLM？')
add_table(
    ['问题', '影响'],
    [
        ['Token 爆炸', '30 天对话历史轻松打满 8K~32K 上下文窗口'],
        ['注意力稀释', '模型在几百轮历史中找不到真正相关信息（Lost in the Middle）'],
        ['幻觉风险', '无关内容干扰模型，可能编造不存在的故障码'],
        ['成本浪费', '每轮都重发大量无用历史，浪费 API 费用'],
    ]
)

add_h3('四层记忆结构')
add_code('┌─短期记忆(最近5轮完整对话) ← 最近聊了什么\n├─对话摘要(窗口外历史压缩)  ← 之前聊了什么\n├─用户画像(设备型号/故障史)  ← 这是个什么样的用户\n└─工作记忆(当前任务上下文)  ← 正在排查什么')

add_h3('面试怎么讲？')
add_p('"长对话用全量历史有三个问题：token 爆炸、注意力稀释、幻觉。我设计了一个四层 Memory——最近 5 轮完整对话保留细节，更早的历史用 LLM 压缩成摘要，用户画像记录设备型号和故障历史，工作记忆跟踪当前任务状态。四层加起来替代全量历史，控制 token 消耗。"')

add_page_break()

# A2A 评估
add_h2('知识点 5：A2A 多 Agent 协作与评估')

add_h3('评估 Agent 做什么？')
add_code('客服Agent生成回复 → 评估Agent打分(4维度) →\n  ├─ 总分≥6.0 → 放行\n  └─ 总分<6.0 → 带反馈重生成 →\n        ├─ 重试成功 → 放行\n        └─ 超最大重试 → 兜底话术')

add_h3('四个评分维度')
add_table(
    ['维度', '权重', '考察什么'],
    [
        ['相关性 relevance', '30%', '回复是否紧扣用户问题'],
        ['准确性 accuracy', '35%', '事实是否正确，有无编造'],
        ['安全性 safety', '15%', '无危险建议（如"自己拆电机"）'],
        ['完整性 completeness', '20%', '是否覆盖了问题的所有关键点'],
    ]
)

add_h3('面试怎么讲？')
add_p('"我加了一个评估 Agent，类似代码 review——客服回复出来之后，独立的评估 Agent 从相关性、准确性、安全性、完整性四个维度打分。安全分低说明回复有风险（比如让用户自己拆机），准确性低说明 Agent 在编造不存在的信息。低于阈值触发重生成，用更保守的语调重新回答。评估用小模型（硅基流动的 Qwen2.5-14B），成本低、判断稳定。"')

add_page_break()

# ReAct Agent
add_h2('知识点 6：ReAct Agent 工作模式')

add_h3('ReAct = Reasoning + Acting')
add_code('循环：\n1. Thought(思考) → "用户需要天气信息，我应该调用 get_weather"\n2. Action(行动) → 调用工具获取天气数据\n3. Observation(观察) → "北京今天 35°C"\n4. 回到步骤1 → 信息够了就生成回复，不够就继续调工具')

add_h3('为什么用 Agent 而不是固定流程？')
add_p('固定流程（Chain）适合确定性任务。客服场景不确定——用户可能问天气、问故障、问保养、要求生成报告。Agent 让 LLM 自主判断需要什么工具，像真人客服一样灵活。')

add_h3('面试怎么讲？')
add_p('"我基于 LangChain 的 ReAct Agent 模式构建。LLM 看到用户问题后，自主思考需要什么信息——比如问天气就调 get_weather，问保养就调 rag_summarize 查知识库，拿到结果再判断是否够用。如果工具返回的信息不够，它会自动再调一次。我把 7 个工具注册给 Agent，每个工具有名称、描述、参数 schema，LLM 自己决定调用哪个。"')

add_page_break()

# ============================================================
# 第二部分：面试题集
# ============================================================
add_h1('第二部分：面试题集')

add_h2('一、「介绍你的项目」——核心必问题')

add_p('这是面试第一问，决定面试官对你的第一印象。需要准备三个版本：', bold_first=True)

add_h3('版本 1：标准版（90 秒，适合"先自我介绍一下"）')
add_p('"我最近做了一个智能客服系统，叫 RoboServe，针对扫地机器人的故障排查和使用咨询。')

add_p('技术栈方面：后端用 Python + LangChain 的 ReAct Agent，前端用 Streamlit，LLM 接阿里云通义千问。')

add_p('核心亮点有三个：')

add_p('第一，检索方面我做了混合检索——Dense 向量 + BM25 稀疏检索，用 RRF 算法融合排行，再用 Cross-Encoder 做精排。这样既能做语义匹配，又能精确匹配关键词。')

add_p('第二，我实现了分层 Memory 机制——短期记忆、对话摘要、用户画像、工作记忆四层，解决长对话的 token 爆炸问题。')

add_p('第三，我加了 A2A 多 Agent 协作——一个独立的评估 Agent 给回复打分，不达标就触发重生成，保证回复质量。')

add_p('目前整个链路已经跑通了，知识库有 119 条文档，支持天气查询、故障诊断、使用咨询、生成诊断报告等功能。"')

add_h3('版本 2：精简版（30 秒，适合"简单介绍一下你的项目"）')
add_p('"我做了一个智能客服系统 RoboServe，基于 LangChain ReAct Agent。检索用了混合检索——Dense 向量 + BM25 + RRF 融合 + Cross-Encoder 精排，四阶段保障召回质量。还做了 Memory 分层管理和 A2A 评估 Agent 做质量把关。技术栈 Python + LangChain + ChromaDB + Redis + Streamlit，LLM 接通义千问。"')

add_h3('版本 3：技术深挖版（3 分钟，适合"详细讲讲你的项目"）')
add_p('这时候面试官对你感兴趣了，你可以展开讲。建议按"做什么 → 怎么做 → 难点 → 收获"这个结构。')

add_p('"这个项目的完整链路是：用户提问 → ReAct Agent 判断意图 → 调用相应工具。如果是知识类问题，走 RAG 流程：先两路并行检索（Dense 向量 + BM25 关键词），用 RRF 按排名融合，再过 Cross-Encoder 精排，选出最相关的 3 条文档喂给 LLM 生成回答。')

add_p('我还做了几个设计：Memory 分层（四层压缩替代全量历史）、A2A 评估（独立 Agent 四维度打分+重试回路）、三级降级（BGE → TF-IDF → 取前 N）、开关设计（每个模块都可以独立开关）。')

add_p('遇到的最大挑战是 Python 依赖链问题。sentence_transformers 间接依赖 torch，几百 MB 启动慢。我的方案是延迟加载——模块只在真正需要时才 import，不影响主流程。"')

add_h3('「介绍项目」的避坑指南')
add_table(
    ['不要说', '要说'],
    [
        ['"我用 AI 帮了大忙" / "大部分代码是 AI 写的"', '"我设计了架构，AI 辅助实现" —— 强调你的设计决策'],
        ['"我用了很多技术，比如..." 然后列一堆名词', '每个技术后面跟一句"为什么"和"解决了什么"'],
        ['"这是一个简单的xx系统..."', '"这是一个面向YY场景的XX系统" —— 不要说简单'],
        ['照背技术名词，被追问就卡住', '只说自己真的理解的部分，不被追问就不要主动展开'],
    ]
)

add_page_break()

add_h2('二、技术深挖题')

add_h3('检索相关')

add_qa('你们的混合检索为什么要用 Dense + BM25 两路？',
    'Dense 向量擅长语义匹配——用户说"机器不动了"能匹配"机器人无法移动"——但弱于精确匹配特定术语。BM25 刚好相反——搜"E03 错误码"能精确命中，但不理解"边刷不转"和"边刷故障"是一个意思。两路互补，覆盖更多检索场景。')

add_qa('RRF 的 k=60 怎么定的？如果 k=10 会怎样？',
    'k=60 是 RRF 原论文的推荐值，是经验上的平衡点。k 越小，排名靠前的文档权重越大，更激进；k 越大，排名差异的影响越小，更保守。如果 k=10，第 1 名得分是 1/11≈0.091，第 10 名是 1/20=0.05，差距拉大——Dense 路的第一名可能压过 BM25 路的内容。实际可以 A/B 测试不同 k 值。')

add_qa('如果粗排没召回正确答案，精排能救回来吗？',
    '不能。精排只在粗排结果上重排序，不会引入新文档。如果粗排漏了，精排也无能为力。这就是为什么混合检索很重要——两路互补降低漏召回的概率。另外如果有特别重要的文档，可以考虑做特例兜底。')

add_qa('为什么要做 Rerank？直接用 Embedding 的相似度排序不行吗？',
    'Bi-Encoder 把 query 和 doc 分别编码再算相似度，看不到两者的交互。Cross-Encoder 把 query 和 doc 拼在一起输入模型，能捕捉细粒度的语义关系。举例：query 是"边刷不转"，doc_A 说"边刷正常说明电机没问题"，doc_B 说"边刷不转可能原因"。Bi-Encoder 可能分不出区别（都含边刷），Cross-Encoder 能准确识别 doc_B 才是真正相关的。')

add_h3('Memory 相关')

add_qa('如果你的对话超过了 5 轮短期记忆窗口，用户又问了一个跟很早期相关的问题怎么办？',
    '对话摘要在起作用。超出窗口的历史我们会用 LLM 压缩成摘要，摘要 prompt 专门要求保留关键事实（设备型号、故障码、已尝试方案）。比如用户 10 轮前说"我的 E03 报错了"，摘要里会保留"用户设备报 E03 错误"。10 轮后用户说"那个错误还在"，Agent 能从摘要里定位到 E03。加上工作记忆层会追踪当前任务，连续追问不会被摘要压掉。')

add_qa('摘要会不会丢失关键信息？怎么验证？',
    '有可能丢失。目前的措施：摘要 prompt 明确要求保留关键事实；工作记忆层独立维护当前任务上下文。验证方法：跑 20 组真实多轮对话，检查摘要是否遗漏了重要信息，调整 prompt 直到满意。这是需要持续迭代的。')

add_h3('A2A 评估相关')

add_qa('评估 Agent 打分的准确性怎么保证？你信任一个 LLM 去评价另一个 LLM？',
    '这是一个好问题。目前确实是 LLM 评价 LLM，不是 100% 可靠。我做了几个设计降低风险：评分维度明确（每个维度有具体的扣分规则），输出 JSON 结构化打分而非模糊评价，容错解析（小模型偶尔输出不规范的 JSON，用正则兜底提取分数）。长期看，应该用人工标注的真实 case 来校准评估标准，但作为第一版，当前方案已经能过滤掉明显的问题。')

add_qa('评估 Agent 用小模型（14B）打分，和用大模型（72B）打分会差多少？',
    '主要差距在对"灰色地带"的敏感度。明显的问题（编造故障码、危险建议）小模型能识别；但一些微妙的表述不当（暗示但不明确说错）小模型可能放过。我们在 prompt 里把小模型调成"宁可错杀不可放过"——安全分默认 5 分基础分，只有明确安全才给高分。')

add_page_break()

add_h2('三、场景设计题')

add_qa('如果知识库有 10 万条文档，ChromaDB 还能用吗？需要做什么改造？',
    'ChromaDB 几万条文档没问题，10 万以上建议考虑 Milvus 或 Qdrant。同时需要：1) 加缓存——热门问题缓存检索结果；2) 分层索引——先做粗分类（故障/保养/选购），缩小检索范围；3) 向量索引优化——用 IVF 或 HNSW 替代暴力搜索。')

add_qa('如果用户问"我上次问的那个问题解决了吗"，你的系统怎么处理？',
    '这是多轮对话的典型场景。Agent 需要意识到这是一个追问——不是新问题——然后从 Memory 中查找用户上次的问题。如果工作记忆中标记了"当前任务：排查边刷不转"，Agent 就会回复"您上次问的是边刷不转的问题，目前排查到..."。关键在于 Agent 的判断能力和 Memory 中任务状态的准确性。')

add_qa('如果要同时服务 100 个用户，你的系统需要做什么改造？',
    '当前是单机部署，100 并发需要：1) ChromaDB 改成服务端模式（当前是本地文件模式）；2) Agent 实例池，预创建几个 Agent 复用；3) Redis 做会话隔离（这个已经有了）；4) LLM API 加限流，防止打爆。另外评估 Agent 可以降级为异步——不是每轮都评，而是抽样或异步后台评分。')

add_h2('四、行为面试题')

add_qa('你项目中最大的技术难点是什么？怎么解决的？',
    '最大的难点是 Python 依赖链崩溃问题。sentence_transformers 间接依赖 torch → torchvision，整个依赖链几百 MB。在 BM25 模块我不小心引入了 langchain_text_splitters，导致即便不需要 Rerank，系统启动也要加载 torch，启动慢甚至 OOM。我的解决方案：延迟加载——把 sentence_transformers 的 import 从文件顶部移到函数内部，只在真正需要时才触发；BM25 模块完全不用 langchain，自己实现文本分块。这让我深刻理解了 import 机制和依赖管理的重要性。')

add_qa('如果让你重做这个项目，你会改什么地方？',
    '三个：第一，检索链路应该先做 A/B 测试验证每个环节的效果，而不是一开始就上全链路——可能某些场景下 Dense 或 BM25 单独就够用；第二，评估 Agent 的评分标准应该基于真实 case 标注来校准，当前主要靠 prompt 调优，不够科学；第三，工具函数的错误处理可以更完善，当前 try/except 大多用 pass，应该加降级日志。')

add_page_break()

# ============================================================
# 第三部分：简历撰写指导
# ============================================================
add_h1('第三部分：简历撰写指导')

add_p('以下是基于你的 RoboServe 项目，如何写出能通过筛选、引发面试官兴趣的简历描述。', bold_first=True)

add_h2('一、项目经历的标准写法')

add_h3('模板结构')
add_p('每个项目按"STAR 结构"来写：场景(Situation) + 任务(Task) + 行动(Action) + 结果(Result)。')

add_h3('你的项目简历描述（推荐直接用在简历上）')

add_code('''RoboServe 智能客服系统（Python + LangChain + ChromaDB + Redis）
[2026.03 - 2026.06]  独立开发

• 基于 ReAct Agent 模式构建智能客服系统，集成 7 个工具函数（RAG检索、
  天气查询、报告生成等），LLM 自主决策工具调用，支持多轮对话

• 设计并实现混合检索架构：Dense向量检索（ChromaDB + DashScope 
  text-embedding-v4）+ BM25稀疏检索（jieba分词），通过 RRF 算法
  两路融合，BGE Cross-Encoder 精排，检索精度相比单路提升显著

• 实现分层 Memory 机制（短期记忆/摘要/用户画像/工作记忆），解决长对话
  token 爆炸和注意力稀释问题，控制上下文大小降低 API 成本

• 设计 A2A 多 Agent 质量评估回路：独立评估 Agent 四维度打分（相关性/
  准确性/安全性/完整性），不达标触发重生成 + 兜底策略

• 技术栈：Python, LangChain, ChromaDB, Redis, Streamlit, jieba, 
  rank_bm25, sentence_transformers, 通义千问 API, 硅基流动 API''')

add_h3('为什么这样写？')
add_table(
    ['要素', '写法', '原因'],
    [
        ['数字', '"7个工具函数" "四维度" "top-8→top-3"', '数字比形容词有说服力'],
        ['动词', '"设计并实现" "构建" "集成"', '主动动词体现你主导了工作'],
        ['对比', '"相比单路检索提升"', '有对比才能体现你做了什么优化'],
        ['技术名词', '不加解释直接列', '面试官看到感兴趣的技术会主动追问'],
        ['结果', '不要空泛的"效果很好"', '用具体数据或具体改进点说明'],
    ]
)

add_page_break()

add_h2('二、技能特长的写法')

add_h3('推荐版（分级展示）')

add_code('''编程语言：Python（熟练，主要开发语言）、SQL（基础）
后端框架：LangChain、FastAPI（了解）
数据库：ChromaDB（向量数据库）、Redis（缓存/会话）、MySQL（基础）
AI/LLM：RAG 检索增强生成、ReAct Agent、LLM 工具调用、
         Prompt Engineering、Embedding 模型应用
检索技术：混合检索（Dense+BM25）、RRF 融合、Cross-Encoder 精排、
          中文分词（jieba）、BM25 关键词检索
工程能力：YAML 配置管理、异常降级策略、MD5 增量校验、
          Python 依赖管理、Git 版本控制
前端：Streamlit（可独立开发完整 Web 界面）
其他：Docker（基础）、Postman（API 调试）''')

add_h3('避坑：不要犯这些错误')
add_table(
    ['错误写法', '问题', '正确写法'],
    [
        ['"精通 Python"', '大三实习生说精通 → 会被深挖刁难', '"熟练使用 Python"'],
        ['"熟悉机器学习、深度学习"', '只在这个项目用了 Embedding，不要说太宽', '"了解 Embedding 和向量检索"'],
        ['"掌握 Spring Boot"', '如果没用过就不要写，被问就露馅', '只写真正用过的技术'],
        ['罗列 30 个技术名词', '面试官不知道你哪个是真的会', '分级：熟练 / 了解 / 基础'],
        ['"参与开发"而不是"独立开发"', '弱化你的贡献', '如果是你做的就写"独立开发"'],
    ]
)

add_page_break()

add_h2('三、针对不同岗位的简历调整')

add_h3('Agent 开发岗位（你的主要目标）')
add_p('重点突出：ReAct Agent 设计、工具函数注册、A2A 多 Agent 协作、Memory 机制')
add_p('可以加一句：')
add_code('深入理解 LangChain Agent 框架的 ReAct 模式，能自主设计 Tool 集合和系统 Prompt，实现 LLM 自主决策的多轮对话系统。')

add_h3('RAG/NLP 相关岗位')
add_p('重点突出：混合检索链路、RRF 融合、Cross-Encoder 精排、文档分块策略')
add_p('可以加一句：')
add_code('系统掌握了从文档预处理、向量化、混合检索到精排的完整 RAG 链路，理解 Bi-Encoder 和 Cross-Encoder 的适用场景和精度/速度权衡。')

add_h3('Python 后端岗位')
add_p('重点突出：系统架构设计、Redis 持久化、YAML 配置管理、降级策略、Streamlit 前端')
add_p('可以加一句：')
add_code('具备独立从 0 搭建完整后端系统的能力，包括 API 设计、数据库选型、异常处理、配置管理和前端展示。')

add_page_break()

add_h2('四、简历整体结构建议')

add_h3('大三实习生简历的标准结构')
add_table(
    ['顺序', '模块', '内容', '长度'],
    [
        ['1', '个人信息', '姓名、电话、邮箱、GitHub（如有）', '2-3 行'],
        ['2', '求职意向', '岗位：Agent开发/AI应用开发（可写1-2个）', '1 行'],
        ['3', '教育背景', '学校、专业、毕业时间、相关课程（选3-4门）', '3-4 行'],
        ['4', '项目经历', 'RoboServe 项目 + 大数据分析项目（2-3 个项目）', '占简历 40%'],
        ['5', '技能特长', '分类列出（参考上面）', '6-8 行'],
        ['6', '荣誉/证书', '如有（蓝桥杯、软考、英语等级等）', '2-3 行'],
        ['7', '自我评价', '1-2 句总结（可选，不是必须）', '2 行'],
    ]
)

add_h3('一页简历的内容分配')
add_p('大三实习生简历控制在 1 页 A4。按重要性分配空间：', bold_first=True)
add_code('项目经历 40% | 技能特长 20% | 教育背景 15% | 其他 25%')

add_h3('项目经历在简历中的排版')
add_p('每个项目用 3-5 个 bullet point，每个 bullet 不超过 2 行。用动词开头、数字量化。两个项目的推荐描述：')

add_h3('项目 1：RoboServe 智能客服系统（详见上面，略）')

add_h3('项目 2：学生健康数据分析系统')
add_code('''学生健康数据分析系统（Python + Pandas + Matplotlib）
[2026.03 - 2026.04]  独立开发

• 使用 Pandas 对 5 万条学生健康数据（16 个特征）进行清洗和统计分析
• 通过 Matplotlib 生成 8 组可视化图表，包括 BMI 分布、运动频率与
  成绩相关性等
• 完成 3000 字数据分析报告，包含数据洞察和健康建议''')

add_page_break()

add_h2('五、面试中简历被追问怎么办？')

add_h3('常见追问及应对')

add_qa('面试官：你项目里的 RRF 融合是自己写的还是调的库？',
    '自己写的。RRF 本身不复杂，核心就是对排名做倒数加权。自己写的好处是能控制去重逻辑（用 MD5 做 key 去重）和融合参数调优。不建议说"很简单就几行代码"——要说"虽然公式简单，但理解为什么用排名不用分数、k 值怎么选，这些背后原理我认真研究过。"')

add_qa('面试官：你这个项目实际有人在用吗？',
    '诚实回答。如果是自己练手的项目，就说"这是一个课程/个人项目，但我是按实际业务场景设计的——知识库用的是真实扫地机器人的故障排除和维护文档，Prompt 和工具函数也是针对真实客服场景设计的。"强调你考虑了真实场景，不是搭了一个 demo 就完事。')

add_qa('面试官：你项目里最自豪的一个设计是什么？',
    '选一个你能讲清楚的。推荐 Memory 机制（因为分层设计体现了系统思维）或 RRF 融合（因为体现了你对不同检索方式分数不可比这个问题的理解）。关键是要能讲出"为什么这样设计"而不只是"我做了 X"。')

add_h2('六、投递策略建议')

add_h3('海投 vs 精准投递')
add_table(
    ['策略', '适合场景', '建议'],
    [
        ['海投（BOSS直聘批量投）', '刚开始找，积累面试经验', '准备一份通用简历，投一切 AI/后端岗'],
        ['精准投递（官网/内推）', '有了几次面试经验后', '针对每个岗位微调项目描述的侧重点'],
    ]
)

add_p('建议先海投 2-3 天，拿 3-5 个面试练手（不重要的小公司），找到面试感觉后，再精准投递目标公司。')

add_h3('投递渠道优先级')
add_code('内推 > 官网投递 > Boss直聘 > 拉勾 > 实习僧')

add_h3('关于民办二本学历')
add_p('诚实面对。简历上正常写学校就好，不要隐瞒。面试时如果被问到，可以这样回应：')
add_p('"我知道学历是我的短板，所以从大二开始就在补实践。这个项目就是我独立从 0 搭建的，从架构设计到代码实现到调试优化，过程中学到了很多课堂上学不到的东西。我相信实际动手能力比学历更能说明问题。"', bold_first=False)

add_p('关键：不要回避、不要自卑、把话题引向你的实践能力。')

add_page_break()

# ============================================================
# 附录
# ============================================================
add_h1('附录')

add_h2('A. 项目技术架构速查图')

add_code('''┌─────────────────────────────────────┐
│         用户 (Streamlit/FastAPI)        │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│     ReactAgent (react_agent.py)      │
│  ┌─────────────────────────────────┐│
│  │  LLM: qwen3.7-max (DashScope)   ││
│  │  7个Tool + 中间件 + Memory       ││
│  └─────────────────────────────────┘│
└───┬───────┬───────┬───────┬────────┘
    ▼       ▼       ▼       ▼
┌──────┐┌──────┐┌──────┐┌──────────┐
│ RAG  ││天气  ││报告  ││ 评估     │
│检索  ││查询  ││生成  ││ Agent   │
└──┬───┘└──────┘└──────┘└──────────┘
   ▼
┌──────────────────────────────────────┐
│   混合检索链路                        │
│  Dense(top8) + BM25(top8)            │
│      → RRF融合去重                    │
│      → Cross-Encoder精排(top3)        │
│      → LLM生成回复                    │
└──────────────────────────────────────┘
         │              │
    ChromaDB         Redis
  (向量存储)      (会话持久化)''')

add_h2('B. 项目配置速查')

add_table(
    ['配置项', '当前值', '说明'],
    [
        ['LLM 对话模型', 'qwen3.7-max', '通义千问，DashScope API'],
        ['Embedding 模型', 'text-embedding-v4', 'DashScope，1024维'],
        ['评估模型', 'Qwen2.5-14B-Instruct', '硅基流动 API'],
        ['向量数据库', 'ChromaDB (本地)', 'persist_directory 持久化'],
        ['会话存储', 'Redis localhost:6379', 'TTL 30 天'],
        ['检索数量', '8+8 → 5+3', '粗排各8篇，精排保留3篇'],
        ['RRF 参数', 'k=60', '论文推荐默认值'],
        ['Rerank 模型', 'BAAI/bge-reranker-base', 'Cross-Encoder'],
        ['Memory 窗口', '5 轮', '可配置'],
        ['评估阈值', '6.0 分', '四维度加权总分'],
        ['最大重试', '2 次', '避免死循环'],
    ]
)

add_h2('C. 面试前的最后检查清单')

add_code('''面试前 1 小时：
□ 打开项目，跑一遍 streamlit run utils/app_web.py，确认能跑通
□ 打开 agent/react_agent.py，快速过一遍关键代码位置（面试可能被问）
□ 在脑海里过一遍"介绍项目"（30秒版 + 90秒版）
□ 回忆一下 BM25/RRF/Rerank 三个点的核心原理

面试前 10 分钟：
□ 打开项目 README.md 扫一眼
□ 深呼吸三次，告诉自己"我能讲清楚这个项目"
□ 准备好问面试官的问题（2-3个）：
  - "团队目前用什么技术栈？"
  - "实习生主要负责什么工作？"
  - "团队对 AI Agent 方向有什么规划？"''')

# ============================================================
# 保存
# ============================================================
output_path = r'C:\Users\20115\Desktop\agent_project\docs\RoboServe_面试备战指南.docx'
doc.save(output_path)
print(f'文档已保存: {output_path}')

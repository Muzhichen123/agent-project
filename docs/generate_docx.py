from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import re

doc = Document()

# 设置默认字体
style = doc.styles['Normal']
font = style.font
font.name = '微软雅黑'
font.size = Pt(11)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# 设置各级标题样式
for level in range(1, 5):
    heading_style = doc.styles[f'Heading {level}']
    heading_style.font.name = '微软雅黑'
    heading_style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    heading_style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

# 标题
title = doc.add_heading('RoboServe 项目知识点学习清单 + 面试题', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_paragraph('本文档整理了项目开发过程中涉及的全部新技术知识点，每个知识点包含：核心概念、项目中的具体实现、面试常见问题及参考答案。')
doc.add_paragraph('')

# 目录
doc.add_heading('目录', level=1)
toc_items = [
    '一、向量检索基础',
    '二、Embedding 与稠密向量',
    '三、ChromaDB 向量数据库',
    '四、BM25 稀疏检索',
    '五、jieba 中文分词',
    '六、RRF 融合算法',
    '七、Rerank 交叉编码器精排',
    '八、混合检索整体链路',
    '九、Memory 机制',
    '十、A2A 多 Agent 协作',
    '十一、LangChain 核心概念',
    '十二、Python 工程实践',
    '十三、综合面试题',
]
for item in toc_items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_page_break()

# ============================================================
# 辅助函数
# ============================================================
def add_section(title_text, level=1):
    doc.add_heading(title_text, level=level)

def add_subsection(title_text):
    doc.add_heading(title_text, level=2)

def add_paragraph(text):
    p = doc.add_paragraph(text)
    return p

def add_bold_text(paragraph, bold_text, normal_text=''):
    run = paragraph.add_run(bold_text)
    run.bold = True
    if normal_text:
        paragraph.add_run(normal_text)

def add_code_block(code_text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    run = p.add_run(code_text)
    run.font.name = 'Consolas'
    run.font.size = Pt(9)
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    # 设置灰色底纹
    from docx.oxml import OxmlElement
    pPr = p._element.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'F2F2F2')
    pPr.append(shd)
    return p

def add_qa(question, answer):
    q = doc.add_paragraph()
    run = q.add_run(question)
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
    a = doc.add_paragraph(answer)

def add_table(headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            table.rows[r_idx + 1].cells[c_idx].text = str(val)
    doc.add_paragraph('')

# ============================================================
# 一、向量检索基础
# ============================================================
add_section('一、向量检索基础')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '什么是向量检索？',
    ' 把文本（句子、段落、文档）通过 Embedding 模型转成一串数字（向量），然后在向量空间中找距离最近的文档。距离越近 = 语义越相似。')

add_bold_text(doc.add_paragraph(), '为什么用余弦相似度而不是欧式距离？')

add_code_block('''余弦相似度：衡量两个向量的方向是否一致，范围 [-1, 1]，接近 1 = 方向相同 = 语义相似
欧式距离：  衡量两个向量的绝对距离，受向量长度影响

例子：
向量A = (1, 1)  长度 1.41
向量B = (2, 2)  长度 2.83
向量C = (3, 0)  长度 3.00

余弦(A,B) = 1.0   → 方向完全一致，语义相同
欧式(A,B) = 1.41  → 有距离差异

余弦(A,C) = 0.71  → 方向不同
欧式(A,C) = 2.24''')

add_paragraph('选择余弦的原因：文本的长短不同（短句 vs 长文档），导致向量长度差异大。余弦只看方向不看长度，更稳定。')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['model/factory.py', 'DashScope text-embedding-v4 把文本变成 1024 维向量'],
        ['Rag/vector_store.py', 'ChromaDB 存储向量，similarity_search 内部算余弦相似度'],
    ])

add_subsection('面试题')
add_qa('Q：什么是向量检索？和关键词搜索有什么区别？',
    '向量检索把文本转成数字向量，通过计算向量间的距离（通常是余弦相似度）找相关内容。关键词搜索（如 BM25）是精确匹配用户输入的词。向量检索擅长语义匹配（"怎么保养" 能找到 "维护建议"），但弱于精确匹配（搜型号名可能找不准）。两者互补。')

add_qa('Q：余弦相似度的计算公式是什么？取值范围？',
    'cos(A,B) = (A·B) / (|A| × |B|)，即两个向量的点积除以各自长度的乘积。取值 [-1, 1]，1 表示完全相同，0 表示无关，-1 表示完全相反。文本检索中一般看 0 到 1 的范围。')

doc.add_page_break()

# ============================================================
# 二、Embedding 与稠密向量
# ============================================================
add_section('二、Embedding 与稠密向量')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '什么是 Embedding？',
    ' Embedding（嵌入）就是把一段文本压缩成一个固定长度的数字数组（向量）。这个数组"编码"了文本的语义信息——语义相近的文本，向量也相近。')

add_bold_text(doc.add_paragraph(), '稠密向量 vs 稀疏向量：')
add_code_block('''稠密向量（Dense Embedding）：
  - 每个维度都有非零值（通常是浮点数）
  - 由深度学习模型生成
  - 维度通常 384~1024
  - 例：text-embedding-v4 输出 [0.023, -0.156, 0.891, ...]（1024个数字）

稀疏向量（Sparse Embedding / BM25）：
  - 大部分维度是 0，只有匹配到的词才有值
  - 基于词频统计
  - 维度 = 整个词表大小（可能几万个）
  - 例：{"扫地": 2.3, "机器人": 1.8, "清理": 3.1}（只有出现的词有分）''')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['model/factory.py', 'DashScope API 调用 text-embedding-v4'],
        ['知识库', '文档在系统启动时预计算向量，存入 ChromaDB'],
        ['用户查询', '实时计算向量，和库内向量算余弦相似度'],
    ])

add_subsection('面试题')
add_qa('Q：Embedding 模型输出的向量维度是多少？维度越高越好吗？',
    'text-embedding-v4 输出 1024 维。不是越高越好。维度高能编码更多信息但计算成本更高、检索更慢。维度低则可能丢失语义信息。通常 384~1024 是平衡点。')

add_qa('Q：稠密向量和稀疏向量各有什么优缺点？',
    '稠密向量擅长语义理解（"手机坏了" 能匹配 "设备故障"），但不擅长精确匹配（搜特定型号可能偏）。稀疏向量（BM25）擅长精确关键词匹配，但不理解语义。两者互补，这就是为什么我们做混合检索。')

doc.add_page_break()

# ============================================================
# 三、ChromaDB
# ============================================================
add_section('三、ChromaDB 向量数据库')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), 'ChromaDB 是什么？',
    ' 一个轻量级开源向量数据库，专门存和查向量。每个条目包含三部分：')

add_code_block('''Document：原文内容（page_content）
Vector：  对应的向量（embedding）
Metadata：附加元数据（source 文件名、chunk_id 等）

核心操作：
add()     → 存入文档（自动计算向量或使用你提供的向量）
similarity_search(query, k=3) → 查最相似的 top-k 篇''')

add_paragraph('内部用 HNSW（分层可导航小世界图）做近似最近邻搜索，比暴力遍历所有向量快很多。')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['Rag/vector_store.py', '初始化 ChromaDB 客户端，加载文档，执行检索'],
        ['config/chroma.yml', '配置持久化路径、检索数量 k'],
    ])

add_subsection('面试题')
add_qa('Q：ChromaDB 里面存的是什么？',
    '存三样东西：文档原文（page_content）、对应的向量（embedding，由 text-embedding-v4 生成）、元数据（metadata，如来源文件名）。查询时把用户问题也变成向量，然后在库里找余弦相似度最高的文档。')

add_qa('Q：你的文档是怎么分块的？为什么要分块？',
    '用 RecursiveCharacterTextSplitter 按分隔符递归切分，chunk_size=200，overlap=20。分块原因：Embedding 模型有最大输入长度限制（通常 512 token）；一个长文档如果整体编码会丢失细节；分块后检索更精准（返回的是最相关的那一小段，不是整篇文档）。')

doc.add_page_break()

# ============================================================
# 四、BM25 稀疏检索
# ============================================================
add_section('四、BM25 稀疏检索')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), 'BM25 是什么？',
    ' 信息检索领域的经典算法，基于 TF-IDF 思想。')

add_code_block('''score(D, Q) = Σ IDF(qi) × TF_factor(qi, D)

其中：
TF  = 词 qi 在文档 D 中出现的频率（出现越多越好，但有饱和）
IDF = 词 qi 的稀有程度（越少文档包含它，它越重要）''')

add_paragraph('一句话理解：一个文档如果包含了用户查询中的很多词，而且这些词在其他文档中很少出现 → 这个文档和查询高度相关。')

add_bold_text(doc.add_paragraph(), 'BM25 vs TF-IDF 的区别：')
add_code_block('''TF-IDF：  词出现次数越多，得分线性增长
BM25：    有饱和函数，词出现到一定次数后得分不再增长
BM25：    有长度归一化，长文档不会天然占优势''')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['Rag/bm25_store.py', 'BM25Store 类，jieba 分词 + BM25Okapi 索引'],
        ['data/custom_dict.txt', '自定义分词词典'],
        ['持久化', 'bm25_index.pkl，用 pickle 序列化'],
    ])

add_subsection('面试题')
add_qa('Q：BM25 的检索原理是什么？',
    'BM25 基于词频（TF）和逆文档频率（IDF）。一个文档如果包含了很多查询词，而且这些词在整个语料中比较稀有，那么这个文档得分就高。BM25 相比朴素 TF-IDF 的改进是加入了饱和函数（防止一个词出现太多次主导结果）和文档长度归一化。')

add_qa('Q：BM25 索引为什么要持久化？',
    'BM25 需要对所有文档做分词，如果有几百个 chunk，每次启动都重建需要几秒到十几秒。用 pickle 序列化到文件，启动时直接加载只需要零点几秒。同时用 MD5 签名校验——知识库文件变了就自动重建索引。')

add_qa('Q：BM25 对中文有什么特殊要求？',
    'BM25 不能直接用中文原文，必须先分词（把句子切成词语）。因为 BM25 是基于"词"的频率统计，如果不分词，整句中文就只有一个"词"，没法统计。我们用 jieba 做中文分词。')

doc.add_page_break()

# ============================================================
# 五、jieba 中文分词
# ============================================================
add_section('五、jieba 中文分词')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '什么是中文分词？',
    ' 中文没有英文那样的空格分隔词语，"扫地机器人怎么清理" 是一个连续字符串。分词就是把这句话切成词语：["扫地", "机器人", "怎么", "清理"]。')

add_bold_text(doc.add_paragraph(), '为什么要分词？',
    ' BM25 基于词频统计，如果不分词，整句话就是一个"词"，无法计算单个词的频率。分词后才能知道"扫地"出现了几次、"清理"出现了几次。')

add_bold_text(doc.add_paragraph(), '自定义词典的作用：')
add_paragraph('jieba 默认词库是通用中文。"HEPA滤网" 可能被切成 "HEPA" + "滤网"。但在知识库里 "HEPA滤网" 是一个完整术语。自定义词典告诉 jieba "这个词不要拆"。')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['Rag/bm25_store.py 第146-148行', '加载 data/custom_dict.txt'],
        ['Rag/bm25_store.py 第156-157行', '_tokenize 方法：jieba.cut(text)'],
    ])

add_subsection('面试题')
add_qa('Q：为什么 BM25 需要分词，而 Dense 向量检索不需要？',
    'BM25 是基于词频的统计算法，它统计的是"某个词在文档中出现了几次"。如果中文不切词，整句就是一个单位，无法统计单个词的频率。而 Dense 向量由 Embedding 模型（如 text-embedding-v4）处理，模型内部自己学会了理解中文语义，不需要人工分词。')

add_qa('Q：自定义词典解决什么问题？',
    'jieba 默认词库是通用中文，不包含专业术语。比如 "3D结构光" 默认被切成 "3D" + "结构" + "光"，但知识库里是完整术语。自定义词典让 jieba 把它当成一个整体，BM25 才能精确匹配。')

doc.add_page_break()

# ============================================================
# 六、RRF 融合算法
# ============================================================
add_section('六、RRF 融合算法')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '什么是 RRF（Reciprocal Rank Fusion）？',
    ' 把多路检索结果合并成一份最终排序列表的方法。核心思想：只看排名，不看原始分数。')

add_code_block('''RRF_score(d) = Σ  1 / (k + rank_i(d))

d = 某个文档
rank_i(d) = 该文档在第 i 路检索中的排名
k = 平滑常数，默认 60''')

add_bold_text(doc.add_paragraph(), '为什么不用原始分数？')
add_paragraph('Dense 的分数是余弦相似度（0~1），BM25 的分数是 TF-IDF 加权（可能是 0~几十）。两路分数的尺度不同，没法直接比大小。RRF 绕开这个问题——只看"排第几"，不看"得了几分"。')

add_bold_text(doc.add_paragraph(), '手算例子：')
add_code_block('''Dense 检索排名：DocA(1)  DocB(2)  DocC(3)
BM25  检索排名：DocB(1)  DocC(2)  DocA(3)

RRF(k=60):
DocA = 1/(60+1) + 1/(60+3) = 0.01639 + 0.01587 = 0.03226
DocB = 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252  ← 最高
DocC = 1/(60+3) + 1/(60+2) = 0.01587 + 0.01613 = 0.03200

最终排序：DocB > DocA > DocC
DocB 在两路都排前列，所以 RRF 分最高''')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['Rag/vector_store.py 第167-219行', 'hybrid_retrieve 方法中的 RRF 融合逻辑'],
        ['文档去重', 'hashlib.md5(doc.page_content) 做 key'],
        ['config/chroma.yml', 'rrf_k: 60'],
    ])

add_subsection('面试题')
add_qa('Q：RRF 融合为什么要用排名而不是原始分数？',
    'Dense 向量的分数是余弦相似度（范围 0~1），BM25 的分数是 TF-IDF 加权（范围不确定）。两路分数的尺度和分布都不同，无法直接比较。RRF 只用排名（第 1、第 2、第 3...），避开了分数归一化的问题。')

add_qa('Q：k=60 这个值怎么来的？',
    'RRF 原始论文（Cormack et al., 2009）推荐的默认值。k 越大，排名差异的影响越小（趋于平均）；k 越小，前面的排名权重越大。60 是经验上的平衡点。实际使用中可以测试不同 k 值对比效果。')

doc.add_page_break()

# ============================================================
# 七、Rerank 交叉编码器精排
# ============================================================
add_section('七、Rerank 交叉编码器精排')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '粗排 vs 精排：')
add_code_block('''粗排（Retrieval）：  从大量文档中快速筛选出候选集（如 top-8）
精排（Reranking）：  对候选集做精细评估，选出最相关的 top-3''')

add_bold_text(doc.add_paragraph(), 'Bi-Encoder vs Cross-Encoder：')
add_code_block('''Bi-Encoder（双塔模型，用于粗排）：
  query  →  [Encoder]  →  向量 A
  doc    →  [Encoder]  →  向量 B
  score = cosine(A, B)
  特点：query 和 document 各自独立编码
  优点：快！document 向量可以预计算存入数据库
  缺点：看不到 query 和 doc 的交互，精度有限

Cross-Encoder（交叉编码器，用于精排）：
  [query + doc 拼接]  →  [Encoder]  →  一个分数
  特点：query 和 document 拼在一起同时输入模型
  优点：能看到两段文本的交互关系，精度高很多
  缺点：慢！每来一个 query 都要和每个候选 doc 重新跑一遍''')

add_bold_text(doc.add_paragraph(), '具体例子：')
add_code_block('''query: "扫地机器人边刷不转"
doc_A: "扫地机器人边刷正常旋转说明电机没问题"
doc_B: "扫地机器人边刷不转可能原因：电机损坏、边刷卡住、驱动轮故障"

Bi-Encoder：两篇都含 "扫地机器人"+"边刷"，分数差距小
Cross-Encoder：doc_B 直接回答了"不转"的问题，分数远高于 doc_A''')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['Rag/reranker.py', 'RerankerService 类'],
        ['降级策略', 'BGE Cross-Encoder → TF-IDF → 直接取 top_n'],
        ['延迟加载', 'sentence_transformers 在函数内部导入'],
    ])

add_subsection('面试题')
add_qa('Q：什么是 Rerank？为什么需要它？',
    'Rerank 是在粗排检索结果上再做一次精细排序。粗排（如 ChromaDB 的 similarity_search）速度快但精度有限，因为 Bi-Encoder 把 query 和 doc 分开编码，看不到它们的交互。Rerank 用 Cross-Encoder 把 query 和 doc 拼在一起编码，能发现更细粒度的相关性，从 top-8 精排到 top-3。')

add_qa('Q：Cross-Encoder 和 Bi-Encoder 的区别？',
    'Bi-Encoder 把 query 和 doc 分别编码成向量，再算余弦相似度。doc 的向量可以预计算存入数据库，查询时只需编码 query，速度快但精度有限。Cross-Encoder 把 query 和 doc 拼在一起输入模型，能捕捉两者的交互关系，精度高但每次查询都要和每个候选 doc 重新计算，不能预计算。所以 Bi-Encoder 做粗排，Cross-Encoder 做精排。')

doc.add_page_break()

# ============================================================
# 八、混合检索整体链路
# ============================================================
add_section('八、混合检索整体链路')

add_subsection('完整数据流')
add_code_block('''用户提问："扫地机器人边刷不转怎么修"
  │
  ▼
① Dense 检索（ChromaDB）
  query → embedding → 余弦相似度 → top 8 篇
  │
  ▼
② BM25 检索（jieba 分词 → BM25Okapi）
  query → 分词 → 词频匹配 → top 8 篇
  │
  ▼
③ RRF 融合
  两路 top 8 → 按排名计算 RRF 分 → MD5 去重 → 合并排序 → top 8 篇
  │
  ▼
④ Rerank 精排
  top 8 → Cross-Encoder 打分 → 降序排列 → top 3 篇
  │
  ▼
⑤ 拼接 Context
  top 3 篇文档 → 拼成参考文本 → 喂给 LLM
  │
  ▼
⑥ LLM 生成回复
  qwen3.7-max 基于参考文本 + 用户问题 → 生成最终回答''')

add_subsection('面试题')
add_qa('Q：你的检索链路是什么样的？',
    '用户问题进来后，先走两路检索：Dense 向量检索（ChromaDB，语义匹配）和 BM25 稀疏检索（关键词匹配），各取 top-8；然后用 RRF 算法按排名融合去重；再过 Cross-Encoder 精排到 top-3；最后把 top-3 的文档拼成 context 喂给 LLM 生成回答。')

add_qa('Q：为什么要粗排 + 精排两阶段？',
    '直接用 Cross-Encoder 对所有文档打分太慢（每篇都要跑一次模型）。先粗排快速从几百篇文档中筛出 top-8，再精排只对 8 篇做 Cross-Encoder，兼顾速度和精度。这是一个经典的搜索系统设计模式。')

doc.add_page_break()

# ============================================================
# 九、Memory 机制
# ============================================================
add_section('九、Memory 机制')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '为什么不用全量历史消息？')
add_code_block('''问题 1：Token 爆炸
  30 天对话历史 + 长对话 → 轻松打满模型上下文窗口（8K~32K）
  超出窗口的部分被截断 → 丢失信息

问题 2：注意力稀释
  模型在几百轮历史中找不到真正相关的信息
  学术上叫 "Lost in the Middle" 问题

问题 3：幻觉风险
  长上下文里混杂大量无关内容 → 模型被"带偏" → 编造不存在的信息

问题 4：成本浪费
  每轮对话都在重发大量已无用的历史 → 消耗大量 token 费用''')

add_bold_text(doc.add_paragraph(), 'Memory 分层结构：')
add_code_block('''┌─────────────────────────────────────────┐
│  短期记忆（最近 5 轮完整对话）             │  ← 最近发生了什么
├─────────────────────────────────────────┤
│  对话摘要（窗口外的压缩）                   │  ← 之前聊了什么
├─────────────────────────────────────────┤
│  用户画像（长期信息）                       │  ← 这是一个什么样的用户
├─────────────────────────────────────────┤
│  工作记忆（当前任务上下文）                  │  ← 正在处理什么
└─────────────────────────────────────────┘''')

add_bold_text(doc.add_paragraph(), '更新机制：')
add_code_block('''每轮对话后触发 update_memory：
  1. 新消息追加到短期记忆
  2. 短期记忆超过 window_size → 最早的消息移出，进入摘要
  3. 用 LLM 重新生成摘要（压缩）
  4. 每 extract_interval 轮用 LLM 提取/更新用户画像
  5. 更新工作记忆（检测用户当前在追问什么）''')

add_subsection('项目中的位置')
add_table(['位置', '说明'],
    [
        ['utils/memory_manager.py', 'MemoryManager 类'],
        ['config/memory.yml', 'Memory 参数配置'],
        ['prompts/memory_summary.txt', '摘要压缩 prompt'],
        ['prompts/memory_extract.txt', '画像提取 prompt'],
        ['agent/react_agent.py', '开关逻辑，enabled=false 走原有全量历史'],
    ])

add_subsection('面试题')
add_qa('Q：Memory 机制解决什么问题？',
    '全量历史消息有三个问题：token 爆炸（对话越长，每次请求携带的 token 越多）、注意力稀释（模型在长上下文中找不到相关信息）、幻觉风险（无关内容干扰模型）。Memory 用分层压缩（短期对话 + 摘要 + 画像 + 工作记忆）替代全量历史，控制上下文大小。')

add_qa('Q：你的 Memory 分了哪几层？',
    '四层：短期记忆（最近 5 轮完整对话）、对话摘要（超出窗口的历史用 LLM 压缩）、用户画像（设备型号、故障历史等长期信息）、工作记忆（用户当前正在追问的问题）。四层组合起来替代全量历史。')

add_qa('Q：摘要丢失关键信息怎么办？',
    '摘要 prompt 里明确要求保留关键事实（设备型号、故障码、已尝试方案）。实际运行中需要用真实对话验证，如果发现丢失就调 prompt。这是一个持续调优的过程。同时有工作记忆层兜底——当前任务的上下文单独维护，不会被摘要压缩掉。')

add_qa('Q：用户画像怎么更新的？是覆盖还是增量？',
    '增量合并。每次提取画像时，把已有画像和最新对话一起传给 LLM。代码层面，列表类字段（如故障历史）用 dict.fromkeys(existing + new) 做追加去重，不是简单覆盖。')

doc.add_page_break()

# ============================================================
# 十、A2A 多 Agent 协作
# ============================================================
add_section('十、A2A 多 Agent 协作')

add_subsection('核心概念')
add_bold_text(doc.add_paragraph(), '什么是 A2A？',
    ' A2A（Agent-to-Agent）是 Google 提出的协议，让不同 Agent 之间可以互相通信和协作。')

add_bold_text(doc.add_paragraph(), '在你项目中的应用：')
add_code_block('''客服 Agent 生成回复
  │
  ▼
评估 Agent 独立打分（相关性、准确性、安全性、完整性）
  │
  ├─ score >= 阈值 → 放行，返回给用户
  │
  └─ score < 阈值 → 带着反馈重新生成
       │
       ├─ 重试成功 → 放行
       │
       └─ 达到最大重试次数 → 返回兜底话术''')

add_bold_text(doc.add_paragraph(), '关键设计：')
add_table(['维度', '设计要点'],
    [
        ['评分维度', '相关性、准确性、安全性、完整性，各带权重'],
        ['评估模型', '用 qwen-plus（轻量便宜快），不是 qwen3.7-max'],
        ['反馈机制', '低分时给出具体反馈，让重生成有方向'],
        ['最大重试', '2-3 次，防止死循环和 token 浪费'],
        ['兜底策略', '多次不过 → "抱歉，建议联系人工客服"'],
        ['开关', 'evaluator.enabled=false 时完全跳过'],
    ])

add_subsection('面试题')
add_qa('Q：为什么要加评估 Agent？',
    '客服场景对回复质量要求高。如果 Agent 编造了不存在的故障码或错误的维修方法，后果比一般 QA 严重。评估 Agent 作为独立的质量把关环节，自动检测幻觉和有害内容，低于阈值触发重生成。这是"回复质量风控"。')

add_qa('Q：评估 Agent 和客服 Agent 用同一个模型吗？',
    '不是。评估用 qwen-plus（轻量、便宜、快），生成用 qwen3.7-max。评估不需要很强的生成能力，但需要稳定的判断力。用小模型做评估也能节约成本——每次重试都要调一次评估模型，大模型成本太高。')

doc.add_page_break()

# ============================================================
# 十一、LangChain 核心概念
# ============================================================
add_section('十一、LangChain 核心概念')

add_subsection('核心概念')
add_table(['概念', '是什么', '项目中对应'],
    [
        ['Document', '文档结构体：page_content + metadata', 'ChromaDB 返回的每个文档块'],
        ['PromptTemplate', '带占位符的提示词模板', 'prompts/main_prompt.txt'],
        ['Tool', 'LLM 可调用的函数', 'agent/tools/agent_tools.py 里的 7 个工具'],
        ['Chain', '多个步骤串成的工作流', 'rag_service.py 的检索→拼context→生成'],
        ['Agent', 'LLM 自主决定调用 Tool 的循环', 'agent/react_agent.py'],
        ['Middleware', '拦截工具调用的钩子', 'agent/tools/middleware.py'],
    ])

add_bold_text(doc.add_paragraph(), 'ReAct 模式：')
add_code_block('''ReAct = Reasoning + Acting

循环过程：
  1. LLM 思考（Reasoning）→ 决定要调用什么工具
  2. LLM 行动（Acting）→ 调用工具获取信息
  3. LLM 观察（Observation）→ 看到工具返回的结果
  4. 回到步骤 1 → 判断信息是否足够，不够就继续调，够就生成最终回复''')

add_subsection('面试题')
add_qa('Q：LangChain 的 Agent 是怎么工作的？',
    '基于 ReAct 模式——LLM 看到用户问题后自主思考需要什么信息，选择调用对应的 Tool（如 rag_summarize 查知识库、get_weather 查天气），拿到工具返回结果后再判断是否足够回答。不够就再调用，够就生成最终回复。系统提示词里定义了每个工具的能力边界。')

add_qa('Q：Tool 是怎么注册的？',
    '用 LangChain 的 @tool 装饰器。装饰器给函数加上了名称、描述和参数 schema，这些信息会传给 LLM。LLM 根据"用户问题 + 所有工具的描述"来决定调用哪个工具，并自动填入参数。')

doc.add_page_break()

# ============================================================
# 十二、Python 工程实践
# ============================================================
add_section('十二、Python 工程实践')

add_subsection('项目中涉及的工程知识点')

add_bold_text(doc.add_paragraph(), '1. 延迟导入（Lazy Import）')
add_code_block('''# 错误做法：文件顶部导入，启动就触发
from sentence_transformers import CrossEncoder  # → torch 几百 MB

# 正确做法：函数内部导入，真正需要时才触发
def _load_bge():
    from sentence_transformers import CrossEncoder  # 延迟加载''')

add_bold_text(doc.add_paragraph(), '2. 三级降级策略')
add_code_block('''try:
    result = bge_rerank(docs)          # 第一级：最好
except:
    result = tfidf_rerank(docs)         # 第二级：兜底
    if not result:
        result = docs[:top_n]          # 第三级：直接取前 N''')

add_bold_text(doc.add_paragraph(), '3. 开关设计')
add_code_block('''if self.memory_enabled:
    context = memory.get_context(session_id)
else:
    context = original_history  # 完全走原有逻辑''')

add_bold_text(doc.add_paragraph(), '4. pickle 持久化')
add_code_block('''# 保存
with open("bm25_index.pkl", "wb") as f:
    pickle.dump((bm25_index, documents, signature), f)
# 加载
with open("bm25_index.pkl", "rb") as f:
    bm25_index, documents, signature = pickle.load(f)''')

add_bold_text(doc.add_paragraph(), '5. MD5 签名校验')
add_code_block('''import hashlib
current_md5 = hashlib.md5(file_content).hexdigest()
if current_md5 != stored_md5:
    rebuild_index()  # 文件变了，重建索引''')

add_bold_text(doc.add_paragraph(), '6. Redis 持久化')
add_code_block('''# 存
redis_client.setex(f"history:{session_id}", ttl, json.dumps(messages))
# 取
messages = json.loads(redis_client.get(f"history:{session_id}"))''')

add_subsection('面试题')
add_qa('Q：为什么 sentence_transformers 要延迟加载？',
    'Python 的 import 是静态的——模块顶部写 import 就会立即执行。sentence_transformers 依赖 transformers → torch → torchvision，torch 几百 MB，加载需要几秒。如果 Rerank 没开启，这些库完全不需要加载。延迟加载把开销推迟到第一次使用时。')

add_qa('Q：你的系统如果 Rerank 服务挂了怎么办？',
    '三级降级。第一级用 BGE Cross-Encoder 本地推理；如果加载失败，降级到 TF-IDF + 余弦相似度（纯 Python 计算，不需要模型）；如果 TF-IDF 也失败，直接取粗排的前 top_n 条。每一级都有 try/except 兜底，不会影响主流程。')

doc.add_page_break()

# ============================================================
# 十三、综合面试题
# ============================================================
add_section('十三、综合面试题')

add_subsection('项目整体')

add_qa('Q：介绍一下你的项目？',
    '我做的是一个基于 RAG 的智能客服系统，用于扫地机器人的故障排查和使用咨询。系统的核心是一个 ReAct Agent，能自主判断用户意图并调用相应工具。检索方面，我设计了混合检索架构——Dense 向量 + BM25 稀疏检索 + RRF 融合 + Cross-Encoder 精排，兼顾语义理解和精确匹配。另外实现了 Memory 机制解决长对话的 token 爆炸问题，以及多 Agent 协作做回复质量校验。')

add_qa('Q：项目中你遇到的最大技术挑战是什么？',
    'import 依赖链问题。项目中用了 langchain_text_splitters，但它间接依赖 sentence_transformers → torch → torchvision，torch 几百 MB 导致启动慢甚至崩溃。我的解决方案是：在 BM25 模块中完全不导入 langchain，自己实现文本分块；在 Reranker 中延迟加载 sentence_transformers，只在 enabled 时才触发。这让我理解了 Python import 机制和依赖管理的工程实践。')

add_subsection('开放性问题')

add_qa('Q：如果让你继续优化这个系统，你会做什么？',
    '三个方向：1) 查询改写——用 LLM 把用户的模糊查询改写为更明确的形式再检索；2) 多轮检索——根据用户的追问动态调整检索策略；3) 评估数据闭环——收集评估 Agent 的打分数据，用于优化检索参数和 prompt。')

add_qa('Q：你觉得你的项目还有什么不足？',
    'Memory 机制的摘要质量需要持续调优，可能丢失关键细节；BM25 的自定义词典需要根据实际使用不断补充；A2A 评估 Agent 的阈值需要更多真实 case 来标定。这些都是需要在实际运行中迭代优化的。')

doc.add_page_break()

# ============================================================
# 学习优先级建议
# ============================================================
add_section('学习优先级建议')

add_code_block('''必须完全掌握（面试必问）：
  ✓ 向量检索基本原理（Embedding + 余弦相似度）
  ✓ BM25 思想（词频 × 稀有度）
  ✓ RRF 融合（为什么用排名不用分数）
  ✓ 混合检索链路（能画出数据流图）
  ✓ Memory 机制（为什么需要、分几层）
  ✓ ReAct Agent 工作模式

理解即可（大概率会问但不会深挖）：
  ○ Cross-Encoder vs Bi-Encoder 的区别
  ○ jieba 分词和自定义词典
  ○ ChromaDB 的 Document 结构
  ○ 延迟导入和三级降级的工程意义

了解概念（可能被问到你用过什么）：
  △ LangChain 的 Tool / Chain / Middleware
  △ Redis 持久化
  △ pickle 序列化
  △ MD5 签名校验''')

# 保存
output_path = r'C:\Users\20115\Desktop\agent_project\docs\RoboServe_学习清单与面试题.docx'
doc.save(output_path)
print(f'Word 文档已保存: {output_path}')

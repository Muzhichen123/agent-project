# RAG 客服系统优化 — 总体集成方案

## 项目概览

本文档描述扫地机器人客服 RAG 系统的四大优化模块的集成顺序、依赖关系、实施路线和测试策略。

## 1. 四大优化模块总览

| # | 模块 | 新建文件 | 修改文件 | 配置文件 |
|---|------|---------|---------|---------|
| 1 | Rerank 精排 | `Rag/reranker.py` | `Rag/rag_service.py` | `config/rag.yml`, `config/chroma.yml` |
| 2 | 混合检索 | `Rag/bm25_store.py`, `data/custom_dict.txt` | `Rag/rag_service.py`, `Rag/vector_store.py` | `config/chroma.yml` |
| 3 | A2A 评估 | `agent/evaluator.py`, `prompts/evaluator.txt`, `prompts/regenerate.txt` | `agent/react_agent.py` | `config/evaluator.yml` (新建) |
| 4 | Memory 机制 | `utils/memory_manager.py`, `config/memory.yml`, `prompts/memory_summary.txt`, `prompts/memory_extract.txt` | `agent/react_agent.py` | `config/memory.yml` (新建) |

详细设计分别见:
- `docs/design/01_rerank.md`
- `docs/design/02_hybrid_retrieval.md`
- `docs/design/03_a2a_evaluator.md`
- `docs/design/04_memory.md`

## 2. 模块依赖关系

```
模块 1 (Rerank)          ──┐
                          ├──→ 模块 3 (A2A 评估)
模块 2 (混合检索) ──→ 模块 1 ──┘
                          │
模块 4 (Memory)    ───────┘  (独立于检索优化，但和 A2A 有间接关系)
```

依赖说明:
- **模块 2 依赖模块 1**: 混合检索扩大召回到 top-10，需要 Rerank 精排到 top-3，两者配合才有最佳效果
- **模块 3 依赖模块 1+2**: A2A 评估的准确性依赖检索质量。如果检索给到模型的参考资料就是错的，再怎么评估也没用
- **模块 4 独立**: Memory 机制和检索管线无关，可以并行开发

## 3. 实施路线（按天排）

### Phase 1: 检索优化（Day 1-4）

#### Day 1: 模块 1 — Rerank

```
上午:
  - 阅读 docs/design/01_rerank.md
  - 查阅 DashScope Rerank API 文档，确认接口格式
  - 创建 Rag/reranker.py
  - 修改 config/rag.yml 添加 rerank 配置
  - 修改 config/chroma.yml 将 k 从 3 改为 8

下午:
  - 修改 Rag/rag_service.py 集成 reranker
  - 编写测试脚本验证
  - 准备 5 个测试 query 对比有无 Rerank 的效果

验收标准:
  - Rerank API 调用成功，返回排序结果
  - rag_service 正常工作，无报错
  - 打开/关闭 rerank.enabled 配置可正常切换
```

#### Day 2-3: 模块 2 — 混合检索

```
Day 2 上午:
  - 阅读 docs/design/02_hybrid_retrieval.md
  - 安装 rank_bm25 和 jieba
  - 创建 data/custom_dict.txt（根据知识库内容补充术语）
  - 创建 Rag/bm25_store.py

Day 2 下午:
  - 修改 config/chroma.yml 添加 hybrid_search 配置
  - 修改 Rag/vector_store.py，在 load_documents 末尾同步构建 BM25 索引
  - 测试 BM25 分词效果和索引构建

Day 3:
  - 修改 Rag/rag_service.py 实现 RRF 融合
  - 集成测试: Dense + BM25 → RRF → Rerank → LLM
  - 调参: rrf_k, dense_top_k, bm25_top_k, final_top_k
  - 对比测试: 10 个 query 对比优化前后

验收标准:
  - BM25 索引正常构建和持久化
  - RRF 融合返回合理结果
  - 精确匹配场景（型号名、故障码）检索质量明显提升
  - 文档更新时 BM25 索引同步更新
```

#### Day 4: 检索联调 + 性能测试

```
上午:
  - 端到端测试: 用户提问 → 混合检索 → Rerank → RAG 总结 → Agent 回复
  - 回归所有场景: 日常对话、天气查询、报告生成

下午:
  - 性能测试: 记录各环节耗时
    - Dense 检索: ____ ms
    - BM25 检索: ____ ms
    - RRF 融合: ____ ms
    - Rerank: ____ ms
    - 端到端: ____ ms
  - 如果总耗时 > 3 秒，分析瓶颈并优化

验收标准:
  - 所有现有功能正常
  - 端到端延迟 < 3 秒（不含 LLM 生成时间）
  - 检索结果质量可量化提升
```

### Phase 2: 上下文优化（Day 5-8）

#### Day 5-6: 模块 4 — Memory 机制（设计 + 实现）

```
Day 5 上午:
  - 阅读 docs/design/04_memory.md
  - 确认 Memory schema 设计（可按需调整）
  - 创建 config/memory.yml
  - 创建 prompts/memory_summary.txt 和 prompts/memory_extract.txt

Day 5 下午:
  - 创建 utils/memory_manager.py
  - 实现核心功能: get_context, update_memory, _update_summary, _extract_profile

Day 6:
  - 修改 agent/react_agent.py 集成 MemoryManager
  - 实现开关逻辑（memory.enabled 控制是否启用）
  - 单元测试 Memory 基本功能

验收标准:
  - Memory 创建、读取、更新正常
  - 摘要压缩功能正常
  - 开关逻辑正常（关闭时走原有 Redis 全量历史）
```

#### Day 7-8: 模块 4 — Memory 集成 + 回归测试

```
Day 7:
  - 回归测试所有场景:
    - 日常对话（连续 20 轮，验证 Memory 压缩效果）
    - 故障排查（验证工作记忆跟踪）
    - 报告生成（验证中间件标记不受影响）
    - 新会话（验证从空白 Memory 开始）
  - 对比测试: Memory 模式 vs 全量历史模式，回复质量是否有下降

Day 8:
  - Token 对比测试: 不同轮数的对话，上下文 token 数对比
  - 性能测试: Memory 更新的额外耗时
  - 修复发现的问题
  - 调优 prompt: memory_summary.txt 和 memory_extract.txt

验收标准:
  - 50 轮对话后上下文 token 数 < 3000
  - 回复质量无明显下降
  - 报告生成场景正常
  - Memory 更新耗时 < 2 秒
```

### Phase 3: 质量兜底（Day 9-12）

#### Day 9-10: 模块 3 — A2A 评估 Agent

```
Day 9:
  - 阅读 docs/design/03_a2a_evaluator.md
  - 创建 config/evaluator.yml
  - 创建 prompts/evaluator.txt 和 prompts/regenerate.txt
  - 创建 agent/evaluator.py

Day 10:
  - 修改 agent/react_agent.py 集成评估逻辑
  - 实现重试回路和兜底机制
  - 单元测试评估器（正常回复/幻觉回复/有害回复）
  - 测试重试机制

验收标准:
  - 评估器正常打分
  - 通过的回复直接放行
  - 不通过的回复触发重试
  - 重试耗尽后使用兜底话术
```

#### Day 11-12: 整体联调 + 压力测试

```
Day 11:
  - 四个模块全部开启，端到端测试
  - 准备 30-50 个测试 case（覆盖日常对话、故障排查、型号查询、报告生成等）
  - 逐一验证，记录评估日志

Day 12:
  - 阈值调优: 根据测试结果调整
    - evaluator.pass_threshold
    - memory.short_term.window_size
    - hybrid_search.rrf_k
    - rerank.top_n
  - 性能压测: 模拟 10 个并发请求
  - 文档整理: 更新 README.md

验收标准:
  - 所有测试 case 通过
  - 端到端响应时间 < 8 秒（含评估时间）
  - 评估器误杀率 < 10%（好的回复被误判为不通过）
  - Memory 在长对话中稳定运行
```

## 4. 配置开关设计

每个模块都有独立的 enabled 开关，可以独立开启/关闭:

```yaml
# config/chroma.yml
hybrid_search:
  enabled: true   # 模块 2

# config/rag.yml
rerank:
  enabled: true   # 模块 1

# config/evaluator.yml
evaluator:
  enabled: true   # 模块 3

# config/memory.yml
memory:
  enabled: true   # 模块 4
```

**推荐的开启顺序**:
1. 先单独开 Rerank → 验证
2. 再开混合检索 → 验证
3. 再开 Memory → 验证
4. 最后开 A2A 评估 → 验证

**全部关闭时**: 系统行为和当前完全一致，零风险回退。

## 5. 新增依赖汇总

```
# requirements.txt 新增
rank-bm25>=0.2.2
jieba>=0.42.1
```

其余模块无新增依赖（Rerank 用 HTTP API，A2A 和 Memory 复用现有 langchain/redis）。

## 6. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| DashScope Rerank API 格式变化 | 模块 1 不可用 | 代码中做好异常捕获，失败时回退到粗排 |
| BM25 索引构建慢 | 知识库更新延迟 | 当前知识库小（6文件），可接受；后续考虑增量更新 |
| Memory 摘要丢失关键信息 | 模型忘记重要上下文 | 反复调摘要 prompt；保留短期记忆窗口足够大 |
| A2A 评估器误杀 | 正常回复被拦截导致重试 | 初始阈值设宽松（3.0）；逐步收紧 |
| 评估增加延迟 | 用户等待时间变长 | 用轻量模型 qwen-plus 做评估；异步评估方案（后续） |
| 全部模块叠加后性能 | 端到端延迟过高 | 各模块有独立开关，可以按需关闭 |

## 7. 后续优化方向（第二期）

以下不在当前范围内，记录备忘:

- **BM25 → Elasticsearch**: 知识库规模扩大后迁移到 ES
- **Memory 异步更新**: 先返回回复，后台更新 Memory
- **A2A 异步评估**: 先发回复，后台评估，不通过则发补充消息
- **用户画像持久化**: 跨 session 的用户画像（当前按 session 隔离）
- **检索质量监控**: 自动化的检索质量评估和告警
- **A/B 测试框架**: 在线 A/B 测试不同配置的效果

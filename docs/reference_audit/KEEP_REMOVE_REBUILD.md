# KEEP / REMOVE / REBUILD

面向未来独立仓库 `tk-script-agent-lab`，本文件只分类原项目中值得借鉴、应舍弃和必须重建的内容。结论不是要求复制原项目源码，也明确禁止把原仓库直接改造成新项目。

## 1. KEEP

| 项 | 可借鉴模式 | 原项目证据 | 为什么保留 |
|---|---|---|---|
| K1 | 单一 Graph 入口 | `langgraph.json` 将 `agent` 指向 `./src/enrichment_agent/graph.py:graph`（`langgraph.json:L4-L6`） | 教学型 Agent 需要一个清晰入口，便于 Studio、测试和部署 |
| K2 | Configuration 独立 | `Configuration` dataclass 集中模型、prompt、预算配置（`src/enrichment_agent/configuration.py:L13-L62`） | 配置和业务状态分离，便于替换模型和控制预算 |
| K3 | 输入/内部/输出 State 分层 | `InputState`、`State`、`OutputState` 分开定义（`src/enrichment_agent/state.py:L15-L87`） | 新项目可清楚区分用户输入、中间过程和最终输出 |
| K4 | StateGraph 节点编排 | `StateGraph(State, input_schema=..., output_schema=..., context_schema=...)`（`src/enrichment_agent/graph.py:L216-L219`） | 适合展示 Agent 工作流、状态流转和可视化调试 |
| K5 | ToolNode 模式 | `ToolNode([search, scrape_website])`（`src/enrichment_agent/graph.py:L222-L225`） | 工具执行与模型决策分离，是教学 Agent 的核心模式 |
| K6 | Structured Output 思路 | 动态 `Info` tool 和 Reflection Pydantic 输出（`src/enrichment_agent/graph.py:L37-L42`，`src/enrichment_agent/graph.py:L85-L98`） | 新项目应保留“结构化产物”概念，但 schema 应固定为 TikTok 领域模型 |
| K7 | Conditional Edge | `add_conditional_edges` 用于 agent 和 checker 路由（`src/enrichment_agent/graph.py:L224-L226`） | 适合表达 Human Gate、质量检查、重试和结束条件 |
| K8 | 最大循环限制概念 | `max_loops` 配置和 Reflection 后判断（`src/enrichment_agent/configuration.py:L47-L52`，`src/enrichment_agent/graph.py:L197-L213`） | 新项目需要预算和停止条件，但应覆盖所有循环边 |
| K9 | Studio 配置体验 | README 说明可在 Studio 输入 state/config（`README.md:L127-L139`） | 教学项目需要可视化演示入口 |
| K10 | 测试分层 | 单测和集成测试目录分离（`tests/unit_tests/test_configuration.py:L1-L5`，`tests/integration_tests/test_graph.py:L34-L121`） | 新项目应保留分层，但扩展确定性测试和 eval |

## 2. REMOVE

| 项 | 应舍弃内容 | 原项目证据 | 为什么不适合 TikTok Script Agent |
|---|---|---|---|
| R1 | 通用网页研究 `topic` 输入 | `InputState.topic` 是泛化研究主题（`src/enrichment_agent/state.py:L19-L20`） | TikTok 脚本应围绕商品、受众、卖点、视频参考等固定业务对象 |
| R2 | 用户动态传入任意 `extraction_schema` | `InputState.extraction_schema` 直接进入 `Info` tool 参数（`src/enrichment_agent/state.py:L22-L23`，`src/enrichment_agent/graph.py:L37-L42`） | 新项目需要稳定领域 schema，避免任意 schema 破坏教学边界 |
| R3 | Tavily 搜索业务 | `search()` 使用 `TavilySearch`（`src/enrichment_agent/tools.py:L23-L34`） | TikTok Lab 的核心不是泛网页搜索，应换成本地知识库/参考素材检索 |
| R4 | 通用网页抓取 | `scrape_website()` 用 aiohttp GET 任意 URL（`src/enrichment_agent/tools.py:L52-L65`） | 商品脚本生成不应依赖任意网页正文抓取 |
| R5 | 网页摘要模型工具 | 抓取后把 content[:40000] 交给模型总结（`src/enrichment_agent/tools.py:L67-L74`） | 新项目需要可追踪事实抽取，不应把网页摘要作为事实基础 |
| R6 | 通用 data enrichment prompt | `MAIN_PROMPT` 面向 web research 和 Info tool（`src/enrichment_agent/prompts.py:L3-L17`） | TikTok 脚本需要创意、合规、卖点、口播结构和人审语义 |
| R7 | 围绕 search/scrape 的循环 | `tools -> call_agent_model`（`src/enrichment_agent/graph.py:L225-L226`） | 新项目循环应围绕素材检索、事实校验、脚本草稿、Human Gate |
| R8 | 任意 URL 继续研究建议 | checker prompt 可鼓励 Assistant 看 URL 或搜索（`src/enrichment_agent/graph.py:L125-L130`） | TikTok 项目应明确允许来源和素材库，不开放泛网页探索 |

## 3. REBUILD

| 项 | 新项目能力 | 为什么不能直接复制 |
|---|---|---|
| B1 | `ProductProfile` | 原项目只有 `topic` 和动态 schema；商品资料需要固定字段、来源、禁用词和合规信息 |
| B2 | `ProductFact` | 原项目 `info` 不绑定事实来源；商品事实必须可追踪、可校验 |
| B3 | `SellingPoint` | 原项目不建模卖点优先级、受众痛点、证据强度 |
| B4 | `ReferenceVideo` | 原项目只处理网页/搜索结果，不处理视频素材、字幕、表现形式 |
| B5 | `ReferenceInsight` | 需要从参考视频中提炼 hook、节奏、结构，而非网页摘要 |
| B6 | `CreativeIdea` | 原项目是资料补全，不是创意生成管线 |
| B7 | `SourceUsage` | 原项目没有来源字段强制校验；新项目要记录每条脚本事实使用了哪个 source |
| B8 | `ScriptDraft` | 原项目输出任意 `info` dict；脚本要有 hook、scene、voiceover、caption、CTA 等结构 |
| B9 | Human Gate | 原项目没有人工审核节点；TikTok 脚本应在人审后才能进入关键生成或发布态 |
| B10 | 本地知识库 RAG | 原项目只有联网搜索增强，不具备 embedding/vector/top-k/metadata filter |
| B11 | 确定性事实校验 | Reflection 是模型自评；新项目需要代码校验商品事实、来源覆盖和禁用声明 |
| B12 | Run Trace | 原项目仅依赖 messages，没有独立 trace schema；教学项目应显示每步输入、输出、来源和预算 |
| B13 | Eval | 原项目测试只做少量端到端断言；新项目需要固定样例、回归评估和失败用例 |
| B14 | 错误状态与预算 | 原项目无独立错误 state，工具循环缺少显式上限；新项目要重建统一预算和错误路径 |

## 4. 原项目与未来项目职责边界

| 维度 | 原项目 `data-enrichment` | 未来 `tk-script-agent-lab` |
|---|---|---|
| 主要任务 | 泛化网页研究并填充用户 schema | 教学型 TikTok 脚本 Agent |
| 输入 | `topic` + 任意 `extraction_schema` | 商品资料、参考视频、知识库材料、创作约束 |
| 外部数据 | Tavily 搜索、任意网页抓取 | 本地知识库、明确上传或内置素材、可控参考数据 |
| 中间状态 | `messages`、`info`、`loop_step` | product facts、sources、insights、ideas、draft、review state、trace |
| 模型职责 | 搜索决策、网页摘要、Info 填充、Reflection | 创意生成、脚本草拟、局部解释；不负责最终事实证明 |
| 代码职责 | Graph 编排和少量路由 | Schema 校验、来源绑定、事实检查、预算、错误路径、eval |
| 输出 | 任意 `info` dict | 可审计脚本草稿和来源使用说明 |

## 5. 建议的新仓库最小结构

```text
tk-script-agent-lab/
  README.md
  pyproject.toml
  langgraph.json
  .env.example
  src/tk_script_agent_lab/
    __init__.py
    configuration.py
    state.py
    graph.py
    prompts.py
    tools.py
    validators.py
    trace.py
  tests/
    unit_tests/
      test_configuration.py
      test_state_validation.py
      test_fact_validation.py
      test_routing.py
    integration_tests/
      test_graph_fixture_run.py
  data/
    fixtures/
      products/
      reference_videos/
      knowledge_base/
  docs/
    architecture.md
    eval_plan.md
```

这是最小教学型骨架建议，不应在当前仓库内实施。

## 6. 可参考的代码模式

可参考但不直接照搬的模式：

| 模式 | 原项目位置 | 新项目改造方向 |
|---|---|---|
| `Configuration.from_runnable_config` | `src/enrichment_agent/configuration.py:L54-L62` | 保留字段筛选模式，增加范围校验和默认值测试 |
| dataclass State | `src/enrichment_agent/state.py:L15-L87` | 换成 TikTok 领域字段，明确错误和 trace |
| `add_messages` reducer | `src/enrichment_agent/state.py:L39-L67` | 保留模型/工具消息历史，同时增加结构化 trace |
| `StateGraph(...).compile()` | `src/enrichment_agent/graph.py:L216-L228` | 重建 product/profile -> retrieve -> validate -> ideate -> draft -> human gate |
| `ToolNode` | `src/enrichment_agent/graph.py:L222-L225` | 换成本地素材检索、事实查找、脚本检查工具 |
| Structured output checker | `src/enrichment_agent/graph.py:L85-L98` | 用 Pydantic 固定输出模型，不接受用户任意 schema |
| 条件路由 | `src/enrichment_agent/graph.py:L163-L213` | 加入 deterministic validation failure、human review、budget exceeded 分支 |

## 7. 许可注意

原项目 `pyproject.toml` 声明许可证为 MIT（`pyproject.toml:L8-L10`），`LICENSE` 要求复制或 substantial portions 使用时包含版权和许可声明（`LICENSE:L1-L13`）。如果未来项目复制本仓源码片段、文件结构中的实质代码或 prompt，需要保留 MIT 许可文本和版权声明。仅借鉴架构模式、重新实现领域代码，通常不需要复制源码，但仍应在文档中标明参考来源更稳妥。

## 8. 后续创建 `tk-script-agent-lab` 的最小入口

建议第一步是在独立目录创建最小教学 Graph：

```text
Input: ProductProfile + ReferenceMaterial IDs
State: product_facts, source_usage, reference_insights, creative_ideas, script_draft, validation_errors, trace
Nodes:
  load_inputs -> retrieve_local_sources -> extract_product_facts -> validate_facts
  -> generate_creative_ideas -> draft_script -> deterministic_script_check
  -> human_gate -> END
```

首批测试应优先覆盖：schema 校验、source_usage 必填、事实不允许无来源、预算上限、Human Gate 路由、fixture run 结果稳定。

## 9. 明确禁止直接改造原仓库

不要把 `data-enrichment` 直接改造成 `tk-script-agent-lab`。原因：

| 原因 | 说明 |
|---|---|
| 业务边界不同 | 原仓围绕网页研究和任意 schema；新仓围绕 TikTok 脚本教学和固定领域模型 |
| 数据来源不同 | 原仓依赖 Tavily/网页；新仓应基于本地知识库和受控参考素材 |
| 校验要求不同 | 原仓主要靠 LLM Reflection；新仓必须有确定性事实和来源校验 |
| 测试目标不同 | 原仓集成测试依赖真实服务；新仓应从 fixture 和 eval 开始 |
| 许可与维护清晰度 | 独立仓库更容易保留参考声明、控制范围，并避免污染原模板 |

结论：保留 Graph/State/Tool/Structured Output/Conditional Edge 等工程模式，删除网页研究业务假设，围绕 TikTok 脚本领域模型、来源追踪、确定性校验和教学可解释性重建。

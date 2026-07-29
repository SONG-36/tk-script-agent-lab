# Reference Architecture Audit

审计对象：`data-enrichment`。本审计只读检查既有代码、配置、测试和文档，仅新增本 Markdown 报告。

## 1. 仓库现场

| 项目 | 记录 |
|---|---|
| 当前工作目录 | `/Volumes/server-data/projects/andy/data-enrichment` |
| Git 顶层 | `/Volumes/server-data/projects/andy/data-enrichment` |
| 分支 | `main...origin/main` |
| HEAD | `6ca652518d234cc2043ea275cc400bec68f60075` |
| 最新提交 | `6ca6525 Merge pull request #30 from langchain-ai/dependabot/uv/uv-fec1d00dd4` |
| Remote | `origin https://github.com/langchain-ai/data-enrichment.git` |
| 初始未提交修改 | 无，`git status --short --branch` 仅输出分支行 |
| 初始未跟踪文件 | 无 |
| 现有 `.env` | 存在，`find . -maxdepth 3 -type f` 列出 `./.env` |
| 现有虚拟环境 | 存在，`test -d .venv` 返回 `.venv exists` |
| 可能影响审计的本地改动 | 未发现 Git 可见改动；但存在本地 `.env` 和 `.venv`，可能影响实际运行环境 |

文件结构与任务预期基本一致：存在 `README.md`、`pyproject.toml`、`langgraph.json`、`Makefile`、`.env.example`、`src/enrichment_agent/`、`tests/`、`ntbk/testing.ipynb`。`docs/` 在审计前不存在。

## 2. 项目定位

该项目是 LangGraph Data Enrichment 模板。README 说明它从开放式网页研究中生成结构化结果，目标是填充数据库或表格；示例 Graph 位于 `src/enrichment_agent/graph.py`，可自动从网页收集某个 topic 的信息并按用户 JSON Schema 组织输出（`README.md:L6-L7`）。

输入是用户提供的 `topic` 和 `extraction_schema`（`README.md:L12-L18`，`src/enrichment_agent/state.py:L15-L27`）。输出是 `info: dict[str, Any]`（`src/enrichment_agent/state.py:L75-L87`）。

使用 LangGraph 的原因是把研究 Agent 分成明确节点、状态、工具节点、条件路由和循环：`StateGraph` 在 `graph.py` 中创建，节点包括模型节点、工具节点和反思节点（`src/enrichment_agent/graph.py:L216-L228`）。Tool Calling 用于让模型选择 `search`、`scrape_website` 或动态 `Info` 工具（`src/enrichment_agent/graph.py:L37-L55`）。

Tavily 是联网搜索工具的实现：`search()` 用 `TavilySearch(max_results=configuration.max_search_results)` 发起外部搜索（`src/enrichment_agent/tools.py:L23-L34`）。Structured Output 主要有两层：最终 `Info` 是模型绑定的动态工具，其参数直接来自用户传入的 `extraction_schema`（`src/enrichment_agent/graph.py:L37-L42`）；Reflection 使用 Pydantic `InfoIsSatisfactory` 和 `with_structured_output()` 要求检查模型输出结构化判断（`src/enrichment_agent/graph.py:L85-L98`，`src/enrichment_agent/graph.py:L133-L135`）。

README 称项目会验证完整性和准确性（`README.md:L14-L19`），但源码显示验证本身仍由模型判断完成，并不是确定性事实校验（`src/enrichment_agent/graph.py:L101-L160`）。因此“准确性验证”应理解为 LLM reflection，而非事实正确性证明。

## 3. 目录与模块职责

| 路径 | 职责 | 证据 |
|---|---|---|
| `langgraph.json` | 声明 LangGraph API/Studio 的 graph 入口和 `.env` | `langgraph.json:L1-L7` |
| `pyproject.toml` | 包元数据、MIT 许可证、依赖、dev 依赖 | `pyproject.toml:L1-L19`，`pyproject.toml:L56-L62` |
| `Makefile` | 本地 test、integration_tests、lint 命令 | `Makefile:L7-L23`，`Makefile:L38-L47` |
| `.env.example` | Tavily、LangSmith、模型供应商 key 示例 | `.env.example:L1-L11` |
| `configuration.py` | RunnableConfig/Studio 可配置字段 | `src/enrichment_agent/configuration.py:L13-L62` |
| `state.py` | 输入、内部 State、输出 State | `src/enrichment_agent/state.py:L15-L87` |
| `graph.py` | 模型节点、Reflection、路由、Graph 编译 | `src/enrichment_agent/graph.py:L22-L228` |
| `tools.py` | Tavily 搜索和网页抓取摘要工具 | `src/enrichment_agent/tools.py:L23-L74` |
| `prompts.py` | 主 prompt 模板 | `src/enrichment_agent/prompts.py:L1-L17` |
| `utils.py` | 模型初始化和消息文本工具 | `src/enrichment_agent/utils.py:L13-L34` |
| `tests/` | 单测和真实集成测试 | `tests/unit_tests/test_configuration.py:L1-L5`，`tests/integration_tests/test_graph.py:L34-L121` |
| `ntbk/testing.ipynb` | LangGraph SDK 调用示例，包含 notebook 内安装提示 | `ntbk/testing.ipynb` 中匹配行 `L30`、`L39-L41`、`L117-L122` |

## 4. 运行入口

调用关系：

```text
langgraph.json
-> ./src/enrichment_agent/graph.py:graph
-> StateGraph(State, input_schema=InputState, output_schema=OutputState, context_schema=Configuration)
-> call_agent_model
-> conditional route_after_agent
-> tools ToolNode([search, scrape_website]) 或 reflect
-> conditional route_after_checker
-> call_agent_model 或 END
-> compiled graph
```

| 问题 | 结论 | 证据 |
|---|---|---|
| `langgraph.json` 指向哪个 Graph | `agent` 指向 `./src/enrichment_agent/graph.py:graph` | `langgraph.json:L4-L6` |
| Graph 对象在哪里创建 | `workflow = StateGraph(...)` | `src/enrichment_agent/graph.py:L216-L219` |
| Graph 在哪里 compile | `graph = workflow.compile()`，名称 `ResearchTopic` | `src/enrichment_agent/graph.py:L228-L229` |
| 本地开发命令 | README 建议用 LangGraph Studio 打开目录并输入状态 | `README.md:L24-L35`，`README.md:L127-L139` |
| 单元测试命令 | `make test` 等价于 `python -m pytest tests/unit_tests/` | `Makefile:L7-L10` |
| 集成测试命令 | `make integration_tests` 跑 `tests/integration_tests` | `Makefile:L12-L13` |
| CI 单测 | GitHub Actions 安装依赖、ruff、mypy、pytest | `.github/workflows/unit-tests.yml:L34-L60` |
| CI 集成测试 | 需要 Anthropic、Tavily、LangSmith secret | `.github/workflows/integration-tests.yml:L39-L46` |
| Notebook 入口 | 用 `langgraph_sdk.get_client()` 连接本地 LangGraph API 并 stream run | `ntbk/testing.ipynb` 匹配行 `L39-L41`、`L117-L122` |

## 5. 输入模型

输入是 dataclass，不是 Pydantic、TypedDict 或普通 dict。`InputState` 定义 `topic: str`、`extraction_schema: dict[str, Any]`、可选 `info`（`src/enrichment_agent/state.py:L15-L27`）。Graph 声明 `input_schema=InputState`（`src/enrichment_agent/graph.py:L216-L219`）。

代码没有在进入 Graph 前对 `extraction_schema` 做确定性 JSON Schema 校验。它会被直接作为工具参数 schema：`info_tool["parameters"] = state.extraction_schema`（`src/enrichment_agent/graph.py:L37-L42`）。无效 schema 最可能在 `raw_model.bind_tools(...)`、模型供应商工具 schema 转换或 `ainvoke()` 时失败（`src/enrichment_agent/graph.py:L53-L55`），而不是在项目自有代码中提前失败。

| 字段 | 定义位置 | 类型 | 来源 | 使用节点 | 风险 |
|---|---|---|---|---|---|
| `topic` | `src/enrichment_agent/state.py:L19-L20` | `str` | 用户输入或 LangGraph API/Studio input | `call_agent_model`、`reflect` prompt 格式化 | 未做长度、注入或领域校验 |
| `extraction_schema` | `src/enrichment_agent/state.py:L22-L23` | `dict[str, Any]` | 用户输入 | `call_agent_model` 创建 `Info` tool；`reflect` prompt；`scrape_website` 摘要 prompt | 任意 schema 可能格式非法、过大、语义诱导模型 |
| `info` | `src/enrichment_agent/state.py:L25-L26` | `Optional[dict[str, Any]]` | 初始可由用户传入，通常由模型提交 | `call_agent_model` 写入；`reflect` 读取和可能写回；OutputState 暴露 | 可由模型伪造，格式与事实正确性不等价 |
| `model` | `src/enrichment_agent/configuration.py:L17-L23` | `str` | 默认值或 RunnableConfig/Studio configurable | `init_model` | 默认模型与 README 旧自动配置不一致 |
| `prompt` | `src/enrichment_agent/configuration.py:L25-L31` | `str` | 默认或 RunnableConfig | `call_agent_model` | 可配置 prompt 可改变行为和安全边界 |
| `max_search_results` | `src/enrichment_agent/configuration.py:L33-L38` | `int` | 默认或 RunnableConfig | `search` | 未见范围校验；过大可能成本/延迟风险 |
| `max_info_tool_calls` | `src/enrichment_agent/configuration.py:L40-L45` | `int` | 默认或 RunnableConfig | 未被源码使用 | 配置存在但不生效，不能限制 Info 调用 |
| `max_loops` | `src/enrichment_agent/configuration.py:L47-L52` | `int` | 默认或 RunnableConfig | `route_after_checker` | 只在 Reflection 后判断，不限制工具循环 |

## 6. State

`State` 继承 `InputState`，新增 `messages` 和 `loop_step`（`src/enrichment_agent/state.py:L29-L72`）。它没有直接使用 `MessagesState`，但 `messages` 使用 `add_messages` reducer，具备消息累积/按 ID 替换语义（`src/enrichment_agent/state.py:L39-L67`）。`ToolNode` 会把工具执行结果作为 `ToolMessage` 写回 `messages`，项目源码通过 `ToolNode([search, scrape_website])` 接入（`src/enrichment_agent/graph.py:L222-L225`）。

| State 字段 | 初始来源 | 读取节点 | 写入节点 | 更新方式 | 风险 |
|---|---|---|---|---|---|
| `topic` | 用户输入 | `call_agent_model`、`reflect` | 无 | 替换式状态字段 | 未校验 topic 真实性或范围 |
| `extraction_schema` | 用户输入 | `call_agent_model`、`reflect`、`scrape_website` | 无 | 替换式状态字段 | 动态工具 schema 注入点；无本地 schema 校验 |
| `info` | 初始可选；通常模型 `Info` tool args | `reflect`、`route_after_checker`、OutputState | `call_agent_model`、`reflect` | 替换式字段 | 保存最终结构化结果，但不能证明事实准确 |
| `messages` | 默认空列表；模型/工具逐步添加 | `call_agent_model`、`reflect`、`route_after_agent`、`route_after_checker` | `call_agent_model`、`ToolNode`、`reflect` | `add_messages` 追加或同 ID 替换 | 保存模型原始消息、工具结果和 Reflection ToolMessage；上下文可膨胀 |
| `loop_step` | 默认 `0` | `route_after_checker` | `call_agent_model` | `operator.add` 累加，每次模型主节点 +1 | 只统计主模型节点调用，不直接限制工具调用数量 |

错误和重试信息没有独立 State 字段。工具异常主要依赖 `ToolNode` 默认行为；Reflection 不满意时写入 `ToolMessage(status="error")`（`src/enrichment_agent/graph.py:L149-L159`）。

## 7. Graph 和 Node

实际 Graph：

```text
START
-> call_agent_model
-> route_after_agent
   -> reflect, 如果最后 AIMessage 调用了 Info
   -> tools, 如果最后 AIMessage 调用了 search/scrape_website/其他工具
   -> call_agent_model, 如果最后消息不是 AIMessage
tools
-> call_agent_model
reflect
-> route_after_checker
   -> call_agent_model, 如果未达 max_loops 且无 info 或 Reflection ToolMessage 为 error
   -> END, 如果满意或达到 max_loops
```

| Node | 类型 | 读取数据 | 写入数据 | 是否调用模型 | 是否调用工具 | 下一步 |
|---|---|---|---|---|---|---|
| `call_agent_model` | MODEL | `topic`、`extraction_schema`、`messages`、config | `messages`、`info`、`loop_step` | 是，`model.ainvoke()` | 绑定工具，但由模型决定 tool call | `route_after_agent` |
| `route_after_agent` | ROUTING | `messages[-1]` | 无 | 否 | 否 | `reflect` 或 `tools` 或 `call_agent_model` |
| `tools` | TOOL | AIMessage tool calls、注入 State/config | `messages` 中 ToolMessage | `scrape_website` 内部会调用模型摘要网页 | `search` 调 Tavily；`scrape_website` 调 aiohttp | `call_agent_model` |
| `reflect` | MODEL | `topic`、`extraction_schema`、`messages`、`info` | `messages`，满意时也写回 `info` | 是，`with_structured_output(...).ainvoke()` | 否 | `route_after_checker` |
| `route_after_checker` | ROUTING | `loop_step`、`info`、最后 ToolMessage status、config | 无 | 否 | 否 | `call_agent_model` 或 END |

边和条件边证据：添加节点和边见 `src/enrichment_agent/graph.py:L220-L226`。最大循环限制来自 `Configuration.max_loops` 默认 6（`src/enrichment_agent/configuration.py:L47-L52`）并在 `route_after_checker` 判断（`src/enrichment_agent/graph.py:L197-L213`）。`max_info_tool_calls` 定义存在（`src/enrichment_agent/configuration.py:L40-L45`），但源码未引用，不能形成实际限制。

无限循环风险：`tools -> call_agent_model -> tools` 这条路径不会经过 `route_after_checker` 的 `max_loops` 结束判断（`src/enrichment_agent/graph.py:L223-L226`）。虽然 `call_agent_model` 每次会增加 `loop_step`（`src/enrichment_agent/graph.py:L77-L82`），但工具循环不检查该值；如果模型一直选择 search/scrape 而不提交 `Info`，项目源码没有显式工具调用上限。

## 8. 模型调用

| 调用位置 | 模型职责 | 输入 | 输出 | Tool/Schema | 校验 | 风险 |
|---|---|---|---|---|---|---|
| `call_agent_model` | 决定下一步研究行动，或用 `Info` 提交结构化结果 | 主 prompt + 历史 messages | AIMessage；若有 `Info` tool call 则提取 `args` 为 `info` | 绑定 `scrape_website`、`search`、动态 `Info`，`tool_choice="any"` | 仅检查是否有 tool_calls；无业务事实校验 | 搜索词、工具选择、最终字段值均可幻觉 |
| `scrape_website` | 将网页 HTML/文本截断内容总结成与 schema 相关 notes | URL 页面内容前 40000 字符 + schema | 字符串摘要 | 无工具绑定 | 无来源引用/事实校验 | 模型可能误读网页、遗漏或编造摘要 |
| `reflect` | 判断 `info` 是否满意完整 | 主 prompt + 历史 messages + presumed_info | `InfoIsSatisfactory` Pydantic 结构 | `with_structured_output(InfoIsSatisfactory)` | 只保证 checker 输出结构 | 自我检查可能放过错误或不完整结果 |

默认模型：代码默认 `anthropic/claude-haiku-4-5-20251001`（`src/enrichment_agent/configuration.py:L17-L18`）。README 的可见 setup 默认仍写 `anthropic/claude-3-5-sonnet-20240620`（`README.md:L42-L46`，`README.md:L173-L176`），存在文档与代码不一致。

模型初始化通过 `init_chat_model(model, model_provider=provider)` 完成（`src/enrichment_agent/utils.py:L25-L34`）。源码未见显式 timeout、retry、token 统计、成本记录或原始响应持久化。原始 AIMessage 会进入 `messages`（`src/enrichment_agent/graph.py:L72-L79`），工具结果也进入 `messages`。

完全依赖模型的结论包括：搜索 query 是否充分、网页摘要、最终 `Info` 字段值、Reflection 满意度。格式正确但仍可能业务错误的输出包括：符合 schema 的公司列表、市场份额、创始人、URL、未来展望等。

## 9. Tool Calling

| 工具 | 定义位置 | 输入 Schema | 输出格式 | 外部网络 | 副作用 | API Key | 选择方式 | 异常/限制 |
|---|---|---|---|---|---|---|---|---|
| `search` | `src/enrichment_agent/tools.py:L23-L34` | 函数参数 `query: str` | `Optional[list[dict[str, Any]]]` | 是，Tavily | 无写入副作用 | 需要 `TAVILY_API_KEY` | 模型通过 tool calling 选择 | 无本地 try/except；结果数用 `max_search_results` |
| `scrape_website` | `src/enrichment_agent/tools.py:L52-L74` | `url: str`，注入 `state` 和 `config` | `str` 摘要 | 是，aiohttp GET + LLM | 无写入副作用 | 依赖所选模型 key | 模型通过 tool calling 选择 | 无本地 try/except、timeout、URL allowlist |
| `Info` | `src/enrichment_agent/graph.py:L37-L42` | 用户 `extraction_schema` | tool call `args` dict | 否 | 写入 `state.info` | 依赖所选模型 key | 模型选择提交最终结果 | 无本地 JSON Schema 校验；`max_info_tool_calls` 未使用 |

Tavily 调用链：

```text
call_agent_model
-> 模型生成 search tool call
-> ToolNode 执行 search
-> TavilySearch.ainvoke({"query": query})
-> ToolMessage 写回 State.messages
-> call_agent_model 继续处理
```

该项目具有联网搜索增强能力，但不具备经典知识库 RAG 流程。未发现本地知识库、Embedding、向量索引、Top-K 检索、Metadata Filter 或文档入库流程；依赖中也只有 `langchain-tavily`、模型包和 LangGraph/LangChain（`pyproject.toml:L11-L19`）。

## 10. Structured Output

用户的 `extraction_schema` 被包装成名为 `Info` 的动态工具 schema（`src/enrichment_agent/graph.py:L37-L42`）。模型通过 `bind_tools([scrape_website, search, info_tool], tool_choice="any")` 获取这个 schema（`src/enrichment_agent/graph.py:L52-L55`）。当模型调用 `Info` 时，代码取第一个 `Info` tool call 的 `args` 作为 `info`（`src/enrichment_agent/graph.py:L60-L71`）。

最终结构化结果不是由 Pydantic model 校验生成，而是模型按照动态 tool schema 生成 tool args。源码没有调用 `jsonschema.validate()` 或类似确定性校验。因此：

| 维度 | 当前处理 |
|---|---|
| 格式合法 | 主要依赖模型供应商工具调用 schema 支持；项目自身未做 JSON Schema 校验 |
| 事实准确 | 未确定性保证；依赖 Tavily/网页内容和模型理解 |
| 来源真实 | 未要求结构化来源字段，也未校验 URL 引用 |
| 信息完整 | 依赖 Reflection 模型判断，不是证明 |

最终输出通过 `OutputState.info` 暴露给调用方（`src/enrichment_agent/state.py:L75-L87`）。

## 11. Reflection

Reflection Node 是 `reflect()`（`src/enrichment_agent/graph.py:L101-L160`）。它读取 `topic`、`extraction_schema`、`messages` 和 `info`，构造 checker prompt，把 `presumed_info` 发给同一配置模型，并用 `with_structured_output(InfoIsSatisfactory)` 得到 `reason`、`is_satisfactory`、`improvement_instructions`（`src/enrichment_agent/graph.py:L114-L135`）。

如果满意且存在 `info`，Reflection 写入 `ToolMessage(status="success")`；否则写入 `ToolMessage(status="error")` 并附带改进建议（`src/enrichment_agent/graph.py:L136-L160`）。路由器在未达到 `max_loops` 且状态为 error 时继续循环，否则结束；达到 `max_loops` 后直接 END（`src/enrichment_agent/graph.py:L197-L213`）。

模型自我检查不是确定性正确性证明。当前 Reflection 能帮助模型发现明显缺项、鼓励继续搜索或访问 URL，但不能证明网页真实、引用真实、事实准确、来源覆盖充分，也可能错误地认为结果“已经足够好”。

## 12. 测试

| 测试文件 | 被测对象 | 使用真实模型 | 使用真实 Tavily | 验证内容 | 未覆盖风险 |
|---|---|---|---|---|---|
| `tests/unit_tests/test_configuration.py` | `Configuration.from_runnable_config()` | 否 | 否 | 从空 config 构造不报错 | 不验证字段默认值、范围、README 一致性 |
| `tests/integration_tests/test_graph.py` | `graph.ainvoke()` 端到端 | 是 | 是 | `info` 非空、LangChain founder 包含 harrison；芯片列表含 5 个 providers 和 NVIDIA | 依赖外部模型/搜索；不证明来源、事实准确或幻觉防护 |
| `tests/conftest.py` | anyio backend | 否 | 否 | pytest async backend 为 asyncio | 无业务覆盖 |

CI 单测会安装依赖、跑 ruff、mypy、unit pytest（`.github/workflows/unit-tests.yml:L34-L60`）。集成测试需要真实 API key（`.github/workflows/integration-tests.yml:L39-L46`）。

覆盖结论：

| 问题 | 当前是否覆盖 |
|---|---|
| Graph 路由 | 集成测试间接覆盖成功路径；无显式路由单测 |
| 工具调用 | 集成测试可能真实调用；无 mock/断言 ToolMessage |
| 循环终止 | 无专门测试 |
| Structured Output | 只断言部分字段存在和类型 |
| 无效输入 | 无 |
| API 错误 | 无 |
| 模型幻觉 | 无 |
| 来源正确 | 无 |
| 事实准确 | 仅少量弱断言 |
| 成本或最大调用次数 | 无 |

本次实际执行：`uv run --no-sync python -m pytest tests/unit_tests -q`，结果 `1 passed in 0.30s`。未运行集成测试，因为它会触发真实模型和 Tavily 调用，违反本次禁止真实 LLM 调用和 Tavily 调用的约束。

## 13. 风险

| 风险 ID | 说谎或失败位置 | 原因 | 当前防护 | 防护是否充分 | 新项目启示 |
|---|---|---|---|---|---|
| R1 | Tavily 搜索结果 | 搜索结果可能错误、过时或摘要偏差 | 无确定性校验 | 不充分 | TikTok 项目要记录来源时间和可复核原文 |
| R2 | Tavily 摘要与网页 | Tavily 返回可能不是完整网页事实 | 可再 scrape URL | 不充分 | 不把搜索摘要当事实终点 |
| R3 | `scrape_website` 摘要 | LLM 总结网页可能误读或漏读 | 截取前 40000 字符 | 不充分 | 关键事实需结构化抽取和引用定位 |
| R4 | `Info` 最终结果 | 模型可写入未检索信息 | Reflection | 不充分 | 必须有事实到来源的映射 |
| R5 | 引用 | Schema 不要求引用，模型可能生成不存在引用 | 无 | 不充分 | SourceUsage 应独立建模和校验 |
| R6 | 多来源合并 | 模型可能混淆多个公司/网页 | 历史 messages | 不充分 | 事实粒度应可追踪 |
| R7 | 完整性 | 模型可能认为已完整 | Reflection | 不充分 | 完整性规则要由代码/eval 补充 |
| R8 | Reflection | checker 仍是模型 | `InfoIsSatisfactory` 格式约束 | 不充分 | 自检只能做启发式质量门 |
| R9 | Structured Output | 格式合法不代表事实正确 | 动态 tool schema | 不充分 | 区分 schema validation 与 factual validation |
| R10 | `max_loops` 上限 | 达到上限后直接 END，可能输出不完整 | 上限防无限循环 | 部分充分 | 结束态需暴露 incomplete/error |
| R11 | 默认模型 | README 和代码默认不一致 | 无自动检查 | 不充分 | 配置默认要单源化并测试 |
| R12 | API 异常 | Tavily/aiohttp/model 无本地 try/except | 依赖框架异常传播 | 不充分 | 新项目需定义错误状态和 retry 策略 |
| R13 | 工具循环 | `tools -> call_agent_model` 不经过 `max_loops` 路由 | 无 | 不充分 | 所有循环边都应受统一预算限制 |
| R14 | 未使用配置 | `max_info_tool_calls` 定义但未引用 | 无 | 不充分 | 配置必须有测试证明生效 |

## 14. 六个 AI 产品经理问题

### 1. 数据从哪里进来

用户输入：`topic`、`extraction_schema`、可选初始 `info`（`src/enrichment_agent/state.py:L15-L27`）。配置：`model`、`prompt`、`max_search_results`、`max_info_tool_calls`、`max_loops` 从 `RunnableConfig` configurable 合并默认值（`src/enrichment_agent/configuration.py:L13-L62`）。环境变量：`langgraph.json` 指定 `.env`（`langgraph.json:L7`），示例包括 `TAVILY_API_KEY`、`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`FIREWORKS_API_KEY`（`.env.example:L1-L11`）。外部数据来自 Tavily 搜索和 aiohttp 抓取网页（`src/enrichment_agent/tools.py:L23-L74`）。模型输出进入 `messages`、`info` 和 Reflection ToolMessage（`src/enrichment_agent/graph.py:L72-L82`，`src/enrichment_agent/graph.py:L136-L160`）。

### 2. 中间经过了哪些转换

`extraction_schema` 被序列化进 prompt，同时作为动态 `Info` 工具参数 schema；模型返回 AIMessage tool call；`ToolNode` 执行搜索/抓取并把结果写成 ToolMessage；模型读取 ToolMessage 继续；模型调用 `Info` 后 args 写入 `state.info`；Reflection 模型把 `info` 转成 `InfoIsSatisfactory` 判断；路由器根据 ToolMessage status 和 `loop_step` 决定继续或结束。

### 3. 哪一步由模型完成

模型完成：主 Agent 决策和最终 Info 生成（`call_agent_model`）、网页内容摘要（`scrape_website` 内部 `raw_model.ainvoke`）、Reflection 满意度判断（`reflect`）。

### 4. 哪一步必须由确定性代码完成

当前由代码保证：Graph 节点连接、配置字段筛选、消息 reducer、工具函数调用、`max_loops` 在 Reflection 后的路由判断。应该由代码保证但目前不足：JSON Schema 预校验、事实-来源绑定、URL/来源校验、工具调用预算、错误状态、成本记录、最终结果完整性规则。

### 5. 系统可能在哪里说谎

主要位置是搜索结果、网页摘要、最终 `Info`、引用/来源归因、Reflection 判断和达到循环上限后的不完整输出。详见本报告“风险”表 R1-R14。

### 6. 如何证明它做对了

当前项目已有的证明：单测证明 `Configuration.from_runnable_config()` 可运行；集成测试在真实外部服务上做少量端到端断言；本次 import 检查证明 Graph 可加载。

当前项目没有的证明：没有证明来源真实、事实准确、引用存在、所有 schema 字段完整、工具调用受控、错误路径清晰、成本受限。

新项目必须补充的证明：确定性 schema validation、fixture 化工具结果、事实到 source span 的校验、Human Gate 状态、run trace、eval 数据集、失败/重试/预算单测。

## 15. 审计限制

本次未调用 Tavily，未发起真实 LLM 调用，未读取 `.env` 内容，未运行集成测试，未安装或同步依赖。Notebook 只通过文本搜索确认调用入口，未执行。结论基于静态源码、配置、测试文件和允许的单元测试/import 检查。

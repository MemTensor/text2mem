<div align="center">

# Text2Mem · Structured Memory Engine / 结构化记忆引擎

**IR Schema → Validation → Strongly-Typed Execution → Storage / Retrieval / Reasoning → Unified Result**  
**IR 架构 → 校验 → 强类型执行 → 存储 / 检索 / 推理 → 统一结果**

</div>

---

## Contents · 目录

- [Why Text2Mem · 为什么需要 Text2Mem](#why-text2mem--为什么需要-text2mem)
- [Core Capabilities · 核心能力](#core-capabilities--核心能力)
- [Architecture · 架构概览](#architecture--架构概览)
- [Quick Start · 快速开始](#quick-start--快速开始)
- [CLI Guide · 命令行指南](#cli-guide--命令行指南)
- [IR Semantics · IR 操作语义](#ir-semantics--ir-操作语义)
- [Example Workflows · 示例工作流](#example-workflows--示例工作流)
- [Testing · 测试](#testing--测试)
- [Roadmap · 发展路线](#roadmap--发展路线)
- [Contributing · 参与共建](#contributing--参与共建)

---

## Why Text2Mem · 为什么需要 Text2Mem

**EN**  
Modern agents and assistants struggle with long-term memory: operations are ad-hoc, data evolution lacks a stable intermediate form, and model invocations are tightly coupled to storage. Text2Mem addresses these issues with a single IR (Intermediate Representation) that captures thirteen memory operations end-to-end, from schema to execution. Use it as a prototyping sandbox, a drop-in memory core, or a teaching reference for structured agent memory.

**中文**  
在构建个人 / 团队知识库、Agent 长期记忆层时，常见痛点是：操作语义碎片化、数据演化缺乏中间表示、模型调用与存储耦合。Text2Mem 提供一套统一的 IR，覆盖十三种记忆操作，并贯通“规范 → 校验 → 执行 → 结果”。可以作为记忆层原型、生产内核或教学范例。

---

## Core Capabilities · 核心能力

| Dimension (EN) | 能力维度 (ZH) | Highlights |
| -------------- | ------------- | ---------- |
| IR Abstraction | IR 抽象 | Encode / Retrieve / Summarize / Label / Update / Merge / Split / Promote / Demote / Lock / Expire / Delete / Clarify (reserved) |
| Storage Layer | 数据层 | SQLite 原型，统一字段、软删除、聚合统计 |
| Model Layer | 模型层 | Embedding + Generation 双通道，可在 Mock / Ollama / OpenAI 之间切换 |
| Validation | 校验 | JSON Schema + Pydantic v2 双重保障（结构 + 语义） |
| CLI Tooling | 命令行 | 单条 IR、Demo、Workflow、REPL、Session，多模式输出 |
| Extensibility | 可扩展 | 适配器 / 模型服务接口 / IR Args 映射 / dry-run SQL 观察 |

Additional split of Provider vs Service (v0.2): providers implement raw model calls (mock, Ollama, OpenAI), while services orchestrate higher-level capabilities like encode, semantic search, summarize, label, split, etc. See `text2mem.services.service_factory.create_models_service` for entry points.  
Provider 与 Service 职责分离（v0.2）：Provider 实现模型接口（mock / Ollama / OpenAI），Service 负责编排 encode、语义检索、摘要、打标签、拆分等能力，入口在 `text2mem.services.service_factory.create_models_service`。

---

## Architecture · 架构概览

```
Text2Mem/
├─ manage.py                # Unified CLI entry / 命令入口
├─ text2mem/
│  ├─ core/
│  │  ├─ engine.py          # Text2MemEngine: compose schema + adapter + service
│  │  └─ models.py          # Strongly-typed IR & Args (Pydantic)
│  ├─ adapters/
│  │  ├─ base.py            # Adapter protocol / 适配器协议
│  │  └─ sqlite_adapter.py  # SQLite reference implementation
│  ├─ services/             # Model orchestration / 模型服务
│  ├─ schema/               # text2mem-ir-v1.json (JSON Schema)
│  └─ validate.py           # JSON Schema utilities
├─ scripts/                 # CLI helpers & demos / 命令辅助脚本
├─ examples/                # Sample IRs & workflows / 示例
├─ tests/                   # Unit tests / 单元测试
└─ README.md
```

**Engine (`core/engine.py`)**  
- EN: Loads schema → optional validation → Pydantic parsing → adapter execution → wraps `ExecutionResult`.  
- 中文：负责载入 Schema，可选校验，解析 IR 并调用适配器执行，返回 `ExecutionResult`。

**Models (`core/models.py`)**  
- EN: Defines IR structure, per-op args with mutual exclusions, and typed parsing.  
- 中文：定义 IR 结构与各操作参数的互斥 / 必填校验，并提供强类型解析能力。

**Adapters**  
- EN: `BaseAdapter.execute(IR) -> ExecutionResult`; SQLite adapter implements 12/13 ops, plus dry-run and semantic search.  
- 中文：`BaseAdapter.execute(IR)` 返回执行结果；SQLite 适配器实现 12/13 操作，支持 dry-run 与语义检索。

**Services**  
- EN: Abstract embedding, generation, semantic search, label suggestion. Switch providers via factory.  
- 中文：封装嵌入、生成、语义检索、标签建议等能力，通过工厂快速切换 Provider。

---

## Quick Start · 快速开始

### 1. Create Environment · 创建环境

```bash
conda env create -f environment.yml
conda activate text2mem
```

Or install directly · 或直接安装：

```bash
pip install -e .
# Optional providers / 可选模型依赖
pip install openai>=1.6.0
```

### 2. Configure Model Providers · 配置模型服务

**Quick Setup · 快速配置**:

```bash
# Copy configuration template
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor

# Verify configuration
python scripts/check_env.py
```

**Mock (default development) · Mock（默认开发）**:

```bash
python manage.py demo --mode mock
```

**Ollama** (recommended, free + high quality · 推荐，免费且高质量):

Edit `.env`:
```bash
TEXT2MEM_EMBEDDING_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_PROVIDER=ollama
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
OLLAMA_BASE_URL=http://localhost:11434
```

**OpenAI** (highest quality · 最高质量):

Edit `.env`:
```bash
OPENAI_API_KEY=sk-xxx
TEXT2MEM_EMBEDDING_PROVIDER=openai
TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
TEXT2MEM_GENERATION_PROVIDER=openai
TEXT2MEM_GENERATION_MODEL=gpt-3.5-turbo
OPENAI_API_BASE=https://api.openai.com/v1  # optional
```

For more configuration options, see [Environment Configuration Guide](docs/ENVIRONMENT_CONFIGURATION.md).  
更多配置选项，请参阅 [环境配置指南](docs/ENVIRONMENT_CONFIGURATION.md)。

**Programmatic factory usage · 代码直接选择 Provider**：

```python
from text2mem.services.service_factory import create_models_service
service = create_models_service(mode="auto")  # mock / ollama / openai / auto
```

### 3. Minimal Example · 最小示例

```python
from text2mem.services.service_factory import create_models_service
from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.core.engine import Text2MemEngine

service = create_models_service(mode="auto")
adapter = SQLiteAdapter("./text2mem.db", models_service=service)
engine = Text2MemEngine(adapter=adapter, models_service=service)

res = engine.execute({
    "stage": "ENC",
    "op": "Encode",
    "args": {"payload": {"text": "hello text2mem"}}
})
print(res.success, res.data)
```

---

## CLI Guide · 命令行指南

Run `python manage.py` for full help.  
执行 `python manage.py` 查看完整帮助。

| Category · 类别 | Command · 命令 | Description · 说明 | Example · 示例 |
|----------------|----------------|-------------------|----------------|
| Environment | `status` | Check dependencies & provider readiness / 检测依赖与模型状态 | `python manage.py status` |
| Environment | `models-info` | Show current provider config / 查看当前模型配置 | `python manage.py models-info` |
| Config | `set-env KEY VALUE` | Update `.env` entries / 更新环境变量 | `python manage.py set-env TEXT2MEM_EMBEDDING_MODEL nomic-embed-text` |
| Demo | `demo` | Run light/full demo / 运行轻量或全量演示 | `python manage.py demo --full --mode mock` |
| Shortcut | `features` | Encode→Retrieve→Summarize pipeline / 快链示例 | `python manage.py features --mode mock` |
| Single IR | `ir` | Execute inline JSON / 执行单条 IR | `python manage.py ir --inline '{"stage":"RET","op":"Retrieve","args":{"include":["text"]}}'` |
| Workflow | `workflow` | Execute workflow file / 执行工作流文件 | `python manage.py workflow examples/real_world_scenarios/workflow_sales_qbr.json` |
| Workflow | `list-workflows` | List bundled workflows / 列出内置示例 | `python manage.py list-workflows` |
| Interactive | `repl` | Lightweight command loop / 交互式命令行 |
| Session | `session` | Scripted execution, DB switch, output modes / 脚本执行、切库、输出模式 |
| Validation | `models-smoke` | Minimal embed + generate sanity check / 最小模型连通性 |
| Testing | `test` | Run pytest suite / 运行测试 |

### Demo / Session Tips · Demo 与 Session 提示

- `demo --perf --json` collects latency stats and full JSON output.  
  使用 `demo --perf --json` 可收集耗时统计与完整输出。
- `session` supports inline commands (`next`, `run`) and raw IR JSON pasting.  
  `session` 支持逐条执行、批量运行与直接粘贴 IR。
- `meta.dry_run=true` reveals SQL for supported operations.  
  设置 `meta.dry_run=true` 可以查看部分操作的 SQL 计划。

---

## IR Semantics · IR 操作语义

| Operation | 场景意图 | Key Args 关键字段 | Notes 说明 |
|-----------|----------|-------------------|-----------|
| Encode | Write new memory / 写入记忆 | `payload(text|url|structured)` | Supports skip embedding, facets, permissions |
| Label | Add tags/facets / 标签补充 | `tags`, `facets`, `mode` | `mode` = add / replace / remove |
| Update | Modify fields / 修改字段 | `set.{...}` | Enforces non-empty set |
| Merge | Merge entries / 合并 | `strategy`, `primary_id` | Optional re-embedding |
| Split | Break content / 拆分 | `strategy`, `params` | Sentence/chunk/custom |
| Promote | Raise importance / 提升权重 | `weight`, `weight_delta`, `remind` | Reminder uses RFC5545 RRULE |
| Demote | Lower importance / 降权归档 | `archive`, `weight`, `weight_delta`, `reason` | Weight range [0,1] |
| Lock | Protect entries / 保护 | `mode`, `policy` | Allow/deny operations, reviewers, expiry |
| Expire | Lifecycle / 生命周期 | `ttl`, `until`, `on_expire` | Supports soft/hard delete, demote |
| Delete | Remove entries / 删除 | `older_than`, `time_range`, `soft` | Confirmation required for wide ops |
| Retrieve | Semantic search / 语义检索 | `intent(query|vector|context)`, `overrides` | Requires `limit` when targeting STO stage |
| Summarize | Generate summary / 摘要 | `focus`, `max_tokens` | Tied to generation provider |
| Clarify (reserved) | Follow-up questions / 澄清 | TBD | 预留扩展 |

Stage conventions · 阶段约束：
- ENC → Encode (write-after-read allowed for prototyping)  
  ENC 阶段主要负责写入（原型阶段允许写后即读）。
- STO → Mutations (Label, Update, Merge, Split, Promote, Demote, Lock, Expire, Delete)  
  STO 阶段包含所有写入 / 变更操作。
- RET → Retrieve, Summarize (and optional Encode for test loops)  
  RET 阶段负责检索与摘要。

---

## Example Workflows · 示例工作流

- `examples/op_workflows/` — single-operation playbooks with rich comments.  
  单操作工作流示例，涵盖 encode / label / retrieve 等典型场景。
- `examples/real_world_scenarios/` — multi-step scenarios grounded in sales, SRE, and executive workflows (`workflow_sales_qbr.json`, `workflow_incident_postmortem.json`, `workflow_investor_update.json`).  
  真实业务场景工作流，涵盖销售 QBR、故障复盘、投资人更新。
- `examples/ir_operations/` — atomic IR samples validated by schema tests.  
  单条 IR 示例，全部通过 JSON Schema 校验。

Use `python manage.py workflow <file>` to run any scenario end-to-end.  
通过 `python manage.py workflow <文件路径>` 串行执行工作流。

---

## Testing · 测试

**EN**  
Run the full pytest suite (schema validation, engine behaviour, adapter logic, service contracts):

```bash
python manage.py test
```

**中文**  
使用 `python manage.py test` 运行完整测试，覆盖 Schema 校验、引擎执行、适配器逻辑与服务协议。

---

## Roadmap · 发展路线

- [ ] Generate grouped `.env` templates & missing-entry hints / 配置命令输出分组 `.env` 与缺失项提示
- [ ] Implement Clarify end-to-end & extend demos / 完成 Clarify 全链路并纳入 Demo
- [ ] Session enhancements: batch JSON, variable injection, range execution / Session 支持批量 JSON、变量注入、区间执行
- [ ] Full dry-run coverage across write operations / 覆盖所有写操作的 dry-run
- [ ] HTTP / gRPC service wrappers (FastAPI / gRPC proto) / 提供 HTTP / gRPC 服务封装
- [ ] External vector stores & long-form support (Faiss / Chroma / pgvector) / 接入向量库与长文本支持
- [ ] Additional storage adapters (Postgres, cloud KV) / 拓展更多存储适配器

---

## Contributing · 参与共建

**EN**  
Issues and pull requests are welcome. Please include reproducible steps or sample IRs when reporting bugs. Schema and workflow contributions should pass `python manage.py test` to ensure compliance.

**中文**  
欢迎提交 Issue 和 PR！报告问题时附上可复现步骤或样例 IR；贡献 Schema 或工作流时，请务必通过 `python manage.py test`，以确保兼容性与稳定性。

---

**Feedback & Collaboration · 反馈与合作**  
Feel free to reach out with ideas, integrations, or real-world scenarios. 一起建设轻量、可信赖的记忆 IR 生态。

<div align="center">

<h1>Text2Mem · 结构化记忆 IR 执行与检索引擎</h1>

<b>IR Schema v1 → 校验 → 强类型解析 → 存储/检索/模型推理 → 统一结果</b>

</div>

---

## 新增：Provider vs Service 职责划分（v0.2）

- Provider（提供者）只负责“模型接口实现”：EmbeddingModel / GenerationModel（如 Mock、Ollama、OpenAI）。
- Service 负责“编排与能力复用”：统一封装 encode/semantic_search/summarize/label/split 等高阶能力。
- 工厂入口：通过 `text2mem.services.service_factory.create_models_service` 选择 provider 并组装 `ModelsService`。

最简代码示例：

```python
from text2mem.services.service_factory import create_models_service
from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.core.engine import Text2MemEngine

# 根据环境变量/参数自动选择 mock/ollama/openai
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

注意：兼容入口 `text2mem.services.models_service_mock.create_models_service` 仍然可用，但推荐使用 `service_factory`。

---

## 0. 为什么存在？
在构建个人/团队知识库、AI 记忆层或 Agent 长期上下文时，容易出现：操作语义碎片化、数据演化缺乏中间表示、模型调用和存储耦合。Text2Mem 通过一套 IR（Intermediate Representation）抽象 13 类记忆操作，打通：规范 → 校验 → 执行 → 结果，可作为：

- 原型：快速验证“记忆层”设计合理性
- 内核：嵌入到更大 Agent/Workflow 系统
- 教学：演示如何用 IR 统一操作域

---

## 1. 总览特性

| 维度 | 能力 |
|------|------|
| IR 抽象 | Encode / Retrieve / Summarize / Label / Update / Merge / Split / Promote / Demote / Lock / Expire / Delete / Clarify(预留) |
| 数据层 | SQLite 原型（统一字段 + 软删除 + 聚合统计）|
| 模型层 | Embedding + Generation 双通道，可 mock / Ollama / OpenAI 切换 |
| 校验 | JSON Schema + Pydantic v2 双重保证（结构 + 语义）|
| CLI | 单条 IR / Demo / Workflow / REPL / Session（脚本步进 + JSON 粘贴 + 动态切库）|
| 输出 | brief / full JSON；demo 汇总性能与操作序列 |
| 可扩展 | 适配器接口 / 模型服务接口 / IR Args 映射 / dry_run SQL 观察 |

---

## 2. 目录与核心组件

```
Text2Mem/
├─ manage.py                # 统一命令入口
├─ text2mem/
│  ├─ core/
│  │  ├─ engine.py          # Text2MemEngine：装配 schema + adapter + models_service
│  │  └─ models.py          # IR & Args 强类型模型 (Pydantic)
│  ├─ adapters/
│  │  ├─ base.py            # BaseAdapter / ExecutionResult 协议
│  │  └─ sqlite_adapter.py  # 全量 IR 操作原型实现
│  ├─ services/             # 模型服务抽象（embedding / generation / 语义检索）
│  ├─ schema/               # text2mem-ir-v1.json
│  └─ validate.py           # JSON Schema 校验封装
├─ scripts/                 # CLI 复用：demo 运行 / env 生成 / 分组配置
├─ examples/                # sample_ir_* / workflow_* 示例
├─ tests/                   # 单元 + 适配器 + 引擎 + 模型校验
└─ README.md
```

### 2.1 引擎 (core/engine.py)
职责：
- 载入 schema → 可选 schema 校验
- IR → Pydantic → adapter.execute
- 包装结果 ExecutionResult

### 2.2 模型 (core/models.py)
- IR(stage, op, target, args, meta)
- 各操作 Args 互斥/必选验证（TimeRange XOR, EncodePayload one-of, Promote 互斥等）
- `IR.parse_args_typed()` 映射操作 → 对应 Args 类型

### 2.3 适配器 (adapters)
- `BaseAdapter.execute(IR) -> ExecutionResult`
- SQLiteAdapter：实现 12/13 操作（Clarify 预留）+ dry_run + 语义检索（向量维度过滤）
- 附带辅助：统计 / dump / optimize / db_info

### 2.4 模型服务 (services)
- 抽象 encode / summarize / semantic_search / suggest_labels 等
- 可创建 mock (无依赖)、ollama、本地 openai

### 2.5 CLI 设计
- manage.py：命令分组 + usage 分层 + session 扩展状态（output mode / current db / script ptr）
- demo：收集每步耗时，支持 json 汇总

---

## 3. 安装与环境

### 3.1 Conda 推荐
```bash
conda env create -f environment.yml
conda activate text2mem
```

### 3.2 直接安装
```bash
pip install -e .
# 可选：云端模型
pip install openai>=1.6.0
```

### 3.3 模型服务配置
Mock（默认开发）：
```bash
python manage.py demo --mode mock
```

Ollama `.env` 示例：
```
TEXT2MEM_EMBEDDING_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_PROVIDER=ollama
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
```

OpenAI：
```bash
export OPENAI_API_KEY=sk-xxx
export TEXT2MEM_EMBEDDING_PROVIDER=openai
export TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
export TEXT2MEM_GENERATION_PROVIDER=openai
export TEXT2MEM_GENERATION_MODEL=gpt-3.5-turbo
```

编程方式（不依赖 CLI）选择模型服务：

```python
from text2mem.services.service_factory import create_models_service
service = create_models_service(mode="openai")  # 或者 "ollama" / "mock" / "auto"
```

---

## 4. CLI 使用速览

查看帮助：
```bash
python manage.py
```

| 类别 | 命令 | 说明 | 常用示例 |
|------|------|------|----------|
| 环境 | status | 检测依赖/模型可用 | `python manage.py status` |
| 环境 | models-info | 当前模型配置 | `python manage.py models-info` |
| 配置 | set-env KEY VALUE | 写入/更新 .env | `python manage.py set-env TEXT2MEM_EMBEDDING_MODEL nomic-embed-text` |
| 演示 | demo | 单步/全操作跑通 | `python manage.py demo --full --mode mock --perf --json` |
| 快链 | features | Encode→Retrieve→Summarize 串联 | `python manage.py features --mode mock` |
| IR | ir | 执行单条 | `python manage.py ir --inline '{"stage":"RET","op":"Retrieve","args":{"k":2}}'` |
| 工作流 | workflow | 执行 workflow JSON | `python manage.py workflow examples/real_world_scenarios/workflow_project_management.json` |
| 工作流 | list-workflows | 列出示例 | `python manage.py list-workflows` |
| 交互 | repl | 简化命令循环 | `python manage.py repl` |
| 会话 | session | 脚本/粘贴 JSON / 切库 / 输出模式 | `python manage.py session --mode mock --output full` |
| 验证 | models-smoke | 最小 embed+generate | `python manage.py models-smoke --mode mock` |
| 测试 | test | 运行 pytest | `python manage.py test` |

### 4.1 Demo
```bash
# 轻量 3 操作示例
python manage.py demo --mode mock
# 全量 12 操作 + 性能/JSON 输出
python manage.py demo --full --mode mock --perf --json
```

### 4.2 Session 进阶
脚本内容 (script.txt)：
```
encode 记录一次产品讨论
retrieve 讨论
{"stage":"RET","op":"Retrieve","args":{"query":"产品","k":3}}
summarize 产品讨论
```
运行：
```bash
python manage.py session --mode mock --script script.txt --output brief
next   # 逐条执行
run    # 一次执行剩余
output full
switch-db ./test_session.db
```
可用子命令：list / next / run / encode / retrieve / summarize / ir / switch-db / output full|brief / history / save / quit + 直接粘贴原始 IR JSON 行

### 4.3 Dry-Run（查看 SQL）
当前 `dry_run` 通过 IR.meta.dry_run 触发（部分操作支持）：
```bash
python manage.py ir --inline '{"stage":"ENC","op":"Encode","meta":{"dry_run":true},"args":{"payload":{"text":"测试 dry"}}}'
```

---

## 5. IR 操作语义

| 操作 | 核心意图 | 关键字段片段 | 典型场景 |
|------|----------|-------------|----------|
| Encode | 写入新记忆 | payload(text/url/structured) | 采集输入 / 笔记持久化 |
| Label | 补充标签/特性 | tags / facets / auto_generate_tags | 后处理分类 |
| Update | 修改字段 | set.{...} | 修正内容、优先级 |
| Merge | 合并 | strategy / primary_id | 去重聚合 |
| Split | 拆分 | strategy / spans / inherit | 长文切片 |
| Promote | 抬升权重 | weight / weight_delta / remind | 提醒/强化记忆 |
| Demote | 降级/归档 | archive / weight / weight_delta | 过时内容降级 |
| Lock | 保护 | mode / policy | 防止误改 |
| Expire | 过期策略 | ttl / until / on_expire | 生命周期治理 |
| Delete | 删除 | soft / time_range | 清理空间 |
| Retrieve | 检索 | query / order_by / include | 向量 + 过滤搜索 |
| Summarize | 汇总 | focus / max_tokens | 上下文概要 |
| Clarify | 补充信息 | （预留） | 多轮澄清 |

阶段 (stage) 约束：
ENC: Encode
STO: Label / Update / Merge / Split / Promote / Demote / Lock / Expire / Delete
RET: Retrieve / Summarize / (Encode 允许即写即取)

---

## 6. 典型数据流
1. CLI / 调用方 传入 dict/JSON IR
2. (可选) JSON Schema validate
3. Pydantic 强类型解析 → Args 校验
4. Adapter 派发：操作 → _exec_xxx
5. 模型服务（可选）调用：embedding / LLM summarize / label suggestion / semantic_search
6. 组装 dict → ExecutionResult(success,data,error,meta)

失败处理：
- Pydantic 校验失败：抛 ValidationError（调用侧捕获）
- Adapter 内部异常：捕获并返回 ExecutionResult(success=False,error=...)

---

## 7. 扩展指南

### 7.1 新增存储适配器
```python
from text2mem.adapters.base import BaseAdapter, ExecutionResult

class MyAdapter(BaseAdapter):
	def execute(self, ir):
		# 解析 ir.op 并执行
		return ExecutionResult(success=True, data={"ok": True})
```
在引擎装配：
```python
from text2mem.core.engine import Text2MemEngine
engine = Text2MemEngine(adapter=MyAdapter())
```

### 7.2 添加 Clarify 操作（示例思路）
1. models.py 增加 ClarifyArgs + Op 枚举
2. schema 增加对应 definition
3. sqlite_adapter.py 添加 `_exec_clarify`
4. demo / session 增加命令入口

### 7.3 自定义语义检索策略
- 替换 models_service.semantic_search 实现（例如引入 Faiss / pgvector）
- Adapter `_exec_retrieve` 调用保持不变

---

## 8. 测试体系
运行：
```bash
python manage.py test
```
已覆盖：
- 模型参数校验互斥/必选
- 引擎基本执行 & 异步包装
- 适配器核心操作（Encode / Retrieve / Merge / Split / Promote / Expire / Lock / Summarize）
- 嵌入生成元信息（维度/模型/提供商推断）

建议补充（Roadmap 内测阶段）：
- Delete (soft/hard) / Demote 案例
- dry_run SQL 快照
- Retrieve include 非法字段
- Split custom_spans 异常
- Expire until 分支

---

## 9. 性能与注意事项
- SQLite 原型未加向量索引，语义检索 O(n)；规模放大需外置向量库
- embedding 维度不匹配会被跳过（返回 note）
- dry_run 模式仅部分操作支持（逐步补齐）

---

## 10. FAQ
Q: 为什么 Encode 可以在 RET 阶段？
A: 便于“写后立即检索”链路测试，原型允许放宽；生产可强制 ENC。

Q: Clarify 何时加入？
A: 模型提示模板稳定后；当前保留结构位置。

Q: 能否批量 IR？
A: Session 可逐行；后续计划支持 JSON 数组批量。

Q: 如何避免全表操作风险？
A: 可在 adapter `_where_from_target` 增加 require_target 防护（Roadmap）。

---

## 11. Roadmap
- [ ] config 命令生成分组 .env + 缺失项提示
- [ ] Clarify 全链路实现 + Demo 纳入
- [ ] session 支持批量 JSON / 变量替换 / run 区间
- [ ] dry_run 覆盖全部写操作
- [ ] HTTP / gRPC 服务封装（FastAPI / gRPC proto）
- [ ] 外部向量/长文本扩展（Faiss / Chroma / pgvector）
- [ ] 多存储适配（Postgres / 云 KV）

---

## 12. 变更日志
详见 `docs/CHANGELOG.md`

---

欢迎反馈与 PR，共建轻量记忆 IR 生态。

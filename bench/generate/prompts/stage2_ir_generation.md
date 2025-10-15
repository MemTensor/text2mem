# Stage 2 · IR Schema 生成

## 🎯 任务目标

将 Stage 1 自然语言样本转换为 **Text2Mem IR Schema（中间表示）**。

**核心要点：**

1. ✅ 准确映射 NL 指令 → IR 操作
2. ✅ 生成完整 `prerequisites` （IR 数组 ≠ 描述）
3. ✅ 多样化 `target` （优先 search / filter）
4. ✅ 支持 workflow （2–5 步 逻辑链）
5. ✅ 时间一致性 （固定虚拟时间）
6. ✅ 知识提取 （信息 → 知识单元）

---

## 🧠 记忆提取标准（必遵循）

### Level 1 原子化拆分（必须）

* 混合信息 → 多条 `ENC.Encode`，每条仅含 1 个独立记忆点。
* ❌ 错误：一次存整段   ✅ 正确：多条 Encode 分别打标签，但是多条记忆需要相互独立。

### Level 2 类型标注（推荐）

* `args.payload` 字段中加入：

  * `knowledge_type`: `"fact"|"constraint"|"requirement"|"decision"|"action"|"risk"|"metric"|"question"`
  * `source`: 信息来源（人/文档/会议）
  * `context`: 简短上下文说明
* `args.type` 固定 `"knowledge"` （区分 `"note"`）

### Level 3 元数据提取（推荐）

* 结构化字段放入 `facets` 以支持过滤。
  示例：

  ```json
  {"amount":2000000,"currency":"CNY"}
  {"duration_months":2}
  {"window":{"start":"2025-11-01","end":"2025-11-11"}}
  {"certainty":"confirmed"}
  ```

---

## ⏰ 时间规则（固定虚拟时间）

* 虚拟“现在”：`2025-10-21T00:00:00Z`
* 相对时间（含起不含止）：

| 表达          | 时间范围                     |
| ----------- | ------------------------ |
| 昨天          | [2025-10-20, 2025-10-21) |
| 最近 7 天 / 上周 | [2025-10-14, 2025-10-21) |
| 最近 30 天     | [2025-09-21, 2025-10-21) |

**规则：**

* 所有 `prerequisites.args.time` 必须在查询窗口内；
* 顶层 `args.time` 用于过滤，`facets` 可保留业务时间。

### ⚠️ time_range 格式规范（重要！）

```json
// ✅ 正确：相对时间（扁平结构）
{"time_range": {"relative": "last", "amount": 7, "unit": "days"}}

// ✅ 正确：绝对时间（扁平结构）
{"time_range": {"start": "2025-10-01T00:00:00Z", "end": "2025-10-21T00:00:00Z"}}

// ❌ 错误：不要使用嵌套的 absolute 字段！
{"time_range": {"absolute": {"start": "...", "end": "..."}}}
```

**time_range 字段说明**：

| 格式 | 必需字段 | 示例 |
|------|---------|------|
| **相对时间** | `relative`, `amount`, `unit` | `{"relative": "last", "amount": 7, "unit": "days"}` |
| **绝对时间** | `start`, `end` | `{"start": "2025-10-01T00:00:00Z", "end": "2025-10-21T00:00:00Z"}` |

**⚠️ 注意**：time_range 使用**扁平结构**，字段直接在 time_range 对象中，**不要**嵌套 absolute/relative 子对象！

---

## 🧩 Prerequisites 生成规范

| 操作类型                  | 是否必需 | 数量    | 要求              |
| --------------------- | ---- | ----- | --------------- |
| Encode                | 否    | –     | 无需前置            |
| Retrieve / Summarize  | 是    | 3–5 条 | 原子化 + 类型化 + 结构化 |
| STO（Update / Label 等） | 是    | 1–3 条 | 同上              |

**补充要求**

* `tags` 精准（如“预算”“合规”“上线窗口”）
* 不同知识点可使用不同 `time`（间隔 2–5 分钟）
* 每条 Encode 含 `knowledge_type` `source` `context` `facets` 字段

---

## 🏗️ 输出格式（严格）

每个样本输出 1 个 JSON 对象：

```json
{
  "nl":{"zh":"<自然语言指令>"},
  "context":"<输入上下文>",
  "classification":{"instruction_type":"...","structure":"...","lang":"..."},
  "scenario_info":{"scenario":"...","operation":"...","style":"...","topic":"..."},
  "prerequisites":[{ "stage":"ENC","op":"Encode","args":{...} }],
  "schema_list":[{ "stage":"RET|SUM|STO|...","op":"...","target":{...},"args":{...} }]
}
```

---

## ✅ 质量检查清单

* [ ] 原子化：每条 Encode 仅 1 知识点
* [ ] 类型化：包含 `knowledge_type`
* [ ] 归属化：包含 `source`、`context`
* [ ] 结构化：关键数值/时间进入 `facets`
* [ ] 标签精准 + 可检索
* [ ] 时间在查询窗口内
* [ ] `schema_list.target.filter` 可命中 `prerequisites`
* [ ] 输出仅 JSON ，无说明、无代码块

---

## 🧾 输入占位（由上游替换）

```json
{
  "instruction":"{instruction}",
  "context":"{context}",
  "classification":{"instruction_type":"{instruction_type}","structure":"{structure}","lang":"{lang}"},
  "scenario_info":{"scenario":"{scenario}","operation":"{operation}","style":"{style}","topic":"{topic}"}
}
```

---

## 💡 示例（会议纪要 → Retrieve）

```json
[
  {
    "nl":{"zh":"查找上周关于产品设计的会议记录"},
    "context":"用户正在推进新版本设计评审",
    "classification":{"instruction_type":"direct","structure":"single","lang":"zh"},
    "scenario_info":{"scenario":"meeting_notes","operation":"retrieve","style":"concise","topic":"产品设计"},
    "prerequisites":[
      {"stage":"ENC","op":"Encode","args":{"payload":{"text":"产品设计评审会议：确认新版交互方案","knowledge_type":"fact","source":"会议纪要","context":"设计评审-第二次"},"type":"knowledge","tags":["会议","产品设计","评审"],"time":"2025-10-18T10:00:00Z","facets":{"phase":"review"}}},
      {"stage":"ENC","op":"Encode","args":{"payload":{"text":"交互改动需在10月25日前出高保真","knowledge_type":"constraint","source":"产品经理","context":"设计排期"},"type":"knowledge","tags":["会议","产品设计","期限"],"time":"2025-10-15T14:00:00Z","facets":{"deadline":"2025-10-25T00:00:00Z"}}},
      {"stage":"ENC","op":"Encode","args":{"payload":{"text":"可用性测试样本量需≥20","knowledge_type":"requirement","source":"用户研究","context":"可用性测试"},"type":"knowledge","tags":["会议","产品设计","可用性"],"time":"2025-10-14T09:30:00Z","facets":{"sample_size":20}}}
    ],
    "schema_list":[
      {"stage":"RET","op":"Retrieve","target":{"filter":{"has_tags":["会议","产品设计"],"time_range":{"relative":"last","amount":7,"unit":"days"}}}}
    ]
  }
]
```

---

## ⚙️ Structure 分类

| 类型       | 特征      | 说明                             |
| -------- | ------- | ------------------------------ |
| single   | 仅 1 个操作 | 操作 = `scenario_info.operation` |
| workflow | 2–5 个操作 | 多步逻辑链，步骤 id 互引用                |

---


# 📚 Text2Mem 12种操作快速参考（含参数说明）

---

## 🧩 ENC 阶段（创建）

### 1️⃣ Encode — 创建新记录

```json
{
  "stage": "ENC",
  "op": "Encode",
  "args": {
    "payload": {"text": "会议内容..."},
    "type": "note",
    "tags": ["会议", "产品"],
    "facets": {
      "subject": "产品讨论",
      "time": "2024-11-15T10:00:00Z"
    }
  }
}
```

| 字段                  | 类型            | 必需 | 说明                                   |
| ------------------- | ------------- | -- | ------------------------------------ |
| `stage`             | string        | ✅  | 固定为 `"ENC"`                          |
| `op`                | string        | ✅  | 固定为 `"Encode"`                       |
| `args.payload.text` | string        | ✅  | 主要文本内容（推荐使用 text，不建议使用 structured）   |
| `args.type`         | string        | ✅  | 记录类型，如 `note`、`task`、`event`         |
| `args.tags`         | array(string) | 可选 | 标签，建议 2–5 个                          |
| `args.facets`       | object        | 可选 | 结构化元数据，如 subject/time/location/topic |
| `args.source`       | string        | 可选 | 来源描述（如“会议记录”、“网页摘录”）                 |

**要点**：

* 不需要 `target`。
* 不需要 `prerequisites`。
* `payload.text` 为标准化文本（不使用 JSON 结构）。

---

## 🔍 RET 阶段（检索 / 摘要）

### 2️⃣ Retrieve — 检索记录

```json
{
  "stage": "RET",
  "op": "Retrieve",
  "target": {
    "search": {  // ⭐ 70% 使用 search
      "intent": {"query": "产品设计讨论"},
      "overrides": {"k": 10, "alpha": 0.7}
    }
  },
  "args": {"include": ["id", "text", "tags"]}
}
```

| 字段                              | 类型            | 必需 | 说明                  |
| ------------------------------- | ------------- | -- | ------------------- |
| `stage`                         | string        | ✅  | 固定为 `"RET"`         |
| `op`                            | string        | ✅  | 固定为 `"Retrieve"`    |
| `target.search.intent.query`    | string        | ✅  | 自然语言检索关键词           |
| `target.search.overrides.k`     | integer       | 可选 | 返回数量上限（默认10）        |
| `target.search.overrides.alpha` | number(0–1)   | 可选 | 混合检索比例（0=关键词, 1=语义） |
| `args.include`                  | array(string) | 可选 | 指定返回字段白名单           |

**要点**：

* Prerequisites: 3–5 条记录（2–3 相关 + 1–2 不相关）。
* 也可使用 `"target.filter"` 或 `"target.ids"`，但建议多样化。

---

### 3️⃣ Summarize — 汇总摘要

```json
{
  "stage": "RET",
  "op": "Summarize",
  "target": {
    "search": {  // ⭐ 60% 使用 search
      "intent": {"query": "会议内容"},
      "overrides": {"k": 10},
      "limit": 10
    }
  },
  "args": {
    "focus": "action items",
    "max_tokens": 200
  }
}
```

| 字段                | 类型      | 必需 | 说明                        |
| ----------------- | ------- | -- | ------------------------- |
| `stage`           | string  | ✅  | 固定为 `"RET"`               |
| `op`              | string  | ✅  | 固定为 `"Summarize"`         |
| `target`          | object  | ✅  | 目标选择，可用 search/filter/ids |
| `args.focus`      | string  | 可选 | 聚焦的摘要方向                   |
| `args.max_tokens` | integer | 可选 | 最大摘要长度（默认256）             |
| `meta.lang`       | string  | 可选 | 输出语言（`zh`/`en`）           |

**要点**：

* 需有 2–4 条可摘要记录作为 prerequisites。
* Summarize 是 RET 阶段的复合操作，可与 Retrieve 组合。

---

## ⚙️ STO 阶段（存储 / 修改）

---

### 4️⃣ Label — 打标签

```json
{
  "stage": "STO",
  "op": "Label",
  "target": {
    "filter": {  // ⭐ 50% 使用 filter
      "type": "note",
      "time_range": {"relative": "last", "amount": 7, "unit": "days"}
    }
  },
  "args": {
    "tags": ["重要"],
    "mode": "add"
  }
}
```

| 字段              | 类型            | 必需           | 说明                                   |
| --------------- | ------------- | ------------ | ------------------------------------ |
| `stage`         | string        | ✅            | 固定 `"STO"`                           |
| `op`            | string        | ✅            | `"Label"`                            |
| `target.filter` | object        | ✅            | 目标过滤条件                               |
| `args.tags`     | array(string) | ✅ (或 facets) | 要添加或替换的标签                            |
| `args.facets`   | object        | 可选           | 添加/修改的结构化元数据                         |
| `args.mode`     | string        | 可选           | 操作模式：`add`/`replace`/`remove`（默认add） |

**要点**：

* Label 是元数据修改操作。
* 支持批量标签修改。

---

### 5️⃣ Update — 更新记录

```json
{
  "stage": "STO",
  "op": "Update",
  "target": {
    "filter": {"has_tags": ["待更新"]}
  },
  "args": {
    "set": {
      "text": "更新后的内容摘要",
      "subject": "更新后主题"
    }
  }
}
```

| 字段                 | 类型            | 必需 | 说明       |
| ------------------ | ------------- | -- | -------- |
| `target`           | object        | ✅  | 指定要更新的记录 |
| `args.set.text`    | string        | 可选 | 更新后的文本   |
| `args.set.tags`    | array(string) | 可选 | 修改标签     |
| `args.set.subject` | string        | 可选 | 更新主题     |
| `args.set.weight`  | number(0–1)   | 可选 | 调整重要度    |

**要点**：

* `set` 中至少包含一个字段。
* Prerequisites 通常 1–2 条记录。

---

### 6️⃣ Promote — 提升重要度

```json
{
  "stage": "STO",
  "op": "Promote",
  "target": {"filter": {"has_tags": ["紧急"]}},
  "args": {
    "weight_delta": 0.3,
    "remind": {"rrule": "FREQ=WEEKLY;BYDAY=MO"},
    "reason": "周期性复查"
  }
}
```

| 字段                  | 类型          | 必需  | 说明       |
| ------------------- | ----------- | --- | -------- |
| `target`            | object      | ✅   | 指定要提升的记录 |
| `args.weight`       | number(0–1) | 三选一 | 绝对权重     |
| `args.weight_delta` | number      | 三选一 | 相对增量     |
| `args.remind`       | object      | 三选一 | 设置提醒规则   |
| `args.reason`       | string      | 可选  | 提升原因     |

---

### 7️⃣ Demote — 降级/归档

```json
{
  "stage": "STO",
  "op": "Demote",
  "target": {
    "filter": {"time_range": {"relative": "last", "amount": 90, "unit": "days"}}
  },
  "args": {"archive": true, "reason": "过期归档"}
}
```

| 字段                  | 类型      | 必需  | 说明     |
| ------------------- | ------- | --- | ------ |
| `target`            | object  | ✅   | 目标选择   |
| `args.archive`      | boolean | 三选一 | 归档     |
| `args.weight`       | number  | 三选一 | 绝对值降低  |
| `args.weight_delta` | number  | 三选一 | 相对减少   |
| `args.reason`       | string  | 可选  | 降级原因说明 |

---

### 8️⃣ Merge — 合并记录

```json
{
  "stage": "STO",
  "op": "Merge",
  "target": {"ids": ["2", "3"]},
  "args": {
    "strategy": "merge_into_primary",
    "primary_id": "1",
    "soft_delete_children": true
  }
}
```

| 字段                          | 类型            | 必需 | 说明                               |
| --------------------------- | ------------- | -- | -------------------------------- |
| `target.ids`                | array(string) | ✅  | 要合并的子记录                          |
| `args.strategy`             | string        | ✅  | 合并策略（当前仅支持 `merge_into_primary`） |
| `args.primary_id`           | string        | ✅  | 主记录ID                            |
| `args.soft_delete_children` | boolean       | 可选 | 是否软删除子记录（默认true）                 |

---

### 9️⃣ Split — 拆分记录

```json
{
  "stage": "STO",
  "op": "Split",
  "target": {"ids": ["1"]},
  "args": {
    "strategy": "by_chunks",
    "params": {"chunk_size": 500, "num_chunks": 3},
    "inherit_all": true
  }
}
```

| 字段                 | 类型            | 必需 | 说明                                            |
| ------------------ | ------------- | -- | --------------------------------------------- |
| `target.ids`       | array(string) | ✅  | 要拆分的记录                                        |
| `args.strategy`    | string        | ✅  | 拆分方式（`by_sentences` / `by_chunks` / `custom`） |
| `args.params`      | object        | ✅  | 各策略的参数                                        |
| `args.inherit_all` | boolean       | 可选 | 是否继承所有元数据（默认true）                             |

---

### 🔟 Delete — 删除记录

```json
{
  "stage": "STO",
  "op": "Delete",
  "target": {
    "filter": {
      "has_tags": ["temporary"],
      "time_range": {"relative": "last", "amount": 90, "unit": "days"}
    }
  },
  "args": {"soft": true}
}
```

| 字段                | 类型      | 必需 | 说明            |
| ----------------- | ------- | -- | ------------- |
| `target`          | object  | ✅  | 删除目标          |
| `args.soft`       | boolean | 可选 | 是否软删除（默认true） |
| `args.reason`     | string  | 可选 | 删除原因          |
| `args.time_range` | object  | 可选 | 时间范围筛选        |

---

### 11️⃣ Lock — 锁定记录

```json
{
  "stage": "STO",
  "op": "Lock",
  "target": {"ids": ["1"]},
  "args": {
    "mode": "read_only",
    "policy": {"expires": "2026-01-01T00:00:00Z"}
  }
}
```

| 字段                    | 类型                | 必需 | 说明                                           |
| --------------------- | ----------------- | -- | -------------------------------------------- |
| `target.ids`          | array(string)     | ✅  | 要锁定的记录                                       |
| `args.mode`           | string            | 可选 | 模式：`read_only` 或 `append_only`（默认 read_only） |
| `args.reason`         | string            | 可选 | 锁定原因说明                                       |
| `args.policy.expires` | string(date-time) | 可选 | 过期时间                                         |

---

### 12️⃣ Expire — 设置过期策略

```json
{
  "stage": "STO",
  "op": "Expire",
  "target": {"filter": {"type": "temporary"}},
  "args": {
    "ttl": "P30D",
    "on_expire": "soft_delete"
  }
}
```

| 字段               | 类型                | 必需  | 说明                                                          |
| ---------------- | ----------------- | --- | ----------------------------------------------------------- |
| `target`         | object            | ✅   | 设置目标                                                        |
| `args.ttl`       | string(duration)  | 二选一 | 相对过期时间，如 `"P30D"`                                           |
| `args.until`     | string(date-time) | 二选一 | 绝对过期时间                                                      |
| `args.on_expire` | string            | 可选  | 过期行为：`soft_delete` / `hard_delete` / `demote` / `anonymize` |

---

## 🎬 生成指南

### 处理流程

1. **识别 structure 类型**
   - 查看 `classification.structure`
   
2. **对于 single 样本**：
   - 根据 `scenario_info.operation` 生成 **1个** 对应操作
   - 必须使用对应的 stage 和 op
   - 优先使用 search/filter（而非 ids）
   
3. **对于 workflow 样本**：
   - 根据用户指令内容生成 **2-5个** 逻辑相关的操作
   - 忽略 `scenario_info.operation`（仅供参考）
   - 操作类型自由选择
   - 步骤间用 ids 引用
   
4. **构建 prerequisites**：
   - Encode: 不需要
   - Retrieve/Summarize: 3-5条
   - STO操作: 1-3条
   - 必须是完整 IR（有 stage, op, args）
   
5. **选择 target**：
   - 严格按照上面的比例参考
   - 优先 search（检索）/ filter（批量）
   - 减少 ids，避免 all
   
6. **输出格式**：
   - JSONL（一行一个JSON）
   - 完整字段（id, class, nl, prerequisites, schema_list, init_db, notes）

---

## 📤 输出规范

* 输出 1 个 JSON 对象或数组，无额外文字/代码块
* 单行 JSONL 格式
* ID 规则：

  * single：`t2m-{lang}-{instruction_type}-single-{op}-{seq}`
  * workflow：`t2m-{lang}-{instruction_type}-workflow-wf-{seq}`

---

---

## 🚨 常见错误和修复规则（⚠️ 必读！避免生成错误）

根据大量测试样本的错误统计，以下是**最常见的9类错误及其修复方法**。生成前务必检查！

### 1️⃣ facets 不能为空或只有时间 ⭐⭐⭐

**错误示例**：
```json
{"args": {"payload": {...}, "facets": {}}}  // ❌ 空对象
{"args": {"payload": {...}, "facets": {"time": "..."}}}  // ❌ 只有时间
```

**正确示例**：
```json
{"args": {"payload": {...}, "facets": {"certainty": "confirmed"}}}
{"args": {"payload": {...}, "facets": {"amount": 2000000, "currency": "CNY"}}}
{"args": {"payload": {...}, "facets": {"priority": "high", "status": "active"}}}
```

**规则**：
- ✅ facets 必须至少包含一个**业务字段**
- ✅ 推荐字段：`certainty`, `priority`, `status`, `category`, `amount`, `duration`, `deadline` 等
- ❌ 不要只放 `time`（时间应该用顶层的 `time` 字段）
- ❌ 不要留空对象 `{}`

---

### 2️⃣ time_range 必须使用扁平格式 ⭐⭐⭐

**错误示例**：
```json
{"time_range": {"absolute": {"start": "...", "end": "..."}}}  // ❌ 嵌套
{"time_range": {"relative": "last", "amount": 7}}  // ❌ 缺 unit
{"time_range": {"start": "2025-10-01T00:00:00Z"}}  // ❌ 只有 start
```

**正确示例**：
```json
{"time_range": {"relative": "last", "amount": 7, "unit": "days"}}  // ✅ 相对时间
{"time_range": {"start": "2025-10-01T00:00:00Z", "end": "2025-10-21T00:00:00Z"}}  // ✅ 绝对时间
```

**规则**：
- ✅ 优先使用 `relative` 格式（推荐）
- ✅ 相对时间必须包含：`relative`, `amount`, `unit` 三个字段
- ✅ 绝对时间必须包含：`start`, `end` 两个字段
- ❌ 不要使用嵌套的 `absolute` 对象
- ❌ 不要只提供 start 或 end 之一

---

### 3️⃣ Promote 必须提供三选一参数 ⭐⭐⭐

**错误示例**：
```json
{"op": "Promote", "args": {"priority": "high"}}  // ❌ priority 不是有效参数
{"op": "Promote", "args": {"reason": "重要"}}  // ❌ 只有 reason
```

**正确示例**：
```json
{"op": "Promote", "args": {"weight_delta": 0.3, "reason": "提升优先级"}}  // ✅ 相对增量
{"op": "Promote", "args": {"weight": 0.8}}  // ✅ 绝对权重
{"op": "Promote", "args": {"remind": {"rrule": "FREQ=WEEKLY;BYDAY=FR"}}}  // ✅ 设置提醒
```

**规则**：
- ✅ 必须提供以下**至少一种**：
  - `weight` - 绝对权重（0-1之间）
  - `weight_delta` - 相对增量（-1到1之间，推荐 0.2-0.3）
  - `remind` - 提醒规则
- ✅ 推荐使用 `weight_delta`（更自然）
- ❌ 不要只写 `priority` 或 `reason`
- ✅ `reason` 是可选的说明字段，可以附加

---

### 4️⃣ Update 的 set 必须包含有效字段 ⭐⭐⭐

**错误示例**：
```json
{"op": "Update", "args": {"set": {}}}  // ❌ 空对象
{"op": "Update", "args": {"set": {"note": "更新说明"}}}  // ❌ note 不是标准字段
{"op": "Update", "args": {"set": {"progress_note": "..."}}}  // ❌ 自定义字段
```

**正确示例**：
```json
{"op": "Update", "args": {"set": {"text": "更新后的内容"}}}  // ✅ 更新文本
{"op": "Update", "args": {"set": {"subject": "新主题"}}}  // ✅ 更新主题
{"op": "Update", "args": {"set": {"tags": ["已处理", "重要"]}}}  // ✅ 更新标签
{"op": "Update", "args": {"set": {"weight": 0.8}}}  // ✅ 更新权重
```

**规则**：
- ✅ `set` 必须包含至少一个标准字段：
  - `text` - 主要文本内容
  - `subject` - 主题
  - `tags` - 标签数组
  - `weight` - 权重（0-1）
- ❌ 不要使用非标准字段（如 `note`, `progress_note`）
- ❌ 不要留空对象

---

### 5️⃣ ids 和 tags 必须是数组格式 ⭐⭐

**错误示例**：
```json
{"target": {"ids": "1,2,3"}}  // ❌ 字符串
{"target": {"ids": 1}}  // ❌ 数字
{"args": {"tags": "重要"}}  // ❌ 字符串
```

**正确示例**：
```json
{"target": {"ids": ["1", "2", "3"]}}  // ✅ 字符串数组
{"args": {"tags": ["重要", "紧急"]}}  // ✅ 字符串数组
{"target": {"ids": ["1"]}}  // ✅ 单个元素也用数组
```

**规则**：
- ✅ 所有 `ids` 字段必须是**字符串数组**：`["1", "2"]`
- ✅ 所有 `tags` 字段必须是**字符串数组**：`["tag1", "tag2"]`
- ❌ 不要使用逗号分隔的字符串
- ❌ 不要使用数字或单个字符串
- ✅ 即使只有一个元素，也要用数组：`["1"]`

---

### 6️⃣ Stage 和 Op 必须匹配 ⭐⭐

**错误示例**：
```json
{"stage": "STO", "op": "Encode"}  // ❌ Encode 应该是 ENC
{"stage": "ENC", "op": "Retrieve"}  // ❌ Retrieve 应该是 RET
{"stage": "RET", "op": "Label"}  // ❌ Label 应该是 STO
```

**正确映射表**：

| Op | Stage | 说明 |
|----|-------|------|
| `Encode` | `ENC` | 创建记录 |
| `Retrieve`, `Summarize` | `RET` | 检索和摘要 |
| `Label`, `Update`, `Promote`, `Demote`, `Delete`, `Merge`, `Split`, `Lock`, `Expire` | `STO` | 存储管理操作 |

**规则**：
- ✅ 严格按照上表映射
- ❌ 不要混淆 stage 和 op

---

### 7️⃣ Expire 必须用 ttl 或 until ⭐⭐

**错误示例**：
```json
{"op": "Expire", "args": {"time_delta": {"days": 90}}}  // ❌ 不支持 time_delta
{"op": "Expire", "args": {"duration": "90 days"}}  // ❌ 不支持 duration
{"op": "Expire", "args": {"ttl": "P90D", "until": "2026-01-01T00:00:00Z"}}  // ❌ 不能同时提供
```

**正确示例**：
```json
{"op": "Expire", "args": {"ttl": "P90D"}}  // ✅ 相对过期（ISO 8601 duration）
{"op": "Expire", "args": {"until": "2026-01-15T00:00:00Z"}}  // ✅ 绝对过期时间
{"op": "Expire", "args": {"ttl": "P90D", "on_expire": "soft_delete"}}  // ✅ 带行为
```

**规则**：
- ✅ 必须提供以下**二选一**：
  - `ttl` - ISO 8601 duration 格式（如 `"P90D"` = 90天）
  - `until` - 绝对时间（ISO 8601 格式）
- ✅ 可选 `on_expire` - 过期行为（`soft_delete`, `hard_delete`, `demote`, `anonymize`）
- ❌ 不要使用 `time_delta`, `duration` 等自定义字段
- ❌ 不能同时提供 ttl 和 until

---

### 8️⃣ Split strategy 限定三种 ⭐

**错误示例**：
```json
{"op": "Split", "args": {"strategy": "by_topics"}}  // ❌ 不支持
{"op": "Split", "args": {"strategy": "by_paragraphs"}}  // ❌ 不支持
```

**正确示例**：
```json
{"op": "Split", "args": {"strategy": "by_sentences", "params": {"max_sentences": 3}}}
{"op": "Split", "args": {"strategy": "by_chunks", "params": {"num_chunks": 3}}}
{"op": "Split", "args": {"strategy": "custom", "params": {"delimiters": ["\n\n"]}}}
```

**规则**：
- ✅ strategy 只能是以下三种之一：
  - `by_sentences` - 按句子拆分
  - `by_chunks` - 按块拆分
  - `custom` - 自定义拆分
- ✅ 必须提供 `params` 参数
- ❌ 不要使用其他 strategy

---

### 9️⃣ Label 必须提供 tags 或 facets ⭐⭐

**错误示例**：
```json
{"op": "Label", "args": {"mode": "add"}}  // ❌ 没有 tags
{"op": "Label", "args": {}}  // ❌ 空参数
```

**正确示例**：
```json
{"op": "Label", "args": {"tags": ["重要"], "mode": "add"}}  // ✅ 添加标签
{"op": "Label", "args": {"tags": ["旧标签"], "mode": "remove"}}  // ✅ 删除标签
{"op": "Label", "args": {"facets": {"status": "done"}, "mode": "add"}}  // ✅ 添加facets
```

**规则**：
- ✅ 必须提供 `tags` 或 `facets`（至少一个）
- ✅ `mode` 可选值：`add`（默认）, `remove`, `replace`
- ✅ tags 必须是字符串数组
- ❌ 不要留空参数

---

### 🎯 快速检查清单

生成每个 IR 操作前，快速检查：

- [ ] **Encode**: facets 不为空，至少有一个业务字段
- [ ] **time_range**: 使用扁平格式，相对时间三字段齐全
- [ ] **Promote**: 有 weight/weight_delta/remind 之一
- [ ] **Update**: set 中有 text/subject/tags/weight 之一
- [ ] **ids/tags**: 都是字符串数组格式
- [ ] **Stage-Op**: 映射正确（Encode→ENC, Retrieve→RET, Label→STO）
- [ ] **Expire**: 用 ttl 或 until，不用 time_delta
- [ ] **Split**: strategy 是三种之一
- [ ] **Label**: 有 tags 或 facets

---

## ✅ 最终检查清单

生成每个样本前，请确认：

- [ ] 指令是否在上述12个指令之中，与阶段是否对应
- [ ] structure 正确（single=1个操作，workflow=2-5个操作）
- [ ] single 样本的操作匹配 scenario_info.operation
- [ ] workflow 样本不受 scenario_info.operation 约束
- [ ] prerequisites 是完整 IR 数组（有 stage, op, args）
- [ ] target 选择合适（优先 search/filter）
- [ ] 输出是 JSONL（一行一个JSON，无格式化）
- [ ] ID 命名正确（workflow 用 wf）

---

## 📤 输出要求（⚠️ 极其重要！必须严格遵守）

### 1. 必需字段（缺一不可）

**你必须输出一个包含以下所有字段的完整JSON对象**：

```json
{
  "id": "t2m-zh-direct-single-ret-001",           // ✅ 必需
  "class": {                                       // ✅ 必需
    "instruction": "direct",
    "structure": "single",
    "lang": "zh"
  },
  "nl": {                                          // ✅ 必需
    "zh": "自然语言指令"
  },
  "prerequisites": [                               // ✅ 必需（数组，可以为空[]）
    {
      "stage": "ENC",
      "op": "Encode",
      "args": {...}
    }
  ],
  "schema_list": [                                 // ✅ 必需（数组，不能为空）
    {
      "stage": "RET",
      "op": "Retrieve",
      "target": {...},
      "args": {...}
    }
  ],
  "init_db": null,                                 // ✅ 必需（固定为null）
  "notes": "样本说明"                               // ✅ 必需
}
```

### 2. 字段要求详细说明

| 字段 | 类型 | 可否为空 | 说明 |
|------|------|---------|------|
| `id` | string | ❌ 不可 | 必须按规则生成 |
| `class` | object | ❌ 不可 | 必须包含 instruction/structure/lang |
| `nl` | object | ❌ 不可 | 必须包含对应语言的指令 |
| `prerequisites` | array | ✅ 可为`[]` | Encode操作可以是空数组，其他操作必须有内容 |
| `schema_list` | array | ❌ 不可为空 | 至少包含1个操作（single）或2-5个操作（workflow） |
| `init_db` | null | ❌ 必须为`null` | 固定值 |
| `notes` | string | ❌ 不可 | 简短说明 |

### 3. 格式要求

1. **只输出一个完整的JSON对象**，不要输出多个
2. **不要添加任何说明文字、注释或markdown标记**
3. **不要使用```json```代码块**
4. **不要格式化**，所有内容在一行
5. **确保JSON格式正确**，可以被标准JSON解析器解析
6. **所有必需字段必须存在**，即使为空数组或null

### 4. 正确示例

**示例1：Retrieve操作（有prerequisites）**
```
{"id":"t2m-zh-direct-single-ret-001","class":{"instruction":"direct","structure":"single","lang":"zh"},"nl":{"zh":"查找上周的会议记录"},"prerequisites":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"产品设计会议记录","knowledge_type":"fact","source":"会议系统"},"type":"knowledge","tags":["会议","产品"],"time":"2025-10-18T10:00:00Z"}}],"schema_list":[{"stage":"RET","op":"Retrieve","target":{"search":{"intent":{"query":"会议记录"},"overrides":{"k":5,"alpha":0.7}}},"args":{"include":["id","text","tags"]}}],"init_db":null,"notes":"检索上周会议记录"}
```

**示例2：Encode操作（无prerequisites）**
```
{"id":"t2m-zh-direct-single-enc-001","class":{"instruction":"direct","structure":"single","lang":"zh"},"nl":{"zh":"记录今天的会议内容"},"prerequisites":[],"schema_list":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"会议讨论了产品设计方案","knowledge_type":"fact","source":"会议记录"},"type":"knowledge","tags":["会议","产品"],"time":"2025-10-20T10:00:00Z"}}],"init_db":null,"notes":"记录会议内容"}
```

### 5. 错误示例（❌ 这些都是错误的）

**错误1：缺少必需字段**
```json
{"nl":{"zh":"查找会议"}, "context":"..."}  // ❌ 缺少 id, class, prerequisites, schema_list, init_db, notes
```

**错误2：有说明文字**
```
这是生成的样本：
{"id":"..."}  // ❌ 不要有任何说明文字
```

**错误3：使用代码块**
````
```json
{"id":"..."}
```
// ❌ 不要使用markdown代码块
````

**错误4：输出多个JSON对象**
```
{"id":"001"}
{"id":"002"}  // ❌ 只能输出一个JSON对象
```

**错误5：schema_list为空**
```json
{"id":"...","schema_list":[]}  // ❌ schema_list 不能为空数组
```

---

## 🎯 当前生成任务

**请为以下指令生成完整的 IR Schema**：

- **指令**: {instruction}
- **Context**: {context}
- **场景**: {scenario}
- **操作**: {operation}
- **结构**: {structure}
- **语言**: {lang}

### 任务要求

1. **基于上述指令和context生成准确的 IR Schema**
2. **如果是Encode操作**：
   - `prerequisites` 可以为空数组 `[]`
   - `schema_list` 包含1个Encode操作
   - 应用知识提取原则：原子化、类型化、结构化
   
3. **如果是Retrieve/Summarize操作**：
   - `prerequisites` 必须包含3-5条知识单元（应用知识提取原则拆分）
   - `schema_list` 包含1个对应操作
   - prerequisites的时间必须与查询范围匹配
   
4. **如果是STO操作**（Label/Update/Delete等）：
   - `prerequisites` 必须包含1-3条知识单元
   - `schema_list` 包含1个对应操作
   
5. **如果是workflow结构**：
   - `schema_list` 包含2-5个逻辑相关的操作
   - 步骤间用ids引用

6. **知识提取要求**（重要）：
   - prerequisites中的每个Encode必须是原子化的知识点
   - 添加 `knowledge_type`, `source`, `context` 字段
   - 使用 `type: "knowledge"` 而非 `type: "note"`
   - 在facets中提取结构化元数据

7. **输出格式**：
   - 单行JSONL格式
   - 包含所有必需字段
   - 无任何额外文字

---

# 🧪 示例参考（用于生成结构校验）

---

### ✅ 示例 1：Encode-only（无前置）

**输入**

```json
{
  "instruction":"记录今天早上的团队会议内容",
  "context":"用户刚开完日常站会",
  "classification":{"instruction_type":"direct","structure":"single","lang":"zh"},
  "scenario_info":{"scenario":"meeting_notes","operation":"encode","style":"formal","topic":"日常会议"}
}
```

**输出**

```json
{"id":"t2m-zh-direct-single-enc-001","class":{"instruction_type":"direct","structure":"single","lang":"zh"},"nl":{"zh":"记录今天早上的团队会议内容"},"context":"用户刚开完日常站会","prerequisites":[],"schema_list":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"今日早会讨论了当前版本测试进展与下周任务规划","knowledge_type":"fact","source":"会议纪要","context":"团队日会"},"type":"note","tags":["会议","日常","项目进展"],"time":"2025-10-21T09:00:00Z","facets":{"certainty":"confirmed"}}}],"init_db":null,"notes":"无前置操作"}
```

---

### ✅ 示例 2：Retrieve（有 3–5 条知识单元）

**输入**

```json
{
  "instruction":"查找上周关于项目预算的会议纪要",
  "context":"用户准备汇报预算进度",
  "classification":{"instruction_type":"direct","structure":"single","lang":"zh"},
  "scenario_info":{"scenario":"meeting_notes","operation":"retrieve","style":"concise","topic":"项目预算"}
}
```

**输出**

```json
{"id":"t2m-zh-direct-single-ret-001","class":{"instruction_type":"direct","structure":"single","lang":"zh"},"nl":{"zh":"查找上周关于项目预算的会议纪要"},"context":"用户准备汇报预算进度","prerequisites":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"预算评审会议：确认Q4预算目标为200万人民币","knowledge_type":"fact","source":"财务部会议","context":"Q4预算讨论"},"type":"knowledge","tags":["会议","预算"],"time":"2025-10-18T10:00:00Z","facets":{"amount":2000000,"currency":"CNY"}}},{"stage":"ENC","op":"Encode","args":{"payload":{"text":"预算支出需控制在上限200万以内","knowledge_type":"constraint","source":"财务总监","context":"预算限制"},"type":"knowledge","tags":["预算","约束"],"time":"2025-10-18T10:05:00Z","facets":{"amount_limit":2000000,"currency":"CNY"}}},{"stage":"ENC","op":"Encode","args":{"payload":{"text":"研发部门申请增加预算10%用于性能优化","knowledge_type":"request","source":"研发经理","context":"预算申请"},"type":"knowledge","tags":["预算","研发"],"time":"2025-10-17T14:00:00Z","facets":{"increase_ratio":0.1}}}],"schema_list":[{"stage":"RET","op":"Retrieve","target":{"filter":{"has_tags":["会议","预算"],"time_range":{"relative":"last","amount":7,"unit":"days"}}},"args":{"include":["id","text","tags"]}}],"init_db":null,"notes":"检索预算相关会议记录"}
```

---

### ✅ 示例 3：STO 操作（有 1–3 条知识单元）

**输入**

```json
{
  "instruction":"将安全审计结果标记为高优先级",
  "context":"用户在管理近期安全审计任务",
  "classification":{"instruction_type":"direct","structure":"single","lang":"zh"},
  "scenario_info":{"scenario":"security_audit","operation":"label","style":"concise","topic":"安全审计"}
}
```

**输出**

```json
{"id":"t2m-zh-direct-single-sto-001","class":{"instruction_type":"direct","structure":"single","lang":"zh"},"nl":{"zh":"将安全审计结果标记为高优先级"},"context":"用户在管理近期安全审计任务","prerequisites":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"2025年10月安全审计发现两个关键漏洞","knowledge_type":"fact","source":"安全团队报告","context":"月度安全审计"},"type":"knowledge","tags":["安全","漏洞"],"time":"2025-10-18T11:00:00Z","facets":{"severity":"critical"}}}],"schema_list":[{"stage":"STO","op":"Label","target":{"filter":{"has_tags":["安全","漏洞"],"time_range":{"relative":"last","amount":7,"unit":"days"}}},"args":{"tags":["高优先级"],"mode":"add"}}],"init_db":null,"notes":"对关键漏洞结果加标签"}
```

---

## 🚨 最后提醒

**你必须输出一个包含以下7个字段的完整JSON对象**：
1. `id` ✅
2. `class` ✅
3. `nl` ✅
4. `prerequisites` ✅ （数组，Encode可为[]，其他需有内容）
5. `schema_list` ✅ （数组，不能为空）
6. `init_db` ✅ （固定为null）
7. `notes` ✅

**现在开始生成！直接输出完整的JSON对象，不要任何其他内容。**

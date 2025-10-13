# Stage 2: IR Schema 生成

## 🎯 任务目标

将 Stage 1 的自然语言样本转换为 **Text2Mem IR Schema**（中间表示）。

**核心要点**：
1. ✅ **准确映射** NL 指令 → IR 操作
2. ✅ **完整的 prerequisites** - 可执行的 IR 数组（不是描述）
3. ✅ **多样的 target 方式** - 优先使用 search/filter，而非简单 ids
4. ✅ **workflow 处理** - 2-5个逻辑相关的操作组合

---

## 📋 输入输出

### 输入（来自 Stage 1）
```json
{
  "instruction": "查找上周关于产品设计的会议记录",
  "context": "...",
  "classification": {
    "instruction_type": "direct",
    "structure": "single",
    "lang": "zh"
  },
  "scenario_info": {
    "scenario": "meeting_notes",
    "operation": "retrieve"
  }
}
```

### 输出（JSONL，一行一个JSON）
```json
{"id":"t2m-zh-direct-single-ret-001","class":{"instruction":"direct","structure":"single","lang":"zh"},"nl":{"zh":"查找上周关于产品设计的会议记录"},"prerequisites":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"会议记录：产品设计讨论..."},"type":"note","tags":["会议","产品"]}}],"schema_list":[{"stage":"RET","op":"Retrieve","target":{"search":{"intent":{"query":"产品设计会议"},"overrides":{"k":5,"alpha":0.7}}},"args":{"include":["id","text","tags"]}}],"init_db":null,"notes":"检索产品设计相关会议"}
```

---

## 🏗️ IR Schema 基本格式

```json
{
  "stage": "ENC|STO|RET",
  "op": "操作名称",
  "target": {/* 四选一: ids|search|filter|all */},
  "args": {/* 操作参数 */},
  "_comment": "可选说明"
}
```

**Stage 对应**：
- `ENC` - Encode（创建记录）
- `STO` - Update, Label, Promote, Demote, Merge, Split, Delete, Lock, Expire（存储管理）
- `RET` - Retrieve, Summarize（检索）

---

## 🎯 Target 选择器（⭐ 重点：多样性！）

### 四种方式（必须四选一）

#### 1. **search** - 语义搜索 ⭐⭐⭐

**适用场景**：
- **Retrieve 操作**
- **Summarize 操作**
- 任何基于"内容相关性"的查询

```json
"target": {
  "search": {
    "intent": {"query": "产品设计会议讨论"},
    "overrides": {
      "k": 10,
      "alpha": 0.7,
      "order_by": "relevance"
    }
  }
}
```

**参数说明**：
- `intent.query` - 自然语言查询（提取用户意图）
- `k` - 返回数量（3-20）
- `alpha` - 混合权重：0.0=纯关键词，0.7=混合（推荐），1.0=纯语义
- `order_by` - 排序：`relevance`（推荐）| `time_desc` | `time_asc` | `weight_desc`

---

#### 2. **filter** - 条件过滤 ⭐⭐

**适用场景**：
- **批量更新/删除（60-80%应使用）**
- 基于标签/时间/类型的筛选
- Label/Promote/Demote/Expire操作（40-50%应使用）

```json
"target": {
  "filter": {
    "has_tags": ["会议", "重要"],
    "type": "note",
    "priority": "high",
    "time_range": {
      "relative": "last",
      "amount": 7,
      "unit": "days"
    },
    "limit": 50
  }
}
```

**时间范围**：
```json
// 相对时间（推荐，更自然）
{"relative": "last", "amount": 30, "unit": "days"}
{"relative": "last", "amount": 3, "unit": "months"}

// 绝对时间
{"absolute": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}}
```

---

#### 3. **ids** - 直接ID引用

**适用场景**：
- Prerequisites 引用（workflow中）
- **Merge/Split 操作**
- 明确指定特定记录

```json
"target": {"ids": ["1"]}
"target": {"ids": ["1", "2", "3"]}
```

---

#### 4. **all** - 全选（谨慎使用）

**仅用于**：清空全部、重置系统等危险操作

```json
"target": {"all": true}
```

⚠️ 必须配合 `"meta": {"confirmation": true}`

---

## 🎲 Prerequisites（前置环境）

### ⚠️ 重要：必须是完整的 IR 操作数组

**不是描述**，是**可执行的 IR**！

### 规则

| 操作类型 | 是否需要 | 数量 |
|---------|---------|------|
| Encode | ❌ 否 | - |
| Retrieve/Summarize | ✅ 是 | 3-5条 |
| STO操作 | ✅ 是 | 1-3条 |

### ✅ 正确格式

```json
"prerequisites": [
  {
    "stage": "ENC",
    "op": "Encode",
    "args": {
      "payload": {"text": "会议记录：产品设计讨论..."},
      "type": "note",
      "tags": ["会议"]
    },
    "_comment": "创建记录1"
  },
  {
    "stage": "ENC",
    "op": "Encode",
    "args": {
      "payload": {"text": "项目进展：Q4路线图更新..."},
      "type": "note",
      "tags": ["项目"]
    },
    "_comment": "创建记录2"
  }
]
```

### ❌ 错误格式

```json
"prerequisites": [
  {"id": "1", "text": "描述"}  // ❌ 这只是描述，不是IR
]
```

### ID 引用机制

- prerequisites 执行后自动分配 ID（1, 2, 3...）
- 主操作通过 `"target": {"ids": ["1"]}` 引用
- workflow 步骤间也用 ids 引用

---

## 📝 Structure 分类处理

### 1. Single（单操作）

**特点**：
- schema_list 只有 **1个** 操作
- 操作类型 = `scenario_info.operation`（**必须匹配**）

**示例**：
```json
{
  "class": {"structure": "single"},
  "schema_list": [
    {"stage": "RET", "op": "Retrieve", "target": {...}, "args": {...}}
  ]
}
```

---

### 2. Workflow（多操作）

**特点**：
- schema_list 有 **2-5个** 操作
- 操作类型根据用户指令自由选择（**不受 scenario_info.operation 约束**）
- 步骤间用 ids 引用前面的结果

**示例**：
```json
{
  "class": {"structure": "workflow"},
  "nl": {"zh": "先记录会议内容，再生成摘要，然后标记重点，最后设置提醒"},
  "schema_list": [
    {
      "stage": "ENC",
      "op": "Encode",
      "args": {"payload": {"text": "会议内容..."}, "type": "note"}
    },
    {
      "stage": "RET",
      "op": "Summarize",
      "target": {"ids": ["1"]},
      "args": {"focus": "action items"}
    },
    {
      "stage": "STO",
      "op": "Label",
      "target": {"ids": ["1"]},
      "args": {"tags": ["重要"], "mode": "add"}
    },
    {
      "stage": "STO",
      "op": "Promote",
      "target": {"ids": ["1"]},
      "args": {"priority": "high", "remind": {...}}
    }
  ]
}
```

**关键点**：
- 步骤间用 ids 引用
- 操作类型多样（不只是同类）
- 符合自然语言的步骤顺序

---

## 📤 输出样本结构

### 完整样本格式

```json
{
  "id": "t2m-{lang}-{instruction}-{structure}-{op}-{seq}",
  "class": {
    "instruction": "direct|indirect",
    "structure": "single|workflow",
    "lang": "zh|en"
  },
  "nl": {
    "zh": "自然语言指令（中文）"
  },
  "prerequisites": [/* IR操作数组 */],
  "schema_list": [/* IR操作数组 */],
  "init_db": null,
  "notes": "样本说明"
}
```

### ID 命名规则

格式：`t2m-{lang}-{instruction}-{structure}-{op}-{seq}`

**对于 single**：
- `op` = 操作名称缩写（enc/ret/lab/upd/del/pro/dem/mer/spl/loc/exp/sum）
- 示例：`t2m-zh-direct-single-ret-001`

**对于 workflow**：
- `op` = `wf`
- 示例：`t2m-zh-direct-workflow-wf-001`

---

## ⚠️ 关键约束

### 1. JSONL 格式

- **一行一个完整 JSON 对象**
- 不要换行、不要格式化
- 不要添加 markdown 代码块

### 2. Prerequisites 必须是 IR

❌ **错误**：
```json
"prerequisites": [
  {"id": "1", "text": "描述"}
]
```

✅ **正确**：
```json
"prerequisites": [
  {"stage": "ENC", "op": "Encode", "args": {...}}
]
```

### 3. Target 互斥

不能同时使用多种方式：

❌ **错误**：
```json
"target": {"ids": ["1"], "filter": {...}}
```

✅ **正确**：
```json
"target": {"ids": ["1"]}
```

### 4. Structure 对应

- `single`: schema_list 只有 **1个** 操作，且必须匹配 `scenario_info.operation`
- `workflow`: schema_list 有 **2-5个** 操作，不受 `scenario_info.operation` 约束

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

## 📤 输出要求（重要！）

**请严格遵守以下格式：**

1. **只输出一个JSON对象**，不要输出多个
2. **不要添加任何说明文字、注释或markdown标记**
3. **不要使用```json```代码块**
4. **不要格式化**，所有内容在一行
5. **确保JSON格式正确**，可以被标准JSON解析器解析

**正确示例**：
```
{"id":"t2m-zh-direct-single-ret-001","class":{"instruction":"direct","structure":"single","lang":"zh"},"nl":{"zh":"查找会议记录"},"prerequisites":[{"stage":"ENC","op":"Encode","args":{"payload":{"text":"会议内容"},"type":"note"}}],"schema_list":[{"stage":"RET","op":"Retrieve","target":{"search":{"intent":{"query":"会议"}}},"args":{"include":["id","text"]}}],"init_db":null,"notes":"检索"}
```

**错误示例**：
```
这是生成的样本：
{"id":"..."}

或者：

```json
{"id":"..."}
```

或者：

{"id":"..."}
{"id":"..."}  # 多个JSON对象
```

---

**现在开始生成！直接输出JSON，不要任何其他内容。**

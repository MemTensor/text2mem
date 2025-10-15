# Stage 3: Expected结果生成（测试验证完善）

## 🎯 核心目标

你是**Text2Mem测试验证专家**。你的任务是为Stage 2生成的测试样本添加**expected字段**，使其成为完整的、可执行的、可验证的测试用例。

---

## 📋 你要做什么

为每个测试样本添加`expected`字段，包含：

1. ✅ **assertions** — SQL断言，验证操作的实际效果
2. ✅ **ranking** — 检索结果排名验证（仅Retrieve操作）
3. ✅ **triggers** — 时间触发器（通常为空）
4. ✅ **meta** — **必须包含**评测元信息：SQL方言/评测时间/检索步骤索引

**不需要修改**：

* ❌ `id`、`class`、`nl`、`prerequisites`、`schema_list`、`init_db`、`notes` 等字段 — 保持 Stage 2 原样

---

## ⏰ 虚拟评测时间（重要！）

**所有测试样本必须使用固定的虚拟评测时间**：`2025-10-21T00:00:00Z`

这是测试的虚拟"当前时间"，确保：
- ✅ 相对时间查询（"上周"、"最近30天"）可复现
- ✅ 测试结果不受实际运行时间影响
- ✅ Prerequisites 中的时间戳与查询时间范围一致

**在 expected.meta 中必须设置**：
```json
{
  "expected": {
    "meta": {
      "eval_time_utc": "2025-10-21T00:00:00Z",  // ⚠️ 固定使用此时间
      "dialect": "sqlite",
      "step_index": 0
    }
  }
}
```

---

## 🗄️ 评测数据库契约（对齐真实 DDL）

**SQL方言**：默认 **SQLite 3**；如使用 Postgres，请在 `expected.meta.dialect="postgres"` 指定。
**表**：`memory`（字段与含义与 DDL 对齐，关键字段如下）

* 主键与内容：`id INTEGER PRIMARY KEY AUTOINCREMENT`, `text TEXT`, `type TEXT`
* 结构化属性：`subject TEXT`, `time TEXT`, `location TEXT`, `topic TEXT`
* 标签与扩展：`tags TEXT`（JSON array），`facets TEXT`（JSON object，含 `{subject,time,location,topic}`）
* 重要度：`weight REAL`
* 嵌入：`embedding TEXT`（JSON array），`embedding_dim INTEGER`，`embedding_model TEXT`，`embedding_provider TEXT`
* 生命周期：`source TEXT`, `auto_frequency TEXT`, `next_auto_update_at TEXT`, `expire_at TEXT`, `expire_action TEXT`, `expire_reason TEXT`
* 锁：`lock_mode TEXT`, `lock_reason TEXT`, `lock_policy TEXT`, `lock_expires TEXT`
* 谱系：`lineage_parents TEXT`（JSON array of IDs）, `lineage_children TEXT`（JSON array）
* 权限：`read_perm_level TEXT`, `write_perm_level TEXT`, `read_whitelist TEXT`（JSON array）, `read_blacklist TEXT`, `write_whitelist TEXT`, `write_blacklist TEXT`
* 标记：`deleted INTEGER DEFAULT 0`

**JSON 访问约定**

* SQLite：

  * `facets.time` → `JSON_EXTRACT(facets,'$.time')`
  * `tags` 包含某值 → `EXISTS (SELECT 1 FROM json_each(tags) WHERE value LIKE :tag)`
  * `lineage_*` 包含某 id → `EXISTS (SELECT 1 FROM json_each(lineage_children) WHERE value = :child_id)`
* Postgres（当 `meta.dialect="postgres"`）：

  * `facets->>'time'`
  * `EXISTS (SELECT 1 FROM json_array_elements_text(tags) t(value) WHERE t.value LIKE :tag)`

**时间字段优先级**

* 若样本/检索涉及时间窗口：**优先使用顶层 `time`**；为空再回退 `facets.time`。两者均为 ISO8601 字符串。

---

## 📊 输入格式

Stage 2 的输出（JSONL），每行一个测试样本：

```jsonl
{"id":"t2m-zh-direct-single-enc-001","class":{...},"nl":{...},"prerequisites":[],"schema_list":[...],"init_db":null,"notes":"..."}
```

---

## 📤 输出格式

⚠️ **必须直接输出 JSONL**（每行一个完整的测试样本）

```jsonl
{"id":"t2m-zh-direct-single-enc-001","class":{...},"nl":{...},"prerequisites":[],"schema_list":[...],"init_db":null,"expected":{"assertions":[...],"ranking":null,"triggers":[],"meta":{"dialect":"sqlite","eval_time_utc":"2025-10-21T00:00:00Z","step_index":0}},"notes":"..."}
```

**格式要求**：

* ✅ 每行一个完整 JSON 对象
* ✅ 仅新增 `expected` 字段（含 assertions、ranking、triggers，可选 meta）
* ✅ 保持其他字段不变
* ✅ 不要任何解释文字或 markdown 标记
* ✅ 不要用 JSON Array 的 `[` 和 `]` 包裹

---

## 🏗️ Expected 字段结构

```json
{
  "expected": {
    "assertions": [
      {
        "name": "assertion_name",
        "select": {
          "from": "memory",
          "where": ["deleted=0", "text LIKE :keyword"],
          "agg": "count"  // 可选：count/sum/avg/min/max，默认count
        },
        "expect": {"op": "==", "value": 1}, // ==|>=|>|<|<=|!=
        "params": {"keyword": "%关键词%", "id": "1"}
      }
    ],
    "ranking": {                  // 仅 Retrieve 需要，其余为 null
      "gold_ids": ["1","3"],     // 以“逻辑ID”表示（见下方ID映射）
      "min_hits": 1,             // 至少命中个数
      "allow_extra": true,       // 允许top-k出现非gold
      "k": 5                     // 评估top-k（若返回不足k，以实际数量评估）
    },
    "triggers": [],               // 时间触发器（通常为空）
    "meta": {                     // **必须包含**：评测元信息
      "dialect": "sqlite",        // sqlite | postgres
      "eval_time_utc": "2025-10-21T00:00:00Z",  // ⚠️ 固定使用此虚拟评测时间
      "step_index": 0             // 多次检索时指定评测哪一步
    }
  }
}
```

---

## 🔢 ID 映射规则（强制）

* **Prerequisites 的“逻辑 ID”**：按出现顺序映射 `"1","2","3"...`（与表内自增 `id` 无关）。
* `ranking.gold_ids` 与所有断言内 `:id`/`:ids` 参数**必须使用逻辑 ID**。评测器会在载入 prerequisites 时记录插入行的真实自增 id 并完成映射。
* `schema_list[].target.ids`（如有）也指向这些逻辑 ID。

---

## 🕒 时间语义

* 评测时间基准：`expected.meta.eval_time_utc`（如未提供，则用评测器系统时间 UTC）。
* 若检索包含时间窗口（如 `time_from/time_to`），它约束的是 `memory.time`；若为空再回退 `facets.time`。
* Ranking 仅基于相关性与期望 ID，不对时间二次判定；时间窗口只影响候选集。

---

## 📚 12种操作的 Assertion 设计指南（对齐真实表结构）

### 1. Encode

**验证重点**：记录创建、内容保存、标签入库（JSON）
**典型 assertions**：

```json
{
  "assertions": [
    {
      "name": "record_created",
      "select": {"from": "memory", "where": ["deleted=0"]},
      "expect": {"op": ">=", "value": 1},
      "_comment": "至少创建1条记录"
    },
    {
      "name": "content_saved",
      "select": {"from": "memory", "where": ["deleted=0", "text LIKE :keyword"]},
      "expect": {"op": "==", "value": 1},
      "params": {"keyword": "%关键词%"}
    },
    {
      "name": "tags_saved_json",
      "select": {
        "from": "memory",
        "where": [
          "deleted=0",
          "EXISTS (SELECT 1 FROM json_each(tags) WHERE value LIKE :tag)"
        ]
      },
      "expect": {"op": ">=", "value": 1},
      "params": {"tag": "%标签名%"}
    }
  ],
  "ranking": null
}
```

**关键词提取**：从 `schema_list[0].args.payload.text` 提取 1–2 个词。

---

### 2. Retrieve

**验证重点**：检索结果排名
**典型 expected**：

```json
{
  "assertions": [],
  "ranking": {
    "gold_ids": ["1","3"],
    "min_hits": 1,
    "allow_extra": true,
    "k": 5
  }
}
```

**gold_ids 设计**：从 prerequisites 中选择与 query 最相关的 2–3 条，按相关性降序。

---

### 3. Label

**验证重点**：标签添加/修改（`tags` 为 JSON array）

```json
{
  "assertions": [
    {
      "name": "tags_added_json",
      "select": {
        "from": "memory",
        "where": [
          "deleted=0",
          "id=:id",
          "EXISTS (SELECT 1 FROM json_each(tags) WHERE value LIKE :tag)"
        ]
      },
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1", "tag": "%新标签%"}
    }
  ],
  "ranking": null
}
```

---

### 4. Update

**验证重点**：字段更新（文本或结构化列）

```json
{
  "assertions": [
    {
      "name": "field_updated_text",
      "select": {
        "from": "memory",
        "where": ["deleted=0", "id=:id", "text LIKE :new_content"]
      },
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1", "new_content": "%更新后内容%"}
    }
  ],
  "ranking": null
}
```

若更新 `subject/topic/location`，改用对应列 `LIKE :val`。

---

### 5. Delete

**验证重点**：软删除

```json
{
  "assertions": [
    {
      "name": "soft_deleted",
      "select": {"from": "memory", "where": ["deleted=1", "id=:id"]},
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1"}
    },
    {
      "name": "not_in_active",
      "select": {"from": "memory", "where": ["deleted=0", "id=:id"]},
      "expect": {"op": "==", "value": 0},
      "params": {"id": "1"}
    }
  ],
  "ranking": null
}
```

---

### 6. Promote

**验证重点**：权重提升

```json
{
  "assertions": [
    {
      "name": "weight_increased",
      "select": {
        "from": "memory",
        "where": ["deleted=0", "id=:id", "weight >= :min_weight"]
      },
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1", "min_weight": "0.7"}
    }
  ],
  "ranking": null
}
```

---

### 7. Demote

**验证重点**：权重降低/归档

```json
{
  "assertions": [
    {
      "name": "weight_decreased",
      "select": {
        "from": "memory",
        "where": ["deleted=0", "id=:id", "weight <= :max_weight"]
      },
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1", "max_weight": "0.3"}
    }
  ],
  "ranking": null
}
```

---

### 8. Lock

**验证重点**：锁定状态（无 `locked` 列，使用 `lock_mode` 判定）

```json
{
  "assertions": [
    {
      "name": "record_locked",
      "select": {
        "from": "memory",
        "where": ["deleted=0", "id=:id", "COALESCE(lock_mode,'') <> ''"]
      },
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1"}
    }
  ],
  "ranking": null
}
```

---

### 9. Merge

**验证重点**：主记录存在，子记录软删除（可选谱系）

```json
{
  "assertions": [
    {
      "name": "primary_exists",
      "select": {"from": "memory", "where": ["deleted=0", "id=:primary_id"]},
      "expect": {"op": "==", "value": 1},
      "params": {"primary_id": "1"}
    },
    {
      "name": "children_merged",
      "select": {"from": "memory", "where": ["deleted=1", "id IN (:child_ids)"]},
      "expect": {"op": ">=", "value": 2},
      "params": {"child_ids": ["2","3"]}
    }
  ],
  "ranking": null
}
```

（可选）谱系：主记录包含子ID
`"EXISTS (SELECT 1 FROM json_each(lineage_children) WHERE value IN (:child_ids))"`

---

### 10. Split

**验证重点**：生成多条（可选原记录软删/谱系）

```json
{
  "assertions": [
    {
      "name": "multiple_records",
      "select": {"from": "memory", "where": ["deleted=0"]},
      "expect": {"op": ">", "value": 1}
    },
    {
      "name": "original_deleted",
      "select": {"from": "memory", "where": ["deleted=1", "id=:id"]},
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1"}
    }
  ],
  "ranking": null
}
```

---

### 11. Expire

**验证重点**：过期时间设置（可选动作/原因）

```json
{
  "assertions": [
    {
      "name": "expire_time_set",
      "select": {"from": "memory", "where": ["deleted=0", "id=:id", "expire_at IS NOT NULL"]},
      "expect": {"op": "==", "value": 1},
      "params": {"id": "1"}
    }
  ],
  "ranking": null
}
```

---

### 12. Summarize

**验证重点**：源记录存在（不校验摘要文本）

```json
{
  "assertions": [
    {
      "name": "source_records_exist",
      "select": {"from": "memory", "where": ["deleted=0"]},
      "expect": {"op": ">=", "value": 1}
    }
  ],
  "ranking": null
}
```

（如系统将摘要写回，可额外断言 `type='summary'`。）

---

## 💡 Assertion 设计原则

### 1) 关键词提取

* 从 IR 的 `payload.text`、`args.set.*`、或 `tags` 中抽 1–2 个稳健词，避免过长短语。
* 用 `LIKE :keyword`；评测器会对 `%`、`_` 做转义。

### 2) 参数化查询

* **必须**使用 `:placeholder`，禁止将常量直接拼进 SQL。
* `IN` 参数用数组：`"where": ["id IN (:ids)"]`，`"params": {"ids": ["2","3"]}`。

### 3) ID 引用

* 仅使用**逻辑 ID**（"1"…"N"），由评测器映射到真实自增 `id`。
* Ranking 的 `gold_ids` 与断言 `:id`/`:ids` 都遵循此规则。

### 4) 合理验证点

* 只验证操作核心效果；对 LLM 生成内容（如具体摘要文本）不做强约束。
* 边界条件使用 `>=`/`<=` 替代过严的 `==`（除非有确定值）。

---

## ⚠️ 重要约束

1. **输出格式**：只输出 JSONL，不要任何额外文字
2. **字段完整**：必须包含 `assertions`、`ranking`、`triggers`（`meta` 可选）
3. **保持原样**：不得修改 `id`、`class`、`nl`、`prerequisites`、`schema_list` 等
4. **ranking 规则**：

   * Retrieve 操作必须有 `ranking`，`assertions` 为空数组
   * 其他操作 `ranking=null`
   * `allow_extra=false` 时，top-k 仅允许 gold
   * 若实际返回 < k，以实际返回长度评估
5. **triggers**：通常设为 `[]`
6. **SQL 方言**：默认 `sqlite`；如需 `postgres`，务必在 `expected.meta.dialect` 指定

---

## 📤 输出要求（严格遵守！）

**格式要求**：

1. **只输出一个 JSON 对象**（添加了 `expected` 的完整样本）
2. **不要添加任何说明文字、注释或 markdown 标记**
3. **不要使用 `json` 代码块**
4. **不要格式化**，所有内容在**一行**
5. **确保 JSON 正确可解析**
6. **不要输出多个 JSON 对象**

**正确示例**：

```
{"id":"t2m-001","class":{...},"nl":{...},"prerequisites":[...],"schema_list":[...],"init_db":null,"expected":{"assertions":[...],"ranking":null,"triggers":[],"meta":{"dialect":"sqlite","eval_time_utc":"2025-10-14T00:00:00Z"}},"notes":"..."}
```

**错误示例**：

````
# ❌ 添加了说明文字
这是生成的结果：
{"id":"..."}

# ❌ 使用了代码块
```json
{"id":"..."}
````

# ❌ 输出了多个对象

{"id":"..."}
{"id":"..."}

````

---

## 🎬 开始生成

### 输入数据
```json
{test_samples_jsonl}
````

### 任务

为上述测试样本添加 `expected` 字段，生成完整的测试用例（JSONL格式）。

**输出要求**：

1. JSONL 格式（每行一个 JSON 对象）
2. 添加 `expected` 字段（assertions、ranking、triggers，可选 meta）
3. 保持其他字段不变
4. 数量与输入一致
5. 严格遵循以上规范

---

⚠️ **现在开始生成！直接输出 JSON，不要任何其他内容。**

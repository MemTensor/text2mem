# Stage 3: Expected results generation (test validation refinement)

## 🎯 Core Objectives

You are a **Text2Mem test validation expert**. Your task is to add **expected fields** to the test samples generated in Stage 2 to make them complete, executable, and verifiable test cases.

---

## 📋 What you"ll do.

Add the `expected` field to each test sample contained:

1. ✅ **assertions** - SQL assertions that validate the actual effect of the operation
2. ✅ **ranking** - Retrieve result ranking validation (Retrieve operation only)
3. ✅ **triggers** - time triggers (usually empty)
4. ✅ **meta** - **must contain** evaluation meta information: SQL dialect/evaluation time/retrieve step index

**No modifications are required**:

** ❌ `id`, `class`, `nl`, `prerequisites`, `schema_list`, `init_db`, `notes` fields - Keep Stage 2 as is!

---

## ⏰ Virtual review time (important!)

**Fixed virtual evaluation time must be used for all test samples**: `2025-10-21T00:00:00Z`

This is the virtual "current time" of the test, make sure:
- ✅ Relative time queries ("last week", "last 30 days") are reproducible
- ✅ Test results are not affected by actual runtime
- ✅ The timestamp in Prerequisites matches the query time range.

**Must be set in expected.meta**:
```json
{
  "expected": {
    "meta": {
      "eval_time_utc": "2025-10-21T00:00:00Z", // ⚠️ fixed to use this time
      "dialect": "sqlite", { "step_index": 0
      "step_index": 0
    }
  }
}
```

---

## 🗄️ Evaluation Database Contracts (Aligning Real DDLs)

**SQL dialect**: default **SQLite 3**; if using Postgres, specify in `expected.meta.dialect="postgres"`.
**Table**: `memory` (fields and meanings aligned to DDL, key fields below)

* Primary key and content: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `text TEXT`, `type TEXT`
* structured attributes: `subject TEXT`, `time TEXT`, `location TEXT`, `topic TEXT`
* Tags and extensions: `tags TEXT` (JSON array), `facets TEXT` (JSON object with `{subject,time,location,topic}`)
* Importance: `weight REAL`.
* embedding: `embedding TEXT` (JSON array), `embedding_dim INTEGER`, `embedding_model TEXT`, `embedding_provider TEXT`
* lifecycle: `source TEXT`, `auto_frequency TEXT`, `next_auto_update_at TEXT`, `expire_at TEXT`, `expire_action TEXT`, `expire_reason TEXT`
* Locks: `lock_mode TEXT`, `lock_reason TEXT`, `lock_policy TEXT`, `lock_expires TEXT`
* Genealogy: `lineage_parents TEXT` (JSON array of IDs), `lineage_children TEXT` (JSON array)
* Permissions: `read_perm_level TEXT`, `write_perm_level TEXT`, `read_whitelist TEXT` (JSON array), `read_blacklist TEXT`, `write_whitelist TEXT`, `write _blacklist TEXT`.
* Marker: `deleted INTEGER DEFAULT 0`.

**JSON Access Conventions**

* SQLite:

  * `facets.time` → `JSON_EXTRACT(facets,"$.time") `
  * `tags` contains a value → `EXISTS (SELECT 1 FROM json_each(tags) WHERE value LIKE :tag) `
  * `lineage_*` contains some id → `EXISTS (SELECT 1 FROM json_each(lineage_children) WHERE value = :child_id)`
* Postgres (when `meta.dialect="postgres"`):

  * `facets->>"time" `
  * `EXISTS (SELECT 1 FROM json_array_elements_text(tags) t(value) WHERE t.value LIKE :tag) `

**Time field prioritization **

* If the sample/retrieval involves a time window: ** prioritize the top-level `time` **; fall back to `facets.time` for null. Both are ISO8601 strings.

---

## 📊 Input format

Stage 2 output (JSONL), one test sample per line:

```jsonl
{"id": "t2m-en-direct-single-enc-001", "class":{...} , "nl":{...} , "prerequisites":[], "schema_list":[...] , "init_db":null, "notes":"..."}
```

---

## 📤 Output format

⚠️ **Must output JSONL directly** (one full test sample per line)

```jsonl
{"id": "t2m-en-direct-single-enc-001", "class":{...} , "nl":{...} , "prerequisites":[], "schema_list":[...] , "init_db":null, "expected":{"assertions":[...] , "ranking":null, "triggers":[], "meta":{"dialect": "sqlite", "eval_time_utc": "2025-10-21T00:00:00Z", "step_index":0}}, "notes":"..."}
```

**Formatting Requirements**:

* ✅ One full JSON object per line
* ✅ New `expected` field only (with assertions, ranking, triggers, optional meta)
* ✅ Leave other fields unchanged
* ✅ Don"t have any explanatory text or markdown tags.
* ✅ Don"t wrap JSON Array with `[` and `]`.

---

## 🏗️ Expected Field Structure

```json
{
  "expected": {
    "assertions": [
      {
        "name": "assertion_name",
        "select": {
          "from": "memory",
          "where": ["deleted=0", "text LIKE :keyword"],
          "agg": "count"  // Optional: count/sum/avg/min/max, default is count
        },
        "expect": {"op": "==", "value": 1}, // ==|>=|>|<|<=|!=
        "params": {"keyword": "%keyword%", "id": "1"}
      }
    ],
    "ranking": {                  // Only needed for Retrieve, others are null
      "gold_ids": ["1","3"],     // Represented by “logical ID” (see ID mapping below)
      "min_hits": 1,             // Minimum number of hits required
      "allow_extra": true,       // Allow non-gold in top-k results
      "k": 5                     // Evaluate top-k (if less than k returned, evaluate based on actual quantity)
    },
    “triggers”: [],               // Time triggers (usually empty)
    “meta”: {                     // **Must include**: evaluation metadata
      “dialect”: “sqlite”,        // sqlite | postgres
      “eval_time_utc”: “2025-10-21T00:00:00Z”,  // ⚠️ Fixed virtual evaluation time to use this 
      “step_index”: 0             // Specify which step to evaluate during multiple retrievals 
    }
  }
}
```

---

## 🔢 ID Mapping Rules (Mandatory)

* **Logical IDs of Prerequisites**: Mapped in the order they appear as `"1","2","3"...` (unrelated to table"s auto-increment `id`).
* `ranking.gold_ids` and all assertions" `:id`/`:ids` parameters **must use logical IDs**. The evaluator will record the real auto-increment id of inserted rows when loading prerequisites and complete the mapping.
* `schema_list[].target.ids` (if any) also point to these logical IDs.

---

## 🕒 Temporal Semantics

* Evaluation time reference: `expected.meta.eval_time_utc` (if not provided, use evaluator system time UTC).
* If retrieval includes a time window (e.g., `time_from/time_to`), it constrains `memory.time`; if empty then fallback to `facets.time`.
* Ranking is solely based on relevance and expected IDs; no secondary judgment on time; the time window only affects the candidate set.

## 📚 12 Types of Assertion Design Guidelines (Aligning with Real Table Structure)

### 1. Encode

**Validation Focus**: Record creation, content saving, tag storage (JSON)  
**Typical assertions**:

```json
{
  "assertions": [
    {
      "name": "record_created",
      "select": {"from": "memory", "where": ["deleted=0"]},
      "expect": {"op": ">=", "value": 1},
      "_comment": "At least one record created"
    },
    {
      "name": "content_saved",
      "select": {"from": "memory", "where": ["deleted=0", "text LIKE :keyword"]},
      "expect": {"op": "==", "value": 1},
      "params": {"keyword":"%keyword%"}
    },
    {
      "name":"tags_saved_json",
      “select”: {
        “from”: “memory”,
        “where”: [
          “deleted=0”,
          “EXISTS (SELECT 1 FROM json_each(tags) WHERE value LIKE :tag)”
        ]
       },
       “expect”: {“op”: ”>=”, ”value”: 1},
       ”params”: {“tag”: ”%tag_name%”}
     }
   ],
   ”ranking”: null
}
```

**Keyword Extraction**: Extract 1-2 words from `schema_list[0].args.payload.text`.

---

### 2. Retrieve

**Validation Focus**: Ranking of retrieval results  
**Typical expected output**:

```json
{
  "assertions": [],
   "ranking": {
     "gold_ids": ["1", "3"],
     "min_hits": 1,
     "allow_extra": true,
     "k":5
   }
}
```

**Design of gold_ids:** Select the top relevant 2-3 entries from prerequisites related to the query in descending order of relevance.

---

### 3. Label

**Validation Focus:** Adding/modifying tags (`tags` as JSON array)

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
           "EXISTS (SELECT 1 FROM json_each(tags) WHERE value LIKE :tag)"
         ]
       },
       "expect": {"op": "==", "value": 1},
       "params": {"id": "1", "tag": "%new_tag%"}
     }
   ],
   "ranking": null
}
```

---

### 4. Update

**Validation Focus:** Field updates (text or structured columns)

```json
{
   "assertions":[ 
     { 
        "name":"field_updated_text",
        "select":
            {"from":"memory","where":["deleted=0","id=:id","text LIKE :new_content"]}
            ,
            expect:{"op":"==","value":1}, 
            params:{"id":"1", new_content:"%updated_content%" } 
          } 
        ], 
        ranking:null 
}   
```
If updating `subject/topic/location`, use corresponding column `LIKE :val`.


### 5. Delete

**Verification focus**: Soft delete

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

**Verification focus**: Weight increase

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

**Verification focus**: Weight reduction/archiving

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

**Verification key points**: Locked status (no `locked" column, use`lock_mode" to determine)

```json
{
  "assertions": [
    {
      "name": "record_locked",
      "select": {
        "from": "memory",
        "where": ["deleted=0", "id=:id", "COALESCE(lock_mode,"") <> """]
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

**Verification key points**: The main record exists, and the sub-record is soft deleted (optional pedigree)

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

(Optional) Pedigree: The main record contains the child ID
`"EXISTS (SELECT 1 FROM json_each(lineage_children) WHERE value IN (:child_ids))"`

---

### 10. Split

**Verification key points**: Generate multiple records (optional soft deletion of original records/pedigree)

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

**Verification focus**: Expiration time setting (optional action/reason)

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

**Verification key points**: The source record exists (the summary text is not verified)

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

(If the system writes the summary back, you can additionally assert"type="summary".）


## 💡 Assertion Design Principles

### 1) Keyword Extraction

* Extract 1-2 robust words from the IR's `payload.text`, `args.set.*`, or `tags`, avoiding overly long phrases.
* Use `LIKE :keyword`; the evaluator will escape `%` and `_`.

### 2) Parameterized Queries

* **Must** use `:placeholder`; direct concatenation of constants into SQL is prohibited.
* Use an array for `IN` parameters: `"where": ["id IN (:ids)"]`, `"params": {"ids": ["2","3"]}`.

### 3) ID Reference

* Only use **logical IDs** ("1"…"N"), which are mapped to real auto-incrementing `id` by the evaluator.
* The ranking's `gold_ids` and assertion `:id`/`:ids` must follow this rule.

### 4) Reasonable Validation Points

* Validate only the core effects of operations; do not impose strict constraints on LLM-generated content (such as specific summary text).
* Use `>=`/`<=` for boundary conditions instead of overly strict equality (`==`) unless there is a definite value.

---

## ⚠️ Important Constraints

1. **Output Format**: Output only JSONL, no additional text
2. **Field Completeness**: Must include `assertions`, `ranking`, and `triggers` (optional for `meta`)
3. **Maintain Originality**: Do not modify fields like `id`, `class`, `nl`, `prerequisites`, or any items in the list
4. **Ranking Rules**:

   * Retrieve operations must have a non-empty array for 'ranking', with empty arrays for 'assertions'
   * Other operations should set ranking to null
   * When setting 'allow_extra=false', top-k should only allow gold entries
   * If actual returns < k, evaluate based on actual return length
5. **Triggers**: Typically set to `[ ]`
6. **SQL Dialect**: Default is sqlite; if postgres is needed, specify it in expected.meta.dialect

---

## 输出 Output requirements (strictly abide by!）

**Format requirements**：

1. **Only one JSON object is output** (a complete sample of `expected` is added)
2. **Do not add any explanatory text, comments, or markdown marks**
3. **Do not use the 'json` code block**
4. **Do not format**, all content is on the **line**
5. **Make sure the JSON is correct and resolvable**
6. **Do not output multiple JSON objects**

**Correct example**：

```
{"id":"t2m-001","class":{...},"nl":{...},"prerequisites":[...],"schema_list":[...],"init_db":null,"expected":{"assertions":[...],"ranking":null,"triggers":[],"meta":{"dialect":"sqlite","eval_time_utc":"2025-10-14T00:00:00Z"}},"notes":"..."}
```



**Error example**：

````
# ❌ Added explanatory text
This is the generated result：
{"id":"..."}

# ❌ Code block is used
```json
{"id":"..."}
````

# ❌ Multiple objects are output

{"id":"..."}
{"id":"..."}

````

---

## 🎬 Start to generate

### Input data
```json
{test_samples_jsonl}
````

### Task

Add the `expected` field to the above test sample to generate a complete test case (JSONL format).

**Output requirements**：

1. JSONL format (one JSON object per line)
2. Add the `expected' field (assertions, ranking, triggers, optional meta)
3. Keep other fields unchanged
4. The quantity is consistent with the input
5. Strictly follow the above specifications

---

️️**Start generating now!Output JSON directly, without any other content.**
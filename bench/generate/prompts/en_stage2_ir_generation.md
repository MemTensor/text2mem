#Stage 2* IR Scheme generation

## 🎯 Mission objectives

Convert the Stage 1 natural language sample to **Text2Mem IR Scheme (intermediate representation)**.

**Core points：**

1.  准确 Accurately map NL instructions → IR operations
2.  生成Generate complete 'prerequisites` (IR array ≠description)
3.  多样化 Diversified'target` (priority search/filter)
4.  支持 Support workflow (2-5 step logic chain)
5.  时间 Time consistency (fixed virtual time)
6.  知识Knowledge extraction (information → knowledge unit)

---

## Memory extraction standard (must be followed)

### Level 1 Atomization split (required)

* Mixed information → multiple'ENC.Encode`, each one contains only 1 independent memory point.
* 错误 Error: Save the entire paragraph at once ✅ Correct: Multiple Encodes are labeled separately, but multiple memories need to be independent of each other.

### Level 2 type annotation (recommended)

* `args.Add to the 'load` field：

  * `knowledge_type`: `"fact"|"constraint"|"requirement"|"decision"|"action"|"risk"|"metric"|"question"`
  *'source`: source of information (person/document/meeting)
  *'context`: short context description
* `args.type 'fixed` "knowledge"` (distinguish between `"note"`)

### Level 3 metadata extraction (recommended)

* Structured fields are placed in 'facets` to support filtering.
  example：

  ```json
  {"amount":2000000,"currency":"CNY"}
  {"duration_months":2}
  {"window":{"start":"2025-11-01","end":"2025-11-11"}}
  {"certainty":"confirmed"}
  ```

---

## ⏰Time rules (fixed virtual time)

* Virtual "now”:`2025-10-21T00:00:00Z`
* Relative time (including start but not end)：

| Expression | Time range |
| ----------- | ------------------------ |
| Yesterday | [2025-10-20, 2025-10-21) |
| Last 7 days / Last week / [2025-10-14, 2025-10-21) |
|Last 30 days | [2025-09-21, 2025-10-21) |

**Rules：**

* All'prerequisites.args.time` must be in the query window；
* Top layer'args.time` is used for filtering, and 'facets` can retain business time.

###️️ time_range format specification (important!)

```json
// 正确 Correct: relative time (flat structure)
{"time_range": {"relative": "last", "amount": 7, "unit": "days"}}

// 正确 Correct: absolute time (flat structure)
{"time_range": {"start": "2025-10-01T00:00:00Z", "end": "2025-10-21T00:00:00Z"}}

// 错误 Error: Do not use nested absolute fields!
{"time_range": {"absolute": {"start": "...", "end": "..."}}}
```

**time_range field description**：

| Format | Required fields | Example |
|------|---------|------|
|**Relative time * * |'related`,`amount`,`unit` |'{"relative": "last", "amount":7, "unit": "days"}`|
|**Absolute time ** |'start`,'end`|'{"start": "2025-10-01T00:00:00Z", "end": "2025-10-21T00:00:00Z"}`|

**️️ Note**: time_range uses a **flat structure**, the fields are directly in the time_range object, ** Do not**nest absolute/relative child objects!

---

## Pr Prerequisites generation specification

| Operation type | Is it required | Quantity | Requirements |
| --------------------- | ---- | ----- | --------------- |
| Encode | No | – | No pre-required |
| Retrieve / Summarize / Yes / 3-5 items / Atomization + Typing + Structure |
| STO (Update / Label, etc.) / Yes / 1-3 / Same as above |

**Supplementary requirements**

*'tags` are accurate (such as "budget”“ "compliance”, “online window")
*Different'times` can be used for different knowledge points (interval 2-5 minutes)
* Each Encode contains the fields'knowledge_type`'source`'context` and 'facets`

---

##️️ Output format (strict)

Output 1 JSON object per sample：

```json
{
  "nl":{"zh":"<natural language Instruction>"},
  "context": "<input context>",
  "classification":{"instruction_type":"...","structure":"...","lang":"..."},
  "scenario_info":{"scenario":"...","operation":"...","style":"...","topic":"..."},
  "prerequisites":[{ "stage":"ENC","op":"Encode","args":{...} }],
  "schema_list":[{ "stage":"RET|SUM|STO|...","op":"...","target":{...},"args":{...} }]
}
```

---

## 质量 Quality inspection list

* [] Atomization: only 1 knowledge point per Encode
*[]Typing: contains'knowledge_type`
* [] Attribution: contains'source`,'context`
* [] Structure: key values/time enter 'facets`
*[] Accurate label + searchable
* [] The time is in the query window
* [ ] `schema_list.target.filter` can hit`prerequisites`
*[] The output is only JSON, no description, no code block

---

## 输入 Input placeholder (replaced by upstream)

```json
{
  "instruction":"{instruction}",
  "context":"{context}",
  "classification":{"instruction_type":"{instruction_type}","structure":"{structure}","lang":"{lang}"},
  "scenario_info":{"scenario":"{scenario}","operation":"{operation}","style":"{style}","topic":"{topic}"}
}
```

---

## 示例 Example (meeting minutes → Retrieve)

```json
[
  {
    "nl":{"zh": "Find the minutes of last week's meeting on product design"},
    "context": "The user is advancing the design review of the new version",
    "classification":{"instruction_type":"direct","structure":"single","lang":"zh"},
    "scenario_info": {"scenario": "meeting_notes", "operation": "retrieve", "style": "concise", "topic": "product design"},
    "prerequisites":[
      {"stage": "ENC", "op":"Encode","args":{"workload":{"text":"Product design review meeting: confirm the new version of the interaction plan","knowledge_type": "fact", "source":"meeting minutes", "context":"Design review-second time"}, "type": "knowledge", "tags":["Meeting", "Product Design","Review"], "time":" 2025-10-18T10:00:00Z","facets":{"phase":"review"}}},
      {"stage": "ENC", "op":"Encode","args":{"workload":{"text":"Interactive changes need to be released before October 25th in high fidelity","knowledge_type": "restriction", "source": "product manager", "context":"Design schedule"}, "type": "knowledge", "tags":["Meeting","Product Design", "deadline"], "time":" 2025-10-15T14:00:00Z","facets":{"deadline":"2025-10-25T00:00:00Z"}}},
      {"stage": "ENC", "op": "Encode","args":{"workload":{"text":"Availability test sample size needs to be ≥20","knowledge_type": "requirement", "source": "user research", "context":"availability test"}, "type": "knowledge", "tags":["Conference", "Product Design", "availability"], "time":" 2025-10-14T09:30:00Z","facets":{"sample_size":20}}}
    ],
    "schema_list":[
      {"stage":"RET","op": "Retrieve","target":{"filter":{"has_tags":["Conference","product design"],"time_range":{"relative": "last","amount":7, "unit":"days"}}}}
    ]
  }
]
```

---

## Structure classification

| Type | Feature | Description |
| -------- | ------- | ------------------------------ |
| single | only 1 operation | operation='scenario_info.operation` |
| workflow | 2-5 operations | multi-step logical chain, step id mutual reference |

---

# 📚 Text2Mem 12 Operations Quick Reference (Including Parameter Descriptions)

---

## 🧩 ENC Stage (Create)

### 1️⃣ Encode — Create New Record

```json
{
  "stage": "ENC",
  "op": "Encode",
  "args": {
    "payload": {"text": "Meeting content..."},
    "type": "note",
    "tags": ["meeting", "product"],
    "facets": {
      "subject": "Product Discussion",
      "time": "2024-11-15T10:00:00Z"
    }
  }
}
```

| Field                | Type            | Required | Description                             |
| ------------------- | ------------- | -------- | -------------------------------------- |
| `stage`             | string        | ✅       | Fixed as `"ENC"`                       |
| `op`                | string        | ✅       | Fixed as `"Encode"`                    |
| `args.payload.text` | string        | ✅       | Main text content (recommended to use text, not structured)   |
| `args.type`         | string        | ✅       | Record type, such as `note`, `task`, or `event`         |
| `args.tags`         | array(string) | Optional  | Tags, recommended to be between 2–5                          |
| `args.facets`       │ object        │ Optional   │ Structured metadata, such as subject/time/location/topic     |
| `args.source`       │ string        │ Optional   │ Source description (e.g., “meeting notes”, “web excerpt”)                 |

**Key Points**:

* No need for a `target`.
* No need for prerequisites.
* The value of `payload.text` should be standardized text (not using JSON structure).

---

## 🔍 RET Stage (Retrieve / Summarize)

### 2️⃣ Retrieve — Retrieve Records

```json
{
  "stage": "RET",
  "op": "Retrieve",
  "target": {
    "search": {  // ⭐ 70% use search
      "intent": {"query": "Product design discussion"},
      "overrides": {"k": 10, "alpha": 0.7}
    }
  },
  "args": {"include": ["id", "text", "tags"]}
}
```

| Field                             | Type            | Required | Description                  |
| --------------------------------- | ---------------- | -------- | ---------------------------- |
| `stage`                           | string          | ✅       | Fixed as `"RET"`            |
| `op`                              | string          | ✅       | Fixed as `"Retrieve"`       |
| `target.search.intent.query`      | string          | ✅       | Natural language search keyword|
| `target.search.overrides.k`       | integer         | Optional   | Maximum number of returns (default is 10)|
| `target.search.overrides.alpha`   | number(0–1)     | Optional   | Mixed retrieval ratio (0=keyword, 1=semantic)|
| `args.include`                    |

array(string)   |

Optional   |

Specify the whitelist of returned fields           |

**Key Points**:

* Prerequisites: 3–5 records (2–3 relevant + 1–2 irrelevant).
* You can also use `"target.filter"` or `"target.ids"`, but diversification is recommended.

---

### 3️⃣ Summarize — Summarize Content

```json
{
  "stage": "RET",
  "op": "Summarize",
  "target": {
    "search": {   // ⭐60% use search
      		intent”: {“query”: “Meeting content”},
      		“overrides”: {“k”:10},
      		“limit”:10
    }
  },
    “args”: {
    “focus”: “action items”,
    “max_tokens”:200
    }
}
```

| Field                                      || Type       || Required || Description                               ||
|- |- |- |- |- 
|| stage                       || string     || ✅       || Fixed as `"RET"` ||
|| op                           || string     || ✅       || Fixed as `"Summarize"` ||
|| target                    　       　|| object 　    ||

✅ 　　 

||

Target selection, can be used with search/filter/ids ||

|| args.focus              　　       　|| string 　 　 ||

Optional 

|

Focus direction for summary                   ||

|| args.max_tokens             　　   　|| integer 　  

||

Optional 

|

Maximum summary length (default is256)             ||

|| meta.lang                     　　    　||
string 　 　   

||

Optional 

|

Output language (`zh`/`en`)           |

**Key Points**:

* There should be **2-4 summarizable records** as prerequisites.
* Summarize is a composite operation in the RET stage and can be combined with Retrieve.

---

## ⚙️ STO Stage (Store / Modify)

---

### Label — Tagging

```json
{
    "stage":"STO",
    "op":"Label",
          ” target ” : {
    filter: { // ⭐50% use filter 
    "type":"note", 
    "time_range":{"relative":"last","amount ":7,"unit ":"days"}
}} ,
	args:{
	tags:["Important"],
	mode:"add"
}}
``` 

| Field            | Type          | Required      | Description                             |
| ---------------- | ------------- | --------------| --------------------------------------- |
| `stage`          | string        | ✅            | Fixed value `"STO"`                    |
| `op`             | string        | ✅            | `"Label"`                              |
| `target.filter`  | object        | ✅            | Target filtering conditions              |
| `args.tags`      | array(string) | ✅ (or facets)| Tags to be added or replaced             |
| `args.facets`    | object          | Optional      | Structured metadata to add/modify       |
| `args.mode`      | string          | Optional      | Operation mode: `add`/`replace`/`remove` (default is add)  |

**Key Points**:

* Label is a metadata modification operation.
* Supports batch label modifications.

---

### 5️⃣ Update — Update Record

```json
{
  "stage": "STO",
  "op": "Update",
  "target": {
    "filter": {"has_tags": ["To be updated"]}
  },
  "args": {
    "set": {
      "text": "Summary of the updated content",
      "subject": "Updated subject"
    }
  }
}
```

| Field                | Type            | Required | Description       |
| -------------------- | ----------------| ---------| ------------------|
| `target`             | object          | ✅       | Specify the record to update |
| `args.set.text`     | string          | Optional | Updated text      |
| `args.set.tags`     | array(string)   | Optional | Modify tags       |
| `args.set.subject`  | string          | Optional | Updated subject   |
| `args.set.weight`   | number(0–1)     | Optional | Adjust importance |

**Key Points**:

* At least one field must be included in `set`.
* Prerequisites usually involve 1-2 records.

---

### 6️⃣ Promote — Increase Importance

```json
{
  "stage": "STO",
  "op": "Promote",
  "target": {"filter": {"has_tags":["Urgent"]}},
  "args":{
    "weight_delta" :0.3,
    “remind”:{“rrule”:“FREQ=WEEKLY;BYDAY=MO”},
    “reason”:“Periodic review”
   }
}
```

| Field                                                                                                        	| Type          		| Required 		| Description       		              	   	  |
|- - - - - - - - -- – -- – -- – -- – -- – --- – --- – ---–---–---–---–---–---—- |-|-|-|
│ `target`              │ object         │ ✅        │ Specify the record to promote     │
│ `args.weight`        │ number(0-1)   │ One of three options│ Absolute weight                                                                               ──┐ 
│ args.weight_delta     │ number         │ One of three options│ Relative increment                                                         ──┘  
│ args.remind           │ object         │ One of three options│ Set reminder rules                                                  ───┐ 
│ args.reason           │ string         │ Optional         ░░░░░░Reason for promotion                          ────────┘ 

---

###7️⃣ Demote — Downgrade/Archive

```json
{
"stage":"STO", 
"op":"Demote", 
"target":
{ 
"filter":{"time_range":{"relative":"last","amount ":90,"unit ":"days"}}}, 
"args":{"archive ":true,"reason ":"Expired archive"}
}
```
    
||Field ||Type ||Required ||Description ||
|-|-|- |- |-|
|| target ||object ||✅||Target selection||
|| args.archive ||boolean ||One of three options|| Archive ||
|| args.weight ||number ||One of three options|| Absolute value reduction ||
|| args.weight_delta ||number ||=oneofthreeoptions|||Relative decrease||
|| args.reason ||=string |=Optional = Reason for demotion explanation =|

---

### 8️⃣ Merge — Merge Records

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

| Field                       | Type            | Required | Description                             |
| --------------------------- | --------------- | -------- | --------------------------------------- |
| `target.ids`                | array(string)   | ✅       | Sub-records to be merged               |
| `args.strategy`             | string          | ✅       | Merging strategy (currently only supports `merge_into_primary`) |
| `args.primary_id`           | string          | ✅       | Primary record ID                       |
| `args.soft_delete_children` | boolean         | Optional  | Whether to soft delete sub-records (default true) |

---

### 9️⃣ Split — Split Records

```json
{
  "stage": "STO",
  "op": "Split",
  "target": {"ids": ["1"]},
  "args": {
    "strategy": "by_chunks",
    "params": {"chunk_size": 500, “num_chunks”:3},
    “inherit_all”: true
   }
}
```

| Field               | Type          | Required | Description                                      |
| ------------------ | ------------- | -------- | ------------------------------------------------ |
| `target.ids`       | array(string) | ✅        | Records to be split                             |
| `args.strategy`    | string           | ✅        | Splitting method (`by_sentences` / `by_chunks` / `custom`) |
| `args.params`      | object         | ✅        | Parameters for each strategy                     |
| `args.inherit_all` | boolean       | Optional  | Whether to inherit all metadata (default true)  

---

### 🔟 Delete — Delete Record

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

| Field              | Type     | Required | Description         |
| ----------------- | ------- | -------- | ------------------- |
| `target`          | object  | ✅       | Target for deletion   |
| `args.soft`       | boolean | Optional | Whether to soft delete (default true) |
| `args.reason`     | string  | Optional | Reason for deletion   |
| `args.time_range` | object  | Optional | Time range filter      |

---

### 11️⃣ Lock — Lock Record

```json
{
  "stage": "STO",
  "op": "Lock",
  "target": {"ids": ["1"]},
  "args": {
    "mode": “read_only”,
    “policy”: {“expires”: “2026-01-01T00:00:00Z”}
   }
}
```

| Field                  | Type              | Required | Description                                   |
| --------------------- | ----------------- | -------- | --------------------------------------------- |
| `target.ids`          | array(string)     | ✅       | Records to be locked                          |
| `args.mode`           | string            | Optional  | Mode: `read_only` or `append_only` (default is read_only) |
| `args.reason`         | string            | Optional  | Explanation for the lock reason               |
| `args.policy.expires` | string(date-time)  | Optional  | Expiration time                               |

---

### 12️⃣ Expire — Set Expiration Policy

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

| Field             | Type               | Required | Description                                                  |
| ----------------- | ------------------ | -------- | ------------------------------------------------------------ |
| `target`          | object             | ✅       | Set target                                                   |
| `args.ttl`       | string(duration)   | One of two options   | Relative expiration time, e.g., `"P30D"`                     |
| `args.until`     | string(date-time)  | One of two options   | Absolute expiration time                                     |
| `args.on_expire` | string             | Optional      | Expiration behavior: `soft_delete` / `hard_delete` / `demote` / `anonymize` |

---

## 🎬 Generation Guide

### Processing Flow

1. **Identify structure type**
   - Check `classification.structure`
   
2. **For single sample**:
   - Generate **1 corresponding operation** based on `scenario_info.operation`
   - Must use the corresponding stage and op
   - Prefer using search/filter (instead of ids)
   
3. **For workflow sample**:
   - Generate **2-5 logically related operations** based on user instruction content
   - Ignore `scenario_info.operation` (for reference only)
   - Operation types can be freely chosen
   - Reference between steps using ids
   
4. **Build prerequisites**:
   - Encode: Not needed
   - Retrieve/Summarize: 3-5 items
   - STO operations: 1-3 items
   - Must be complete IR (with stage, op, args)
   
5. **Select target**:
   - Strictly follow the above ratio reference
   - Prefer search (retrieve)/filter (batch)
   - Reduce ids, avoid all
   
6. **Output format**:
    – JSONL (one JSON per line)
    – Complete fields (id, class, nl, prerequisites, schema_list, init_db, notes)

## 输出 Output specification

* Output 1 JSON object or array, no additional text/code block
* Single-line JSONL format
* ID rules：

  * single：`t2m-{lang}-{instruction_type}-single-{op}-{seq}`
  * workflow：`t2m-{lang}-{instruction_type}-workflow-wf-{seq}`

---

## 🚨 Common Errors and Fix Rules (⚠️ Must Read! Avoid Generating Errors)

Based on the error statistics from a large number of test samples, here are the **9 most common types of errors and their fixes**. Be sure to check before generating!

### 1️⃣ facets cannot be empty or only contain time ⭐⭐⭐

**Error Examples**:
```json
{"args": {"payload": {...}, "facets": {}}}  // ❌ Empty object
{"args": {"payload": {...}, "facets": {"time": "..."}}}  // ❌ Only time
```

**Correct Examples**:
```json
{"args": {"payload": {...}, "facets": {"certainty": "confirmed"}}}
{"args": {"payload": {...}, "facets": {"amount": 2000000, "currency": "CNY"}}}
{"args": {"payload\": {...}, \"facets\": {\"priority\": \"high\", \"status\": \"active\"}}}
```

**Rules**:
- ✅ facets must include at least one **business field**
- ✅ Recommended fields: `certainty`, `priority`, `status`, `category`, `amount`, `duration`, `deadline` etc.
- ❌ Do not only include `time` (time should use the top-level `time` field)
- ❌ Do not leave an empty object `{}`

---

### 2️⃣ time_range must use flat format ⭐⭐⭐

**Error Examples**:
```json
{"time_range': {'absolute': {'start': '...', 'end': '...'}}}  // ❌ Nested
{'time_range': {'relative': 'last', 'amount': 7}}  // ❌ Missing unit
{'time_range': {'start': '2025-10-01T00:00:00Z'}}  // ❌ Only start provided 
```

**Correct Examples**:
```json
{'time_range': {'relative':'last', 'amount' :7, 'unit':'days'}}   // ✅ Relative time 
{'time_range' :{‘start’:'2025 -10 -01 T00 :00 :00 Z','end':'2025 -10 -21 T00 :00 :00 Z'}}   // ✅ Absolute time 
```

**Rules:**  
- ✅ Prefer using the relative format (recommended)  
- ✅ Relative time must include: three fields: ‘relative’, ‘amount’, ‘unit’   
- ✅ Absolute time must include two fields: ‘start’, ‘end’    
- ❌ Do not use nested absolute objects  
- ❌ Do not provide only start or end


---

### 3️⃣ Promote must provide one of three parameters ⭐⭐⭐

**Error Examples**:
```json
{"op": "Promote", "args": {"priority": "high"}}  // ❌ priority is not a valid parameter
{"op": "Promote", "args": {"reason": "重要"}}  // ❌ only reason provided
```

**Correct Examples**:
```json
{"op": "Promote", "args": {"weight_delta": 0.3, "reason": "提升优先级"}}  // ✅ relative increment
{"op": "Promote", "args": {"weight": 0.8}}  // ✅ absolute weight
{"op": "Promote", "args": {"remind": {"rrule":"FREQ=WEEKLY;BYDAY=FR"}}}  // ✅ set reminder
```

**Rules**:
- ✅ Must provide at least **one of the following**:
  - `weight` - absolute weight (between 0 and 1)
  - `weight_delta` - relative increment (between -1 and 1, recommended: 0.2-0.3)
  - `remind` - reminder rule
- ✅ Recommended to use `weight_delta` (more natural)
- ❌ Do not only write `priority` or `reason`
- ✅ `reason` is an optional explanatory field that can be added

---

### 4️⃣ Update's set must contain valid fields ⭐⭐⭐

**Error Examples**:
```json
{"op":"Update","args":{"set:{}}}   // ❌ empty object 
{"op":"Update","args":{"set":{"note":"更新说明"}}}   // ❌ note is not a standard field 
{"op":"Update","args":{"set":{"progress_note":"..."}}}   // ❌ custom field 
```

**Correct Examples**:
```json
{"op":"Update","args":{"set":{"text":"更新后的内容"}}}   // ✅ update text 
{"op":"Update","args":{"set":{"subject":"新主题"}}}   // ✅ update subject 
{"op":"Update","args":{"set":{"tags":["已处理","重要"]}}}   // ✅ update tags 
{"op":"Update","args":{"set":{"weight:0.8}} }    //✅ update weight  
```

**Rules:**  
- ✅ The `set` must include at least one standard field:  
      - `text`: main text content  
      - `subject`: subject   
      - tags: array of tags    
      -weight: weight (0–1)     
             
    ▪️❌ Do not use non-standard fields (e.g., note, progress_note)    
    ▪️❌ Do not leave an empty object    

---  

###5️⃣ ids and tags must be in array format ⭐⭐  

***Error examples*** :   
``` json  
{“target”:{“ids”: “1,2,3” }}    　//❌ string    
{“target”:{“ids”:1 }}     　//❌ number      
{“ args ” : { “tags”: “重要” }}      　//❌ string       
 ```   

***Correct examples*** :     
 ``` json   
{“ target ” : { “ ids ”:[ “1”, “2”, “3” ] }}    　//✅ string array      
{“ args ” : { “tags”: [ “重要”, “紧急” ] }}     　//✅ string array        
{“ target ” : { “ ids ”:[“1”] }}       　//✅ single element also uses an array         
 ```

 ***Rules*** :
*	All ‘ids’ fields must be **string arrays:** `[‘1’, ‘2’]`
*	All ‘tags’ fields must be **string arrays:** `[‘tag1’, ‘tag2’]`
*	Do NOT use comma-separated strings.
*	Do NOT use numbers or single strings.
*	Even if there’s only one element, it should still be in an array:`[‘1’]`.


---

### 6️⃣ Stage and Op must match ⭐⭐

**Error Examples**:
```json
{"stage": "STO", "op": "Encode"}  // ❌ Encode should be ENC
{"stage": "ENC", "op": "Retrieve"}  // ❌ Retrieve should be RET
{"stage": "RET", "op": "Label"}  // ❌ Label should be STO
```

**Correct Mapping Table**:

| Op | Stage | Description |
|----|-------|-------------|
| `Encode` | `ENC` | Create record |
| `Retrieve`, `Summarize` | `RET` | Retrieval and summary |
| `Label`, `Update`, `Promote`, `Demote`, `Delete`, `Merge`, `Split`, `Lock`, `Expire` | `STO` | Storage management operations |

**Rules**:
- ✅ Strictly follow the mapping in the table above.
- ❌ Do not confuse stage and op.

---

### 7️⃣ Expire must use ttl or until ⭐⭐

**Error Examples**:
```json
{"op": "Expire", "args": {"time_delta": {"days": 90}}}  // ❌ time_delta not supported
{"op": "Expire", "args": {"duration": "90 days"}}  // ❌ duration not supported
{"op": "Expire", "args": {"ttl": "P90D", "until": "2026-01-01T00:00:00Z"}}  // ❌ cannot provide both at once
```

**Correct Examples**:
```json
{"op": "Expire", "args": {"ttl":"P90D"}}  // ✅ Relative expiration (ISO 8601 duration)
{"op":"Expire","args":{"until":"2026-01-15T00:00:00Z"}}   // ✅ Absolute expiration time 
{"op":"Expire","args":{"ttl":"P90D","on_expire":"soft_delete"}}   // ✅ With action 
```

**Rules**:
- ✅ Must provide one of the following **two options**:
    - 'ttl' - ISO 8601 duration format (e.g., `"P90D"` = 90 days)
    - 'until' - absolute time (ISO 8601 format)
- ✅ Optional 'on_expire' - expiration behavior (`soft_delete`,`hard_delete`,`demote`,`anonymize`)
- ❌ Do not use custom fields like 'time_delta', 'duration'
- ❌ Cannot provide both ttl and until at the same time.

---

### 8️⃣ Split strategy limited to three types ⭐

**Error Examples**
```json
{"op":"Split","args":{"strategy":"by_topics"}}   //❌ Not supported 
{"op":"Split","args":{"strategy":"by_paragraphs"}}   //❌ Not supported 
```

 **Correct Examples**
 ```json  
 {"op" : “Split”, “args” : {“strategy”: “by_sentences”, “params”: {“max_sentences”:3}}}
 {" op ": ” Split ", ” args ": {” strategy ": ” by_chunks ", ” params ": {” num_chunks ":3}}}
 {" op ":" Split "," args ":"{“strategy”: “custom”, “params”: {“delimiters”: [“\n\n”]}}}
 ```

 **Rules**
 -✅ Strategy can only be one of the following three types :
     - ‘by_sentences’ – split by sentences 
     - ‘by_chunks’ – split by chunks  
     - ‘custom’ – custom splitting   
     
 -✅ Must provide ‘params’ parameter.    
  
 -❌ Do not use other strategies.  

--- 

###9️⃣ Label must provide tags or facets ⭐⭐ 

 **Error Examples:**  
 ``` json   
{“ op ”:“ Label ”,“ args ”:{“ mode ”:“ add ”}}//❌ No tags   
{“ op ":" Label "," args ":"{} "//❌ Empty parameters    
 ```
 **Correct examples:**    
 ``` json   
{“ op ":" Label "," args ":"{tags":["重要"],"mode:"add" }}//✅ Add label      
{"" op "" :"Label,"" args "" :"{tags:["旧标签"],"" mode "" :"remove}" }/ /✅ Delete label       
{"" op "" :"Label,"" args "" :"{facets:{status:"done"},"mode:"add}"}/ /✅ Add facets        
 ```

 **Rules:**     
– Must provide either ’tags‘ or ’facets‘ (at least one)         
– ’mode‘ optional values: ’add‘(default), ’remove’, ’replace‘          
– Tags must be an array of strings           
– ❌ Do not leave empty parameters

---

### 🎯 Quick Check List

Before generating each IR operation, quickly check:

- [ ] **Encode**: facets are not empty, at least one business field
- [ ] **time_range**: use flat format, all three fields of relative time are complete
- [ ] **Promote**: has weight/weight_delta/remind one of them
- [ ] **Update**: set contains text/subject/tags/weight one of them
- [ ] **ids/tags**: both are in string array format
- [ ] **Stage-Op**: mapping is correct (Encode→ENC, Retrieve→RET, Label→STO)
- [ ] **Expire**: use ttl or until, do not use time_delta
- [ ] **Split**: strategy is one of the three types
- [ ] **Label**: has tags or facets

---

## ✅ Final Check List

Before generating each sample, please confirm:

- [ ] The instruction is among the above 12 instructions and corresponds to the stage 
- [ ] Structure is correct (single=1 operation, workflow=2–5 operations)
- [ ] Single sample's operation matches scenario_info.operation 
- [ ] Workflow samples are not constrained by scenario_info.operation 
- [ ] Prerequisites are a complete IR array (with stage, op, args) 
- [ ] Target selection is appropriate (prefer search/filter) 
- [ ] Output is JSONL (one JSON per line without formatting) 
- [ ] ID naming is correct (workflow uses wf)


---

## 📤 Output requirements (⚠️ Extremely important! Must be strictly adhered to)

### 1. Required fields (one is missing)

**You must output a complete JSON object with all of the following fields**:

```json
{
  "id": "t2m-zh-direct-single-ret-001", // ✅ Required
  "class": { // ✅ Required
    "instruction": "direct", "structure": "single", // Required
    "structure": "single", "lang": "zip", "lang".
    "lang": "zh"
  },
  "nl": { // ✅ Required
    "zh": "natural language instructions"
  },
  "prerequisites": [ // ✅ Required (array, can be empty [])
    {
      "stage": "ENC",
      "op": "Encode",.
      "args": {...}
    }
  ], "schema_list": [ // "schema_list": {...} }
  "schema_list": [ // ✅ Required (array, can't be empty)
    {
      "stage": "RET",
      "op": "Retrieve",
      "target": {...} ,
      "args": {...}
    }
  ], "init_db": null
  "init_db": null, // ✅ Required (fixed to null)
  "notes": "Sample notes" // ✅ Required
}
```

### 2. Detailed description of field requirements

| Fields | Type | Can be null | Description |
|------|------|---------|------|
| `id` | string | ❌ not allowed | must be generated by rule |
| `class` | object | ❌ not allowed | must contain instruction/structure/lang |
| `nl` | object | ❌ not available | must contain instruction/structure/lang |
| `prerequisites` | array | ✅ may be `[]` | Encode operations may be empty arrays, other operations must have content |
| `schema_list` | array | ❌ Cannot be empty | Contains at least 1 operation (single) or 2-5 operations (workflow) |
| `init_db` | null | ❌ must be `null` | fixed value |
| `notes` | string | ❌ not allowed | short description |

### 3. Formatting requirements

1. **Only output one complete JSON object**, do not output more than one
2. **Do not add any explanatory text, comments, or markdown tags**.
3. **Do not use ``json`` code blocks***. 4.
4. **Don't format** everything on one line
5. **Ensure that JSON is formatted correctly** and can be parsed by a standard JSON parser
6. **All required fields must be present**, even if they are an empty array or null

### 4. Correct Example

**Example 1: Retrieve operation (with prerequisites)
```
{"id": "t2m-zh-direct-single-ret-001", "class":{"instruction": "direct", "structure": "single", "lang": "zh"}, "nl":{"zh": "Finding the minutes of the last week"},"" prerequisites":[{"stage": "ENC", "op": "Encode", "args":{"payload":{"text": "Product Design Meeting Minutes", "knowledge_type": "fact", "source": "Meeting Systems"}, "type". "knowledge", "tags":["conference", "product"], "time": "2025-10-18T10:00:00Z"}}], "schema_list":[{"stage": "RET", "op": "Retrieve", "target":{"search":{ "intent":{"query": "minutes"}, "overrides":{"k":5, "alpha":0.7}}}, "args":{"include":["id", "text", "tags"]}}], "init_db":null, "notes":{"Retrieve last week's minutes"}
```

**Example 2: Encode operation (no prerequisites)
```
{"id": "t2m-zh-direct-single-enc-001", "class":{"instruction": "direct", "structure": "single", "lang": "zh"}, "nl":{"zh": "Record today's meeting"},"" prerequisites":[], "schema_list":[{"stage": "ENC", "op": "Encode", "args":{"payload":{"text": "The meeting discussed product design options", "knowledge_type": "fact"," source": "meeting_minutes"}, "type": "knowledge", "tags":["meeting", "product"], "time": "2025-10-20T10:00:00Z"}}], "init_db":null, "notes": "Recorded the meeting content"}
```

### 5. Examples of errors (❌ These are errors)

**Error 1: Missing required fields**
```json
{"nl":{"zh": "Find Meeting"}, "context":"..."}  // ❌ missing id, class, prerequisites, schema_list, init_db, notes
```

**Error 2: with notes text**
```
Here's the generated sample:
{"id":"..."}  // ❌ don't have any description text
```

**Error #3: Using code blocks**
```json
{"id":"..."}
```
// ❌ don't use markdown code blocks

**Error 4: outputting multiple JSON objects**
```
{"id": "001"}
{"id": "002"} // ❌ can only output one JSON object
```

**Error 5: schema_list is empty**
``` JSON.
{"id":"..." , "schema_list":[]} // ❌ schema_list cannot be an empty array
```

---

## 🎯 Currently generating tasks

**Please generate a complete IR Schema** for the following command:

- **Command**: {instruction}
- **Context**: {context}
- **Scenario**: {scenario}
- **Operation**: {operation}
- **Context**: {context} **Scenario**: {scenario} **Operation}
- **Language**: {lang}


### Mandate requirements

1. **Generate an accurate IR Schema based on the above directives and context**
2. **In case of Encode operation**:
   - `prerequisites` can be an empty array `[]`
   - `schema_list` contains 1 Encode operation
   - Apply knowledge extraction principles: atomization, typing, structuring

3. **In case of Retrieve/Summarize operation**:
   - `prerequisites` must contain 3-5 knowledge units (apply knowledge extraction principles to split)
   - `schema_list` contains 1 corresponding operation
   - The time of the prerequisites must match the query range

4. **If it is an STO operation** (Label/Update/Delete etc.):
   - `prerequisites` must contain 1-3 knowledge units
   - `schema_list` contains 1 corresponding operation

5. **If workflow structure**:
   - `schema_list` contains 2-5 logically related operations
   - Steps are referenced by ids

6. **Knowledge Extraction Requirements** (important):
   - Each Encode in prerequisites must be atomized knowledge
   - Add `knowledge_type`, `source`, `context` fields
   - use `type: "knowledge"` instead of `type: "note"`
   - Extract structured metadata in facets

7. **Output format**:
   - Single-line JSONL format
   - Contains all required fields
   - No additional text

---

# 🧪 Example reference (for generating structural checks)

---

### ✅ Example 1: Encode-only (no prepending)

**Encode**

```json
{
  "instruction": "Record the content of this morning's team meeting.",
  "context": "The user has just finished their daily station meeting.",
  
  "scenario_info":{"scenario": "meeting_notes", "operation": "encode", "style": "formal", "topic": "daily_meeting"}
}
```

**Output**

```json
{"id": "t2m-zh-direct-single-enc-001", "class":{"instruction_type": "direct", "structure": "single", "lang": "zh"}, "nl":{"zh": "Recording this morning's team meeting"}, "context": "Users just finished the daily station meeting", "prerequisites":[], "schema_list":[{"stage": "ENC", "op": "Encode", "args":{"payload":{"text":{"text": "Today's morning meeting discussed the current version of testing progress and task planning for next week", "knowledge_type": "fact", "source": "meeting_minutes", "context": "team_day_meeting"}, "type": "note", "tags":["meeting", "daily", "project_progress"], "time": "2025-10- 21T09:00:00Z", "facets":{"certainty": "confirmed"}}}], "init_db":null, "notes": "No predecessor operations"}
```

---

### ✅ Example 2: Retrieve (with 3-5 knowledge units)

**INPUT** **

```json
{
  "instruction": "Finds the minutes of last week's meeting about the project budget.",
  "context": "The user is ready to report on the budget progress",
  
  "scenario_info":{"scenario": "meeting_notes", "operation": "retrieve", "style": "concise", "topic": "project_budget"}
}
```

**Output**

```json
{"id": "t2m-zh-direct-single-ret-001", "class":{"instruction_type": "direct", "structure": "single", "lang": "zh"}, "nl":{"zh": "Finding minutes from last week's meeting about the project budget. "}, "context": "User ready to report on budget progress", "prerequisites":[{"stage": "ENC", "op": "Encode", "args":{"payload":{"text": "Budget Review Meeting: Confirmed Q4 Budget Goal of 2 Million CNY"," knowledge_type": "fact", "source": "Finance Department Meeting", "context": "Q4 Budget Discussion"}, "type": "knowledge", "tags":["meeting", "budget"], "time": "2025-10-18T10:00:00Z"," facets":{"amount":2,000,000, "currency": "CNY"}}},{"stage": "ENC", "op": "Encode", "args":{"payload":{"text": "Budgeted expenditures need to be kept within the upper limit of 2 million", "knowledge _type": "constraint", "source": "finance director", "context": "budget constraints"}, "type": "knowledge", "tags":["budget", "constraints"], "time": "2025-10-18T10:05:00Z", "facets" :{"amount_limit":2000000, "currency": "CNY"}}},{"stage": "ENC", "op": "Encode", "args":{"payload":{"text": "The R&D department is requesting an increase of 10% in the budget for performance optimization.", "knowledge_type":{"payload":{"text": "R&D department is requesting an increase of 10% in the budget for performance optimization.", "knowledge_type":{"knowledge_type":{"payload":{"text": "R&D department is requesting an increase of 10% in the budget for performance optimization."," knowledge_type": "request", "source": "R&D Manager", "context": "Budget Request"}, "type": "knowledge", "tags":["budget", "R&D"], "time": "2025-10-17T14:00:00Z"," facets":{"increase_ratio":0.1}}], "schema_list":[{"stage": "RET", "op": "Retrieve", "target":{"filter":{"has_tags":["meeting", "budget"], "time_ range":{"relative": "last", "amount":7, "unit": "days"}}}, "args":{"include":["id", "text", "tags"]}}], "init_db":null, "notes": "Retrieve minutes of budget-related meetings "}
```

---

### ✅ Example 3: STO operation (with 1-3 knowledge units)

**Enter**

```json
{
  "instruction": "Mark security audit results as high priority.", "context".
  "context": "The user is managing recent security audit tasks.",
  
  "scenario_info":{"scenario": "security_audit", "operation": "label", "style": "concise", "topic": "security_audit"}
}
``

**Output**

```json
{"id": "t2m-zh-direct-single-sto-001", "class":{"instruction_type": "direct", "structure": "single", "lang": "zh"}, "nl":{"zh": "Marks the security audit result as a High Priority"}, "context": "User is managing recent security audit tasks", "prerequisites":[{"stage": "ENC", "op": "Encode", "args":{"payload":{"text": "October 2025 Security Audit Finds Two Critical Vulnerabilities"," knowledge_type": "fact", "source": "security_team_report", "context": "Monthly Security Audit"}, "type": "knowledge", "tags":["security", "vulnerabilities"], "time": "2025-10-18T11:00:00Z"," facets":{"severity": "critical"}}}], "schema_list":[{"stage": "STO", "op": "Label", "target":{"filter":{"has_tags":["security", "vulnerability"], "time_ range":{"relative": "last", "amount":7, "unit": "days"}}}, "args":{"tags":["high_priority"], "mode": "add"}}], "init_db":null, "notes": "Tag critical vulnerability results"}
```

---

## 🚨 Final Reminder

**You must output a full JSON object** containing the following 7 fields:
1. `id` ✅
2. `class` ✅
3. `nl` ✅
4. `prerequisites` ✅ (array, Encode can be [], others need to have content)
5. `schema_list` ✅ (Array, not empty)
6. `init_db` ✅ (Fixed to null)
7. `notes` ✅

** Now start generating! Output the full JSON object directly, without anything else. **
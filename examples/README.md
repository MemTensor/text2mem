<div align="center">

# Text2Mem Examples | Text2Mem 示例

**Usage examples and reference documentation**  
**使用示例和参考文档**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## 📁 Directory Structure

### ir_operations/ - Single IR Examples

Independent IR JSON snippets demonstrating parameter formats for each operation. Useful for pasting into REPL for testing (note: most operations require prerequisite data).

### op_workflows/ - Minimal Executable Workflows

Each file contains a complete workflow of "seed data (Encode) → execute operation", ready to run directly for verification:

**Basic Operations:**
- `op_encode.json` - Encode operation
- `op_retrieve.json` - Retrieve with semantic search
- `op_summarize.json` - Summarize meeting notes

**Metadata Operations:**
- `op_label.json` - Label suggestion (first write "work" tagged record, then label)
- `op_update.json` - Update fields (first write "release", then update)

**Priority Operations:**
- `op_promote.json` - Promote weight (first write "action", then promote)
- `op_demote.json` - Demote weight (first write "archive", then demote)

**Lifecycle Operations:**
- `op_delete.json` - Delete by time range (first write OKR tagged records, then delete)
- `op_lock.json` - Lock record (first write "sensitive", then lock)
- `op_expire.json` - Set expiration (first write "temp", then expire)

**Content Operations:**
- `op_split.json` - Split by sections (first write long text, then split by headings)
- `op_merge.json` - Merge records (first write meeting A/B, then merge/link)

**Search-based Storage Operations** (security: must provide `limit`):
- `op_label_via_search.json` - Label via search+limit
- `op_update_via_search.json` - Update via search+limit
- `op_delete_search.json` - Soft delete via search+limit
- `op_promote_search.json` - Promote via search+limit

### workflows/ - End-to-End Scenarios

Three end-to-end examples (knowledge management, meeting notes, project management), including prerequisite data, queries, and follow-up organization.

---

## 🚀 How to Run

### Interactive REPL (Paste IR Line by Line)

```bash
python manage.py session --db ./text2mem.db
# Paste content from ir_operations/*.json and press Enter
```

### Run Workflows

```bash
# Real-world scenarios
python manage.py workflow examples/real_world_scenarios/workflow_meeting_notes.json --mode mock --db ./text2mem.db
python manage.py workflow examples/real_world_scenarios/workflow_project_management.json --mode mock --db ./text2mem.db
python manage.py workflow examples/real_world_scenarios/workflow_knowledge_management.json --mode mock --db ./text2mem.db

# Minimal operation workflows
python manage.py workflow examples/op_workflows/op_delete.json --mode mock --db ./text2mem.db
python manage.py workflow examples/op_workflows/op_label.json --mode mock --db ./text2mem.db
# ... (same for others)
```

### Run Demo (All Operations)

```bash
# Automatically run all minimal operation workflows
python manage.py demo --mode mock --db ./text2mem.db --set ops
```

---

## 🧩 Programmatic Usage (Optional)

Build `ModelsService` directly in code:

```python
from text2mem.services.service_factory import create_models_service
service = create_models_service(mode="mock")  # or openai/ollama/auto
```

---

## ℹ️ Notes

- **IR JSON aligned with latest Schema**:
  - No `engine_id`; Promote/Demote use `weight` or `weight_delta`; Update.set.weight in [0,1]
  - Retrieve examples use `search.intent.query` or filter-based fields
  - Adapter currently supports absolute time ranges (start/end) for time filtering
  - **Security**: Storage operations (Label/Update/Promote/Demote/Delete/Lock/Expire/Split/Merge) using `target.search` must provide `limit` field; otherwise execution will be rejected

- **Reset and rebuild database**:
  ```bash
  rm -f ./text2mem.db && python manage.py features --db ./text2mem.db
  ```

---

## 📋 Scenario Overview

- **Meeting Notes** (`workflow_meeting_notes`): Record meetings, extract action items, tag, remind, and summarize
- **Project Management** (`workflow_project_management`): Record projects and meetings, tag, promote weight, retrieve and summarize
- **Knowledge Management** (`workflow_knowledge_management`): Record notes and papers, semantic search, summarize and tag

---

# 中文

## 📁 目录结构

### ir_operations/ - 单条 IR 示例

独立的 IR JSON 片段，展示各操作的参数格式，便于在 REPL 中粘贴测试（注意：多数操作需要前置数据）。

### op_workflows/ - 最小可执行工作流

每个文件都包含"先种子（Encode）→再执行该操作"的完整流程，便于直接运行验证：

**基础操作:**
- `op_encode.json` - 编码操作
- `op_retrieve.json` - 语义检索
- `op_summarize.json` - 摘要会议记录

**元数据操作:**
- `op_label.json` - 标签建议（先写入"工作"标签记录，再打标签）
- `op_update.json` - 更新字段（先写入 release，再更新字段）

**优先级操作:**
- `op_promote.json` - 提升权重（先写入 action，再提升权重）
- `op_demote.json` - 降级权重（先写入 archive，再降级）

**生命周期操作:**
- `op_delete.json` - 按时间范围删除（先写入带 OKR 标签且在时间范围内的记录，再按时间范围删除）
- `op_lock.json` - 锁定记录（先写入 sensitive，再锁定）
- `op_expire.json` - 设置过期（先写入 temp，再设置过期）

**内容操作:**
- `op_split.json` - 按章节拆分（先写入长文，再按标题分割）
- `op_merge.json` - 合并记录（先写入 meeting A/B，再合并/链接）

**基于搜索的存储类操作**（安全限制：必须提供 `limit`）:
- `op_label_via_search.json` - 通过 search+limit 精确打标签
- `op_update_via_search.json` - 通过 search+limit 精确更新
- `op_delete_search.json` - 通过 search+limit 精确删除（soft 删除）
- `op_promote_search.json` - 通过 search+limit 精确提升权重

### workflows/ - 端到端场景

三套端到端示例（知识管理、会议记录、项目管理），包含前置数据、查询与后续整理。

---

## 🚀 运行方式

### 交互 REPL 逐条粘贴 IR

```bash
python manage.py session --db ./text2mem.db
# 在提示符粘贴 ir_operations/*.json 内容回车执行
```

### 运行工作流

```bash
# 真实场景
python manage.py workflow examples/real_world_scenarios/workflow_meeting_notes.json --mode mock --db ./text2mem.db
python manage.py workflow examples/real_world_scenarios/workflow_project_management.json --mode mock --db ./text2mem.db
python manage.py workflow examples/real_world_scenarios/workflow_knowledge_management.json --mode mock --db ./text2mem.db

# 最小操作工作流
python manage.py workflow examples/op_workflows/op_delete.json --mode mock --db ./text2mem.db
python manage.py workflow examples/op_workflows/op_label.json --mode mock --db ./text2mem.db
# ...（其余同理）
```

### 运行 Demo（所有操作）

```bash
# 自动依次跑所有最小操作工作流
python manage.py demo --mode mock --db ./text2mem.db --set ops
```

---

## 🧩 编程式使用（可选）

直接在代码中构建 `ModelsService`：

```python
from text2mem.services.service_factory import create_models_service
service = create_models_service(mode="mock")  # 或 openai/ollama/auto
```

---

## ℹ️ 注意事项

- **IR JSON 已与最新 Schema 对齐**：
  - 不包含 `engine_id`；Promote/Demote 使用 `weight` 或 `weight_delta`；Update.set.weight 在 [0,1]
  - 检索示例使用 `search.intent.query` 或基于 filter 的字段
  - 适配器当前对时间过滤支持绝对时间范围（start/end）；因此示例使用绝对时间
  - **安全考虑**：存储类操作（Label/Update/Promote/Demote/Delete/Lock/Expire/Split/Merge）若使用 `target.search`，必须提供 `limit` 字段；否则会被拒绝执行

- **清空并重建 DB**：
  ```bash
  rm -f ./text2mem.db && python manage.py features --db ./text2mem.db
  ```

---

## 📋 场景概述

- **会议记录**（`workflow_meeting_notes`）：录入会议、提取行动项、标记、提醒与摘要
- **项目管理**（`workflow_project_management`）：录入项目与会议、标注、提升权重、检索与总结
- **知识管理**（`workflow_knowledge_management`）：录入笔记与论文、语义检索、摘要与标注

---

<div align="center">

**Last Updated | 最后更新**: 2025-11-10

[⬆ Back to top | 返回顶部](#text2mem-examples--text2mem-示例)

</div>

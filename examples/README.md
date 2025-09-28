````markdown
# Text2Mem Examples

这个目录包含了 Text2Mem 的各种使用示例和参考文档。

## 📁 目录结构

### ir_operations/ - 单条 IR 示例
独立的 IR JSON 片段，展示各操作的参数格式，便于在 REPL 中粘贴测试（注意：多数操作需要前置数据）。

### op_workflows/ - 最小可执行工作流（新增）
每个文件都包含“先种子（Encode）→再执行该操作”的完整流程，便于直接运行验证：

- op_encode.json
- op_label.json（先写入“工作”标签记录，再打标签）
- op_promote.json（先写入 action，再提升权重）
- op_demote.json（先写入 archive，再降级）
- op_update.json（先写入 release，再更新字段）
- op_delete.json（先写入带 OKR 标签且在时间范围内的记录，再按时间范围删除）
- op_lock.json（先写入 sensitive，再锁定）
- op_expire.json（先写入 temp，再设置过期）
- op_split.json（先写入长文，再按标题分割）
- op_merge.json（先写入 meeting A/B，再合并/链接）
- op_retrieve.json（先写入样例，再语义检索）
- op_summarize.json（先写入 meeting 样例，再摘要）
  
另外包含基于语义搜索（target.search）的存储类操作示例（安全限制：必须提供 limit）：

- op_label_via_search.json（通过 search+limit 精确打标签）
- op_update_via_search.json（通过 search+limit 精确更新）
- op_delete_search.json（通过 search+limit 精确删除，soft 删除）
- op_promote_search.json（通过 search+limit 精确提升权重）

### workflows/ - 端到端场景
三套端到端示例（知识管理、会议记录、项目管理），包含前置数据、查询与后续整理。

## 🚀 运行方式

- 交互 REPL 逐条粘贴 IR：
  - python manage.py repl --db ./text2mem.db
  - 在提示符粘贴 ir_operations/*.json 内容回车执行
- 运行工作流：
  - python manage.py workflow examples/real_world_scenarios/workflow_meeting_notes.json --mode mock --db ./text2mem.db
  - python manage.py workflow examples/real_world_scenarios/workflow_project_management.json --mode mock --db ./text2mem.db
  - python manage.py workflow examples/real_world_scenarios/workflow_knowledge_management.json --mode mock --db ./text2mem.db
- 运行最小操作工作流：
  - python manage.py workflow examples/op_workflows/op_delete.json --mode mock --db ./text2mem.db
  - python manage.py workflow examples/op_workflows/op_label.json --mode mock --db ./text2mem.db
  - …（其余同理）
- 运行 demo（自动依次跑所有最小操作工作流）：
  - python manage.py demo --mode mock --db ./text2mem.db --set ops

### 🧩 编程式使用（可选）

- 直接在代码中构建 `ModelsService`：

  ```python
  from text2mem.services.service_factory import create_models_service
  service = create_models_service(mode="mock")  # 或 openai/ollama/auto
  ```

## ℹ️ 注意事项

- IR JSON 已与最新 Schema 对齐：
  - 不包含 engine_id；Promote/Demote 使用 weight 或 weight_delta；Update.set.weight 在 [0,1]
  - 检索示例使用 search.intent.query 或基于 filter 的字段
  - 适配器当前对时间过滤支持绝对时间范围（start/end）；因此示例使用绝对时间
  - 出于安全考虑，存储类操作（Label/Update/Promote/Demote/Delete/Lock/Expire/Split/Merge）若使用 target.search，必须提供 limit 字段；否则会被拒绝执行
- 清空并重建 DB：
  - rm -f ./text2mem.db && python manage.py features --db ./text2mem.db

## 场景概述

- 会议记录（workflow_meeting_notes）：录入会议、提取行动项、标记、提醒与摘要
- 项目管理（workflow_project_management）：录入项目与会议、标注、提升权重、检索与总结
- 知识管理（workflow_knowledge_management）：录入笔记与论文、语义检索、摘要与标注
````


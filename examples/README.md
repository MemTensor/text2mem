# Text2Mem Examples

这个目录包含了 Text2Mem 的各种使用示例和参考文档。

## 📁 目录结构

### `ir_operations/` - IR 操作示例
包含各种 IR 操作的标准示例，展示每种操作的正确格式和参数：

- **基础操作**:
  - `sample_ir_encode.json` - 编码操作，将文本转换为记忆
  - `sample_ir_retrieve.json` - 检索操作，语义搜索和过滤
  - `sample_ir_update.json` - 更新操作，修改记忆内容
  - `sample_ir_delete.json` - 删除操作，软删除和硬删除

- **标签和分类**:
  - `sample_ir_label.json` - 标签操作，自动生成和手动添加标签

- **记忆管理**:
  - `sample_ir_promote.json` - 提升操作，增加记忆重要性
  - `sample_ir_demote.json` - 降级操作，降低记忆优先级

- **高级操作**:
  - `sample_ir_merge.json` - 合并操作，组合相关记忆
  - `sample_ir_split.json` - 拆分操作，分解复杂记忆
  - `sample_ir_lock.json` - 锁定操作，保护重要记忆
  - `sample_ir_expire.json` - 过期操作，设置记忆生命周期

- **AI 功能**:
  - `sample_ir_summarize.json` - 摘要操作，生成内容摘要
  - `sample_ir_clarify.json` - 澄清操作，处理模糊输入

### `workflows/` - 工作流示例
展示复杂业务场景的完整工作流程：

- `workflow_project_management.json` - 项目管理工作流
- `workflow_knowledge_management.json` - 知识管理工作流  
- `workflow_meeting_notes.json` - 会议记录工作流

### `use_cases/` - 使用案例
实际应用场景的完整示例：

- `personal_knowledge_base.py` - 个人知识库管理
- `team_collaboration.py` - 团队协作记忆系统
- `research_assistant.py` - 研究助手应用

## 🚀 如何使用

### 1. 运行单个 IR 操作示例
```bash
# 使用 Text2Mem CLI 执行 IR 操作
python scripts/text2mem_cli.py --ir-file examples/ir_operations/sample_ir_encode.json

# 或使用 IR 测试工具
python scripts/test_ir_operations.py --operation encode
```

### 2. 运行完整工作流
```bash
# 执行工作流示例
python scripts/run_workflow.py examples/workflows/workflow_project_management.json

# 或使用演示脚本
python scripts/demo_complete.py
```

### 3. 探索使用案例
```bash
```bash
# 运行个人知识库示例 (带参数选项)
python scripts/demos/personal_knowledge_base.py --mode auto --db my_knowledge.db

# 使用不同模式运行:
# - auto: 自动尝试Ollama，失败时使用模拟模型 (默认)
# - ollama: 强制使用Ollama模型服务
# - mock: 强制使用模拟模型服务

# 测试 OpenAI API
python scripts/demos/openai_api_example.py
```
```

## 📖 学习路径

1. **初学者**: 从 `ir_operations/` 开始，了解各种基础操作
2. **进阶用户**: 查看 `workflows/` 了解复杂流程组合
3. **开发者**: 参考 `use_cases/` 开发自定义应用

## 🔗 相关资源

- 查看 `docs/` 目录获取详细文档
- 使用 `scripts/` 目录中的工具进行测试和验证
- 运行 `python manage.py status` 检查系统状态

## 💡 提示

- 所有示例都经过验证，可以直接使用
- 示例文件包含详细的注释和说明
- 可以基于示例创建自己的 IR 操作和工作流

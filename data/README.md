# Text2Mem 数据目录组织

此目录包含 Text2Mem 项目的所有数据库文件，按用途分类组织。

## 目录结构

```
data/
├── demo/           # 演示和交互式应用数据库
├── test/           # 测试数据库
├── production/     # 生产环境数据库
└── README.md       # 本文件
```

## 各子目录说明

### demo/ - 演示数据库
- `interactive.db` - 交互式控制台应用的默认数据库
- `mock_demo.db` - Mock模式演示数据库
- `ollama_demo.db` - Ollama模式演示数据库  
- `openai_demo.db` - OpenAI模式演示数据库

### test/ - 测试数据库
- `test_complete.db` - 完整集成测试数据库
- `test_operation.db` - 操作测试数据库
- `test_workflow.db` - 工作流测试数据库

### production/ - 生产环境数据库
- 用于实际使用的数据库文件
- 通常通过环境变量或配置文件指定具体路径

## 使用说明

### 环境变量配置
- `TEXT2MEM_DB_PATH` - 指定自定义数据库路径
- 如果未设置，各工具会使用对应目录下的默认数据库

### 脚本默认路径
- Demo脚本: `data/demo/` 目录下的对应文件
- 测试脚本: `data/test/` 目录下的对应文件
- 工具脚本: `data/demo/interactive.db` (默认)

### 数据库管理
使用 `scripts/tools/db_utils.py` 工具管理数据库：
```bash
# 查看数据库信息
python scripts/tools/db_utils.py info --db data/demo/interactive.db

# 备份数据库
python scripts/tools/db_utils.py backup --db data/demo/interactive.db

# 查看统计信息
python scripts/tools/db_utils.py stats --db data/demo/interactive.db
```

## 注意事项

1. **数据安全**: 生产环境数据库应该定期备份
2. **路径配置**: 推荐使用绝对路径或环境变量配置数据库路径
3. **权限管理**: 确保数据库文件有适当的读写权限
4. **版本控制**: 数据库文件通常不应提交到版本控制系统

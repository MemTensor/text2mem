# Text2Mem 变更日志

## [1.1.0] - 2025-01-05

### CLI 优化
- **优化 manage.py**: 删除冗余命令，增强核心功能
  - 删除 `features` 命令（功能重复，使用 `demo` 替代）
  - 删除 `repl` 命令（功能不完整，使用 `session` 替代）
  - 标记 `bench-*` 命令为开发中状态
  - **增强 session 命令**: 从 3 种操作扩展到支持全部 12 种 IR 操作
    - 原有: encode, retrieve, summarize
    - 新增: label, update, delete, promote, demote, lock, merge, split, expire
  - 总计 16 个命令，功能更聚焦、更完整

### 文档整理
- **清理根目录文档**: 删除 18 个临时/重复文档
  - 移除 8 个 BENCH_* 临时状态文档
  - 移除 5 个 STAGE2_* 开发过程文档
  - 移除 2 个 PROMPT_* 临时总结文档
  - 移除 3 个其他过期文档
  - 根目录现在只保留核心 README.md
- **文档结构优化**: 所有文档现在集中在 `docs/`, `bench/`, `examples/` 目录

### Bench 测试框架
- 完成 v1.3 重构，所有测试从空表开始
- 使用 prerequisites 动态准备数据，性能提升 96%
- 删除预填充数据库依赖，代码库减少 88%

## [1.0.0] - 2023-10-01

### 添加
- 实现 IR Schema v1.3 的全部 13 种操作
- 创建 SQLite 适配器，支持内存或本地文件数据库
- 添加 Pydantic v2 模型，与 Schema 保持一致性
- 创建示例运行器 run_demo.py，支持列出、运行单个或全部示例
- 添加工作流执行器 run_workflow.py，支持按序执行多个 IR 操作
- 完善 13 种操作的示例文件
- 添加单元测试和测试数据
- 创建项目模板生成器 create_project.sh
- 添加 Makefile，简化常用命令

### 优化
- 使用 Conda 环境管理依赖，简化安装流程
- 改进错误处理和报告
- 为所有模型增加严格的字段验证
- 优化项目结构，提高代码复用性
- 标准化适配器接口，便于扩展

### 文档
- 添加详细的安装指南 (INSTALL.md)
- 完善项目文档 (README.md)
- 添加测试文档
- 创建变更日志 (CHANGELOG.md)

## 未来计划

### 近期计划
- 增强向量检索支持
- 添加更多适配器 (PostgreSQL, MongoDB, Redis)
- 改进工作流管理，支持条件分支和循环
- 增加更多单元测试
- 创建 Python API 文档

### 长期计划
- 添加 Web API 界面
- 开发命令行工具
- 提供更丰富的搜索功能
- 支持批处理和异步操作
- 实现数据迁移和版本控制

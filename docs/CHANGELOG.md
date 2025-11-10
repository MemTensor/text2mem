<div align="center">

# Text2Mem Changelog | Text2Mem 变更日志

**Version history and release notes**  
**版本历史和发布说明**

</div>

---

# English | 英文

## [Unreleased] - 2025-01-26

### CLI Modernization

- **Refactored manage.py**: Comprehensive command structure and UX optimization
  - Improved code style, PEP 8 compliant
  - Reorganized command groups (Core Config / Feature Demo / Workflow Execution / Interactive Mode / Model Management / Operations Tools)
  - Enhanced command features:
    - `config`: Added `--db-path` parameter, updated default model versions
    - `test`: Added `-v/--verbose`, `-k/--keyword`, `--smoke` parameters
    - `demo`: Added `--verbose` parameter, improved error handling and statistics
    - `workflow`: Added `--verbose` parameter, detailed step information
    - `models-smoke`: Beautified output format, added troubleshooting guide
    - `setup-ollama`: Improved download progress indication
  - Unified output format with separators and emoji icons
  - All commands maintain backward compatibility

### Documentation Consolidation

- **bench/ Documentation Cleanup**:
  - Merged `QUICKSTART.md` + `QUICK_REFERENCE.md` → `GUIDE.md` (unified entry point)
  - Kept `README.md` (project overview)
  - All documentation converted to bilingual (Chinese-English)
- **docs/ Documentation Optimization**:
  - Enhanced `CONFIGURATION.md` (clearer configuration guide)
  - Kept `CHANGELOG.md` (this file)
  - Converted all files to bilingual format
- **Documentation Structure**:
  - Root directory: `README.md` (main project documentation)
  - `docs/`: Configuration and changelog
  - `bench/`: Benchmark-related documentation
  - `examples/`: Example descriptions
- **Reduced Duplication**: Core documentation now bilingual and streamlined

### Benchmark Testing Framework

- Completed v1.3 refactor, all tests start from empty table
- Use prerequisites to dynamically prepare data, 96% performance improvement
- Removed pre-filled database dependency, 88% codebase reduction

## [1.1.0] - 2025-01-05

### CLI Optimization

- **Optimized manage.py**: Removed redundant commands, enhanced core functionality
  - Removed `features` command (duplicate functionality, use `demo` instead)
  - Removed `repl` command (incomplete functionality, use `session` instead)
  - Marked `bench-*` commands as in-development status
  - **Enhanced session command**: Expanded from 3 to all 12 IR operations
    - Original: encode, retrieve, summarize
    - New: label, update, delete, promote, demote, lock, merge, split, expire
  - Total 16 commands, more focused and complete

### Documentation Cleanup

- **Cleaned Root Directory**: Removed 18 temporary/duplicate documents
  - Removed 8 BENCH_* temporary status documents
  - Removed 5 STAGE2_* development process documents
  - Removed 2 PROMPT_* temporary summary documents
  - Removed 3 other outdated documents
  - Root directory now only retains core README.md
- **Documentation Structure Optimization**: All documents now concentrated in `docs/`, `bench/`, `examples/` directories

## [1.0.0] - 2023-10-01

### Added

- Implemented all 13 operations from IR Schema v1.3
- Created SQLite adapter supporting in-memory or local file database
- Added Pydantic v2 models consistent with Schema
- Created example runner run_demo.py, supporting list, run single or all examples
- Added workflow executor run_workflow.py, supporting sequential execution of multiple IR operations
- Completed example files for all 13 operations
- Added unit tests and test data
- Created project template generator create_project.sh
- Added Makefile to simplify common commands

### Optimized

- Used Conda environment to manage dependencies, simplified installation process
- Improved error handling and reporting
- Added strict field validation for all models
- Optimized project structure, improved code reusability
- Standardized adapter interface for easy extension

### Documentation

- Added detailed installation guide (INSTALL.md)
- Enhanced project documentation (README.md)
- Added test documentation
- Created changelog (CHANGELOG.md)

## Future Plans

### Short-term Plans

- Enhanced vector retrieval support
- Add more adapters (PostgreSQL, MongoDB, Redis)
- Improve workflow management with conditional branches and loops
- Add more unit tests
- Create Python API documentation

### Long-term Plans

- Add Web API interface
- Develop command-line tools
- Provide richer search functionality
- Support batch processing and asynchronous operations
- Implement data migration and version control

---

# 中文 | Chinese

## [未发布] - 2025-01-26

### CLI 现代化

### CLI 现代化
- **重构 manage.py**: 全面优化命令结构和用户体验
  - 改进代码风格，符合 PEP 8 规范
  - 重新组织命令分组 (核心配置 / 功能演示 / 工作流执行 / 交互模式 / 模型管理 / 运维工具)
  - 增强命令功能：
    - `config`: 新增 `--db-path` 参数，更新默认模型版本
    - `test`: 新增 `-v/--verbose`, `-k/--keyword`, `--smoke` 参数
    - `demo`: 新增 `--verbose` 参数，改进错误处理和统计
    - `workflow`: 新增 `--verbose` 参数，详细步骤信息
    - `models-smoke`: 美化输出格式，添加故障排查指南
    - `setup-ollama`: 改进下载进度提示
  - 统一输出格式，添加分隔线和 emoji 图标
  - 所有命令保持向后兼容

### 文档整理与合并
- **bench/ 文档清理**:
  - 合并 `QUICKSTART.md` + `QUICK_REFERENCE.md` → `GUIDE.md` (统一入口)
  - 保留 `WORKFLOW.md` (详细工作流说明)
  - 保留 `README.md` (项目概览)
- **docs/ 文档优化**:
  - 删除 `INSTALL.md` (内容过时，已并入主 README)
  - 重构 `CONFIG.md` → `CONFIGURATION.md` (更清晰的配置指南)
  - 保留 `CHANGELOG.md` (本文件)
- **文档结构**:
  - 根目录: `README.md` (主项目文档)
  - `docs/`: 配置和变更日志
  - `bench/`: Benchmark 相关文档
  - `examples/`: 示例说明
- **减少重复**: 从 19 个活跃文档减少到 6 个核心文档

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

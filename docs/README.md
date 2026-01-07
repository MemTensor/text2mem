<div align="center">

# Text2Mem Documentation | Text2Mem 文档

**Complete documentation index and guide**  
**完整文档索引和指南**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## 📚 Documentation Structure

```
Text2Mem/
├── README.md                   # Project overview and quick start
├── docs/                       # Core documentation
│   ├── README.md              # This file - documentation index
│   ├── CONFIGURATION.md       # Configuration guide
│   └── CHANGELOG.md           # Version history
├── bench/                      # Benchmark system
│   ├── README.md              # Benchmark overview
│   ├── GUIDE.md               # Complete benchmark guide
│   └── TEST_REPORT.md         # Test validation report
└── examples/                   # Usage examples
    └── README.md              # Example documentation
```

## 🎯 Quick Navigation

### Getting Started

1. **[Installation & Setup](../README.md#-quick-start)** - Install Text2Mem and configure environment
2. **[Configuration Guide](CONFIGURATION.md)** - Set up providers (Mock/Ollama/OpenAI)
3. **[First Steps](../examples/README.md)** - Run your first operations

### Core Documentation

- **[README.md](../README.md)** - Project overview, architecture, and quick start
- **[CONFIGURATION.md](CONFIGURATION.md)** - Detailed configuration for all providers
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes

### Benchmark System

- **[bench/README.md](../bench/README.md)** - Benchmark system overview
- **[bench/GUIDE.md](../bench/GUIDE.md)** - Complete benchmark usage guide
- **[bench/TEST_REPORT.md](../bench/TEST_REPORT.md)** - Test report and validation

### Examples & Usage

- **[examples/README.md](../examples/README.md)** - Usage examples and scenarios
- **[examples/ir_operations/](../examples/ir_operations/)** - Single operation IR examples
- **[examples/op_workflows/](../examples/op_workflows/)** - Minimal executable workflows
- **[examples/real_world_scenarios/](../examples/real_world_scenarios/)** - End-to-end scenarios

## 📖 Documentation by Topic

### Architecture & Concepts

#### Operation Schema (IR)
The core of Text2Mem is the **Operation Schema IR** - a typed JSON contract that defines memory operations:

```json
{
  "stage": "ENC|RET|STR",
  "op": "Encode|Retrieve|...",
  "target": {...},
  "args": {...},
  "meta": {...}
}
```

See [README.md - Architecture](../README.md#-architecture) for details.

#### 12 Canonical Operations

**Encoding Stage (ENC):**
- `Encode` - Store new memories with embeddings

**Retrieval Stage (RET):**
- `Retrieve` - Search memories by semantic similarity or filters
- `Summarize` - Generate summaries of selected memories

**Storage Governance Stage (STR):**
- `Label` - Add tags and facets to memories
- `Update` - Modify memory fields (text, type, weight, tags)
- `Promote` - Increase weight or set reminders
- `Demote` - Decrease weight or archive
- `Merge` - Combine multiple memories
- `Split` - Break memory into parts
- `Lock` - Protect from modification
- `Expire` - Set expiration time
- `Delete` - Soft or hard delete memories

**Note:** `Clarify` is a UX utility for disambiguation, not a canonical operation.

### Configuration

#### Quick Setup
```bash
# 1. Copy template
cp .env.example .env

# 2. Choose provider (edit .env)
TEXT2MEM_PROVIDER=mock          # Testing
TEXT2MEM_PROVIDER=ollama        # Local models
TEXT2MEM_PROVIDER=openai        # Cloud API
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete guide.

#### Provider Comparison

| Provider | Speed | Cost | Setup | Use Case |
|----------|-------|------|-------|----------|
| **Mock** | ⚡ Fast | 💰 Free | ✅ None | Testing, development |
| **Ollama** | 🐢 Medium | 💰 Free | 🔧 Local install | Production, privacy |
| **OpenAI** | ⚡ Fast | 💰 Paid | 🔑 API key | Production, best quality |

### CLI Usage

#### Core Commands

```bash
# Environment
python manage.py status         # Check environment
python manage.py config          # Interactive configuration

# Execute IR
python manage.py ir --inline '{...}'    # Execute inline JSON
python manage.py ir --file path.json    # Execute from file

# Demo & Examples
python manage.py demo            # Run demo workflow

# Workflows
python manage.py workflow <file> # Run multi-step workflow

# Interactive
python manage.py session         # Enter REPL mode

# Testing
python manage.py test            # Run test suite
```

See [README.md - CLI Guide](../README.md#-cli-guide) for details.

### Benchmark System

The benchmark system provides two-layer evaluation:
1. **Plan-level**: NL → IR generation quality
2. **Execution-level**: IR → state transition correctness

```bash
# Quick test
./bench-cli run --mode mock -v

# Full test
./bench-cli run --mode ollama -v

# View results
./bench-cli show-result latest

# Generate new benchmark
./bench-cli generate
./bench-cli validate <id> --run-tests
./bench-cli promote <id>
```

See [bench/GUIDE.md](../bench/GUIDE.md) for complete guide.

## 🔧 Tools & Utilities

### Command-line Tools
- **manage.py** - Main management CLI
- **bench-cli** - Benchmark system CLI
- **scripts/** - Utility scripts for development

### Programmatic Usage

```python
from text2mem.services.service_factory import create_models_service
from text2mem.adapters.sqlite_adapter import SQLiteAdapter

# Create service
service = create_models_service(mode="mock")

# Create adapter
adapter = SQLiteAdapter(db_path="./text2mem.db")
```

## 🆘 Troubleshooting

### Common Issues

**Issue: `.env` not found**
```bash
cp .env.example .env
python manage.py config
```

**Issue: Ollama connection failed**
```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# Start Ollama
ollama serve
```

**Issue: OpenAI API error**
- Check API key in `.env`
- Verify API quota and billing

See [CONFIGURATION.md - Troubleshooting](CONFIGURATION.md) for more.

## 📝 Contributing

We welcome contributions! Before contributing:

1. Read the [README.md](../README.md)
2. Check [CHANGELOG.md](CHANGELOG.md) for recent changes
3. Follow the code structure and style
4. Add tests for new features
5. Update documentation

## 🔗 External Resources

- **Paper**: Research paper on Text2Mem (see [paper/](../paper/))
- **GitHub**: [github.com/your-username/Text2Mem](https://github.com/your-username/Text2Mem)
- **License**: [MIT License](../LICENSE)

---

# 中文

## 📚 文档结构

```
Text2Mem/
├── README.md                   # 项目概览和快速开始
├── docs/                       # 核心文档
│   ├── README.md              # 本文件 - 文档索引
│   ├── CONFIGURATION.md       # 配置指南
│   └── CHANGELOG.md           # 版本历史
├── bench/                      # 基准测试系统
│   ├── README.md              # 基准测试概览
│   ├── GUIDE.md               # 完整基准测试指南
│   └── TEST_REPORT.md         # 测试验证报告
└── examples/                   # 使用示例
    └── README.md              # 示例文档
```

## 🎯 快速导航

### 入门指南

1. **[安装与设置](../README.md#-快速开始-1)** - 安装 Text2Mem 并配置环境
2. **[配置指南](CONFIGURATION.md)** - 设置提供者（Mock/Ollama/OpenAI）
3. **[第一步](../examples/README.md)** - 运行第一个操作

### 核心文档

- **[README.md](../README.md)** - 项目概览、架构和快速开始
- **[CONFIGURATION.md](CONFIGURATION.md)** - 所有提供者的详细配置
- **[CHANGELOG.md](CHANGELOG.md)** - 版本历史和发布说明

### 基准测试系统

- **[bench/README.md](../bench/README.md)** - 基准测试系统概览
- **[bench/GUIDE.md](../bench/GUIDE.md)** - 完整基准测试使用指南
- **[bench/TEST_REPORT.md](../bench/TEST_REPORT.md)** - 测试报告和验证

### 示例与使用

- **[examples/README.md](../examples/README.md)** - 使用示例和场景
- **[examples/ir_operations/](../examples/ir_operations/)** - 单操作 IR 示例
- **[examples/op_workflows/](../examples/op_workflows/)** - 最小可执行工作流
- **[examples/real_world_scenarios/](../examples/real_world_scenarios/)** - 端到端场景

## 📖 按主题分类的文档

### 架构与概念

#### 操作契约（IR）
Text2Mem 的核心是 **操作契约 IR** - 定义记忆操作的类型化 JSON 契约：

```json
{
  "stage": "ENC|RET|STR",
  "op": "Encode|Retrieve|...",
  "target": {...},
  "args": {...},
  "meta": {...}
}
```

详见 [README.md - 架构设计](../README.md#-架构设计)。

#### 12 个标准操作

**编码阶段 (ENC):**
- `Encode` - 存储带有向量嵌入的新记忆

**检索阶段 (RET):**
- `Retrieve` - 通过语义相似度或过滤器搜索记忆
- `Summarize` - 生成选定记忆的摘要

**存储治理阶段 (STR):**
- `Label` - 为记忆添加标签和分面
- `Update` - 修改记忆字段（文本、类型、权重、标签）
- `Promote` - 增加权重或设置提醒
- `Demote` - 降低权重或归档
- `Merge` - 合并多个记忆
- `Split` - 将记忆拆分为多个部分
- `Lock` - 保护记忆不被修改
- `Expire` - 设置过期时间
- `Delete` - 软删除或硬删除记忆

**注意：** `Clarify` 是用于消歧的 UX 工具，不属于标准操作集。

### 配置

#### 快速配置
```bash
# 1. 复制模板
cp .env.example .env

# 2. 选择提供者（编辑 .env）
TEXT2MEM_PROVIDER=mock          # 测试
TEXT2MEM_PROVIDER=ollama        # 本地模型
TEXT2MEM_PROVIDER=openai        # 云端 API
```

完整指南见 [CONFIGURATION.md](CONFIGURATION.md)。

#### 提供者对比

| 提供者 | 速度 | 成本 | 设置 | 使用场景 |
|--------|------|------|------|----------|
| **Mock** | ⚡ 快 | 💰 免费 | ✅ 无 | 测试、开发 |
| **Ollama** | 🐢 中等 | 💰 免费 | 🔧 本地安装 | 生产、隐私 |
| **OpenAI** | ⚡ 快 | 💰 付费 | 🔑 API 密钥 | 生产、最佳质量 |

### CLI 使用

#### 核心命令

```bash
# 环境
python manage.py status         # 检查环境
python manage.py config          # 交互式配置

# 执行 IR
python manage.py ir --inline '{...}'    # 执行内联 JSON
python manage.py ir --file path.json    # 从文件执行

# 演示和示例
python manage.py demo            # 运行演示工作流

# 工作流
python manage.py workflow <文件> # 运行多步骤工作流

# 交互式
python manage.py session         # 进入 REPL 模式

# 测试
python manage.py test            # 运行测试套件
```

详见 [README.md - 命令行指南](../README.md#-命令行指南)。

### 基准测试系统

基准测试系统提供两层评估：
1. **计划层**：自然语言 → IR 生成质量
2. **执行层**：IR → 状态转换正确性

```bash
# 快速测试
./bench-cli run --mode mock -v

# 完整测试
./bench-cli run --mode ollama -v

# 查看结果
./bench-cli show-result latest

# 生成新基准
./bench-cli generate
./bench-cli validate <id> --run-tests
./bench-cli promote <id>
```

完整指南见 [bench/GUIDE.md](../bench/GUIDE.md)。

## 🔧 工具与实用程序

### 命令行工具
- **manage.py** - 主管理 CLI
- **bench-cli** - 基准测试系统 CLI
- **scripts/** - 开发实用脚本

### 编程式使用

```python
from text2mem.services.service_factory import create_models_service
from text2mem.adapters.sqlite_adapter import SQLiteAdapter

# 创建服务
service = create_models_service(mode="mock")

# 创建适配器
adapter = SQLiteAdapter(db_path="./text2mem.db")
```

## 🆘 故障排除

### 常见问题

**问题：找不到 `.env`**
```bash
cp .env.example .env
python manage.py config
```

**问题：Ollama 连接失败**
```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/version

# 启动 Ollama
ollama serve
```

**问题：OpenAI API 错误**
- 检查 `.env` 中的 API 密钥
- 验证 API 配额和计费

更多见 [CONFIGURATION.md - 故障排除](CONFIGURATION.md)。

## 📝 参与贡献

欢迎贡献！贡献前请：

1. 阅读 [README.md](../README.md)
2. 查看 [CHANGELOG.md](CHANGELOG.md) 了解最近变更
3. 遵循代码结构和风格
4. 为新功能添加测试
5. 更新文档

## 🔗 外部资源

- **论文**：Text2Mem 研究论文（见 [paper/](../paper/)）
- **GitHub**：[github.com/your-username/Text2Mem](https://github.com/your-username/Text2Mem)
- **许可证**：[MIT 许可证](../LICENSE)

---

<div align="center">

**Last Updated | 最后更新**: 2026-01-07  
**Version | 版本**: v1.2.0

[⬆ Back to top | 返回顶部](#text2mem-documentation--text2mem-文档)

</div>

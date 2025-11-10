<div align="center">

# Text2Mem Documentation | Text2Mem 文档

**Complete documentation index and guide**  
**完整文档索引和指南**

</div>

---

# English

## 📚 Main Documentation

### Core Documentation

- **[README.md](../README.md)** - Project overview, quick start, and architecture
- **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration guide for all providers
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[LICENSE](../LICENSE)** - MIT License

### Benchmark System

- **[bench/README.md](../bench/README.md)** - Benchmark system overview
- **[bench/GUIDE.md](../bench/GUIDE.md)** - Complete benchmark usage guide
- **[bench/TEST_REPORT.md](../bench/TEST_REPORT.md)** - Test report and validation

### Examples

- **[examples/README.md](../examples/README.md)** - Example usage and scenarios

## 🎯 Documentation by Topic

### Getting Started

1. **Installation**: See [README.md - Installation](../README.md#-quick-start)
2. **Quick Start**: See [README.md - Quick Start](../README.md#-quick-start)
3. **Configuration**: See [CONFIGURATION.md](CONFIGURATION.md)
4. **First Steps**: Check the [examples/](../examples/) directory

### Core Concepts

- **IR Schema**: See [README.md - Architecture](../README.md#-architecture)
- **13 Operations**: Encode, Retrieve, Summarize, Label, Update, Merge, Split, Promote, Demote, Lock, Expire, Delete, Clarify
- **Provider System**: Mock, Ollama, OpenAI providers
- **Validation**: JSON Schema + Pydantic v2 dual validation

### Configuration

- **Environment Setup**: [CONFIGURATION.md - Quick Setup](CONFIGURATION.md#quick-setup--快速配置)
- **Provider Selection**: [CONFIGURATION.md - Model Selection](CONFIGURATION.md#model-selection--模型选择)
- **Troubleshooting**: [CONFIGURATION.md - Troubleshooting](CONFIGURATION.md#troubleshooting--故障排除)

### Benchmarking

- **Overview**: [bench/README.md](../bench/README.md)
- **Commands**: [bench/GUIDE.md - Commands](../bench/GUIDE.md#command-reference--命令参考)
- **Workflows**: [bench/GUIDE.md - Workflows](../bench/GUIDE.md#complete-workflow--完整工作流)
- **Test Report**: [bench/TEST_REPORT.md](../bench/TEST_REPORT.md)

## 📂 Directory Structure

```
Text2Mem/
├── README.md                # Main project documentation
├── docs/                    # Documentation
│   ├── README.md           # This file
│   ├── CONFIGURATION.md    # Configuration guide
│   └── CHANGELOG.md        # Version history
├── bench/                   # Benchmark system
│   ├── README.md           # Benchmark overview
│   └── GUIDE.md            # Complete guide
├── examples/                # Usage examples
│   └── README.md           # Example documentation
└── text2mem/               # Source code
```

## 🔧 Tools

- **manage.py** - Main management CLI (see [README.md - CLI Guide](../README.md#-cli-guide))
- **bench-cli** - Benchmark CLI tool (see [bench/README.md](../bench/README.md))
- **scripts/** - Utility scripts

## 🆘 Getting Help

- Check the documentation above
- Look at [examples/](../examples/) for sample code
- Open an issue on GitHub for bugs or questions

## 📝 Notes

This documentation is continuously updated. For the latest information, always refer to the files in the repository.

---

# 中文

## 📚 主要文档

### 核心文档

- **[README.md](../README.md)** - 项目概览、快速开始和架构
- **[CONFIGURATION.md](CONFIGURATION.md)** - 所有 Provider 的配置指南
- **[CHANGELOG.md](CHANGELOG.md)** - 版本历史和发布说明
- **[LICENSE](../LICENSE)** - MIT 许可证

### 基准测试系统

- **[bench/README.md](../bench/README.md)** - 基准测试系统概览
- **[bench/GUIDE.md](../bench/GUIDE.md)** - 完整基准测试使用指南
- **[bench/TEST_REPORT.md](../bench/TEST_REPORT.md)** - 测试报告和验证

### 示例

- **[examples/README.md](../examples/README.md)** - 使用示例和场景

## 🎯 按主题分类的文档

### 入门指南

1. **安装**: 参见 [README.md - 快速开始](../README.md#-快速开始-1)
2. **快速开始**: 参见 [README.md - 快速开始](../README.md#-快速开始-1)
3. **配置**: 参见 [CONFIGURATION.md](CONFIGURATION.md)
4. **第一步**: 查看 [examples/](../examples/) 目录

### 核心概念

- **IR Schema**: 参见 [README.md - 架构设计](../README.md#-架构设计)
- **13 种操作**: 编码、检索、摘要、标签、更新、合并、拆分、提升、降级、锁定、过期、删除、澄清
- **Provider 系统**: Mock、Ollama、OpenAI 提供者
- **验证**: JSON Schema + Pydantic v2 双重验证

### 配置

- **环境设置**: [CONFIGURATION.md - 快速配置](CONFIGURATION.md#quick-setup--快速配置)
- **Provider 选择**: [CONFIGURATION.md - 模型选择](CONFIGURATION.md#model-selection--模型选择)
- **故障排除**: [CONFIGURATION.md - 故障排除](CONFIGURATION.md#troubleshooting--故障排除)

### 基准测试

- **概览**: [bench/README.md](../bench/README.md)
- **命令**: [bench/GUIDE.md - 命令参考](../bench/GUIDE.md#command-reference--命令参考)
- **工作流**: [bench/GUIDE.md - 完整工作流](../bench/GUIDE.md#complete-workflow--完整工作流)
- **测试报告**: [bench/TEST_REPORT.md](../bench/TEST_REPORT.md)

## 📂 目录结构

```
Text2Mem/
├── README.md                # 主项目文档
├── docs/                    # 文档
│   ├── README.md           # 本文件
│   ├── CONFIGURATION.md    # 配置指南
│   └── CHANGELOG.md        # 版本历史
├── bench/                   # 基准测试系统
│   ├── README.md           # 基准测试概览
│   └── GUIDE.md            # 完整指南
├── examples/                # 使用示例
│   └── README.md           # 示例文档
└── text2mem/               # 源代码
```

## 🔧 工具

- **manage.py** - 主管理 CLI（参见 [README.md - 命令行指南](../README.md#-命令行指南)）
- **bench-cli** - 基准测试 CLI 工具（参见 [bench/README.md](../bench/README.md)）
- **scripts/** - 实用脚本

## 🆘 获取帮助

- 查看上述文档
- 查看 [examples/](../examples/) 了解示例代码
- 在 GitHub 上提出问题报告 bug 或提问

## 📝 注意

本文档持续更新。最新信息请始终参考仓库中的文件。

---

<div align="center">

**Last Updated | 最后更新**: 2025-11-10  
**Version | 版本**: 0.2.0

[⬆ Back to top | 返回顶部](#text2mem-documentation--text2mem-文档)

</div>

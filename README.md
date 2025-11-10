<div align="center">

# Text2Mem · Structured Memory Engine
# 结构化记忆引擎

**IR Schema → Validation → Execution → Storage/Retrieval → Unified Result**  
**IR 架构 → 校验 → 执行 → 存储/检索 → 统一结果**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[English](#english) | [中文](#中文) | [Documentation](docs/) | [Contributing](CONTRIBUTING.md)

</div>

---

# English

## 📖 Table of Contents

- [Why Text2Mem](#why-text2mem)
- [Core Features](#core-features)
- [Quick Start](#quick-start)
- [Step-by-Step Guide](#step-by-step-guide)
- [Architecture](#architecture)
- [CLI Guide](#cli-guide)
- [Examples](#examples)
- [Benchmark System](#benchmark-system)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Why Text2Mem

Modern agents and assistants struggle with long-term memory:
- **Ad-hoc operations**: No standardized way to manage memory
- **Tight coupling**: Model invocations directly coupled to storage
- **No intermediate representation**: Lacks a stable layer between intent and execution

**Text2Mem** solves this with:
- ✅ **Unified IR**: 13 memory operations with consistent schema
- ✅ **Provider abstraction**: Switch between Mock/Ollama/OpenAI seamlessly  
- ✅ **Strong validation**: JSON Schema + Pydantic v2
- ✅ **Production-ready**: SQLite adapter with semantic search

Use it as a prototyping sandbox, production memory core, or teaching reference.

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| **13 Operations** | Encode, Retrieve, Summarize, Label, Update, Merge, Split, Promote, Demote, Lock, Expire, Delete, Clarify |
| **Multi-Provider** | Mock (testing), Ollama (local), OpenAI (cloud) |
| **Semantic Search** | Hybrid search with embedding similarity + keyword matching |
| **Validation** | JSON Schema + Pydantic v2 dual validation |
| **CLI Tools** | Unified CLI for all operations + benchmark system |
| **Benchmark** | Complete test generation & validation pipeline |

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-username/Text2Mem.git
cd Text2Mem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install package
pip install -e .
```

### First Run (Mock Mode)

```bash
# Copy environment template
cp .env.example .env

# Use mock provider (no LLM required)
# Edit .env and ensure: TEXT2MEM_PROVIDER=mock

# Run demo
python manage.py demo
```

## 📚 Step-by-Step Guide

### Step 1: Environment Setup

**Choose your provider:**

#### Option A: Mock (Testing, No LLM)
```bash
cp .env.example .env
# .env content:
# TEXT2MEM_PROVIDER=mock
```

#### Option B: Ollama (Local Models)
```bash
# Install Ollama: https://ollama.ai
# Pull models
ollama pull nomic-embed-text
ollama pull qwen2:0.5b

# Configure .env
cp .env.example .env
# Edit .env:
# TEXT2MEM_PROVIDER=ollama
# TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
# TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
# OLLAMA_BASE_URL=http://localhost:11434
```

#### Option C: OpenAI (Cloud API)
```bash
cp .env.example .env
# Edit .env:
# TEXT2MEM_PROVIDER=openai
# TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
# TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
# OPENAI_API_KEY=your-api-key-here
```

### Step 2: Verify Setup

```bash
# Check environment status
python manage.py status

# Expected output:
# ✅ Environment configured
# ✅ Provider: mock/ollama/openai
# ✅ Models loaded
```

### Step 3: Run Your First Operation

#### Encode a Memory
```bash
# Create a memory from text
python manage.py ir '{"op":"Encode","args":{"text":"Meeting with team about Q4 roadmap","knowledge_type":"event","tags":["meeting","roadmap"]}}'

# Output:
# ✅ Encoded memory [id=1]
# 📝 Content: Meeting with team about Q4 roadmap
# 🏷️  Tags: meeting, roadmap
```

#### Retrieve Memories
```bash
# Search by text
python manage.py ir '{"op":"Retrieve","args":{"query":"roadmap meeting","limit":5}}'

# Output:
# 🔍 Found 1 memories
# [1] Meeting with team about Q4 roadmap (score: 0.95)
```

#### Summarize Content
```bash
# Get AI summary of stored content
python manage.py ir '{"op":"Summarize","args":{"memory_ids":[1],"style":"brief"}}'

# Output:
# 📄 Summary: Team discussed Q4 product roadmap and priorities
```

### Step 4: Interactive Mode

```bash
# Enter REPL session
python manage.py session

# Commands:
> encode "Another important meeting"
> retrieve "meeting" limit=5
> status
> help
> exit
```

### Step 5: Run Complete Workflows

```bash
# Execute multi-step workflow
python manage.py workflow examples/op_workflows/encode_label_retrieve.json

# Output shows each step:
# Step 1/3: Encode ✅
# Step 2/3: Label ✅
# Step 3/3: Retrieve ✅
```

### Step 6: Explore Examples

```bash
# Single operations
ls examples/ir_operations/

# Complete workflows
ls examples/op_workflows/

# Real-world scenarios
ls examples/real_world_scenarios/
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────┐
│                 Client / CLI                    │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              IR (JSON Schema)                   │
│  {op: "Encode", args: {text, tags, ...}}       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│            Validation Layer                     │
│      JSON Schema + Pydantic v2                  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              Engine Core                        │
│        Text2MemEngine.execute()                 │
└────────┬────────────────────────┬────────────────┘
         │                        │
         ▼                        ▼
┌──────────────────┐    ┌──────────────────────┐
│  Model Service   │    │   Storage Adapter    │
│  - Mock          │    │   - SQLite           │
│  - Ollama        │    │   - Postgres (TODO)  │
│  - OpenAI        │    │   - Vector DB (TODO) │
└──────────────────┘    └──────────────────────┘
```

**Key Components:**

- **IR Schema**: JSON Schema defining all 13 operations
- **Engine**: Orchestrates validation → execution → result
- **Services**: Model abstraction (embedding, generation)
- **Adapters**: Storage abstraction (currently SQLite)
- **CLI**: User-friendly command-line interface

## 🛠 CLI Guide

### Main Commands

```bash
# Environment
python manage.py status              # Show environment status
python manage.py config              # Interactive configuration

# Single IR execution
python manage.py ir <json>           # Execute one IR
python manage.py ir --file path.json # Execute from file

# Demo & examples
python manage.py demo                # Run demo workflow

# Workflow execution
python manage.py workflow <file>     # Run multi-step workflow

# Interactive mode
python manage.py session             # Enter REPL

# Testing
python manage.py test                # Run test suite
```

### Benchmark CLI

```bash
# Generate benchmark data
./bench-cli generate --count 10 --output bench/data/raw/test.jsonl

# Validate generated data
./bench-cli validate bench/data/raw/test.jsonl

# Clean and prepare data
./bench-cli clean bench/data/raw/test.jsonl --output bench/data/benchmark/benchmark.jsonl

# Test benchmark
./bench-cli test bench/data/benchmark/benchmark.jsonl --mode mock

# View results
./bench-cli results bench/data/results/latest.jsonl
```

See [bench/GUIDE.md](bench/GUIDE.md) for complete benchmark documentation.

## 💡 Examples

### Encode Operation
```json
{
  "op": "Encode",
  "args": {
    "text": "Product launch scheduled for Q1 2024",
    "knowledge_type": "event",
    "tags": ["product", "launch", "2024"],
    "importance": 0.9
  }
}
```

### Retrieve with Filters
```json
{
  "op": "Retrieve",
  "args": {
    "query": "product launch",
    "limit": 10,
    "filters": {
      "tags": ["product"],
      "min_importance": 0.7
    }
  }
}
```

### Label Suggestion
```json
{
  "op": "Label",
  "args": {
    "memory_ids": [1, 2, 3],
    "mode": "suggest"
  }
}
```

See [examples/](examples/) for more.

## 🧪 Benchmark System

Text2Mem includes a complete benchmark pipeline:

1. **Generate**: Create test cases using LLM
2. **Validate**: Ensure schema compliance
3. **Clean**: Filter and deduplicate
4. **Test**: Execute and measure performance
5. **Analyze**: Generate reports

```bash
# Quick benchmark run
./bench-cli generate --count 5
./bench-cli validate bench/data/raw/latest.jsonl
./bench-cli clean bench/data/raw/latest.jsonl
./bench-cli test bench/data/benchmark/benchmark.jsonl
```

See [bench/README.md](bench/README.md) for details.

## 📚 Documentation

- **[README.md](README.md)** - This file
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guide
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[bench/README.md](bench/README.md)** - Benchmark system
- **[bench/GUIDE.md](bench/GUIDE.md)** - Complete usage guide
- **[docs/README.md](docs/README.md)** - Documentation index

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

# 中文

## 📖 目录

- [为什么需要 Text2Mem](#为什么需要-text2mem)
- [核心功能](#核心功能)
- [快速开始](#快速开始-1)
- [分步指南](#分步指南)
- [架构设计](#架构设计)
- [命令行指南](#命令行指南)
- [示例](#示例)
- [基准测试系统](#基准测试系统)
- [文档](#文档-1)
- [参与贡献](#参与贡献)
- [许可证](#许可证-1)

## 🎯 为什么需要 Text2Mem

现代 AI 助手在长期记忆管理上存在挑战：
- **操作碎片化**：缺乏标准化的记忆管理方式
- **紧耦合**：模型调用与存储直接耦合
- **缺少中间层**：意图与执行之间缺乏稳定的抽象层

**Text2Mem** 的解决方案：
- ✅ **统一 IR**：13 种记忆操作，统一 Schema
- ✅ **Provider 抽象**：Mock/Ollama/OpenAI 无缝切换  
- ✅ **强校验**：JSON Schema + Pydantic v2 双重保障
- ✅ **生产就绪**：SQLite 适配器，支持语义检索

可作为原型沙盒、生产内核或教学参考。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| **13 种操作** | 编码、检索、摘要、标签、更新、合并、拆分、提升、降级、锁定、过期、删除、澄清 |
| **多 Provider** | Mock（测试）、Ollama（本地）、OpenAI（云端） |
| **语义搜索** | 混合搜索：嵌入相似度 + 关键词匹配 |
| **强校验** | JSON Schema + Pydantic v2 双重校验 |
| **CLI 工具** | 统一 CLI + 完整基准测试系统 |
| **基准测试** | 完整的测试生成和验证流水线 |

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/Text2Mem.git
cd Text2Mem

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装
pip install -e .
```

### 首次运行（Mock 模式）

```bash
# 复制环境配置
cp .env.example .env

# 使用 mock provider（无需 LLM）
# 编辑 .env 确保: TEXT2MEM_PROVIDER=mock

# 运行演示
python manage.py demo
```

## 📚 分步指南

### 步骤 1：环境配置

**选择 Provider：**

#### 选项 A：Mock（测试用，无需 LLM）
```bash
cp .env.example .env
# .env 内容：
# TEXT2MEM_PROVIDER=mock
```

#### 选项 B：Ollama（本地模型）
```bash
# 安装 Ollama: https://ollama.ai
# 拉取模型
ollama pull nomic-embed-text
ollama pull qwen2:0.5b

# 配置 .env
cp .env.example .env
# 编辑 .env：
# TEXT2MEM_PROVIDER=ollama
# TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
# TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
# OLLAMA_BASE_URL=http://localhost:11434
```

#### 选项 C：OpenAI（云端 API）
```bash
cp .env.example .env
# 编辑 .env：
# TEXT2MEM_PROVIDER=openai
# TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
# TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
# OPENAI_API_KEY=你的-API-密钥
```

### 步骤 2：验证配置

```bash
# 检查环境状态
python manage.py status

# 预期输出：
# ✅ 环境已配置
# ✅ Provider: mock/ollama/openai
# ✅ 模型已加载
```

### 步骤 3：执行第一个操作

#### 编码记忆
```bash
# 从文本创建记忆
python manage.py ir '{"op":"Encode","args":{"text":"团队会议讨论 Q4 路线图","knowledge_type":"event","tags":["会议","路线图"]}}'

# 输出：
# ✅ 已编码记忆 [id=1]
# 📝 内容：团队会议讨论 Q4 路线图
# 🏷️  标签：会议、路线图
```

#### 检索记忆
```bash
# 按文本搜索
python manage.py ir '{"op":"Retrieve","args":{"query":"路线图 会议","limit":5}}'

# 输出：
# 🔍 找到 1 条记忆
# [1] 团队会议讨论 Q4 路线图 (相似度: 0.95)
```

#### 生成摘要
```bash
# 获取内容的 AI 摘要
python manage.py ir '{"op":"Summarize","args":{"memory_ids":[1],"style":"brief"}}'

# 输出：
# 📄 摘要：团队讨论了 Q4 产品路线图和优先级
```

### 步骤 4：交互模式

```bash
# 进入 REPL 会话
python manage.py session

# 命令：
> encode "另一个重要会议"
> retrieve "会议" limit=5
> status
> help
> exit
```

### 步骤 5：运行完整工作流

```bash
# 执行多步骤工作流
python manage.py workflow examples/op_workflows/encode_label_retrieve.json

# 输出显示每个步骤：
# 步骤 1/3: Encode ✅
# 步骤 2/3: Label ✅
# 步骤 3/3: Retrieve ✅
```

### 步骤 6：探索示例

```bash
# 单个操作示例
ls examples/ir_operations/

# 完整工作流
ls examples/op_workflows/

# 真实场景
ls examples/real_world_scenarios/
```

## 🏗 架构设计

```
┌─────────────────────────────────────────────────┐
│              客户端 / CLI                       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              IR (JSON Schema)                   │
│  {op: "Encode", args: {text, tags, ...}}       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              校验层                             │
│      JSON Schema + Pydantic v2                  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              引擎核心                           │
│        Text2MemEngine.execute()                 │
└────────┬────────────────────────┬────────────────┘
         │                        │
         ▼                        ▼
┌──────────────────┐    ┌──────────────────────┐
│    模型服务      │    │    存储适配器        │
│  - Mock          │    │   - SQLite           │
│  - Ollama        │    │   - Postgres (TODO)  │
│  - OpenAI        │    │   - Vector DB (TODO) │
└──────────────────┘    └──────────────────────┘
```

**核心组件：**

- **IR Schema**：定义所有 13 种操作的 JSON Schema
- **引擎**：编排 校验 → 执行 → 结果
- **服务**：模型抽象（嵌入、生成）
- **适配器**：存储抽象（目前为 SQLite）
- **CLI**：用户友好的命令行界面

## 🛠 命令行指南

### 主要命令

```bash
# 环境
python manage.py status              # 显示环境状态
python manage.py config              # 交互式配置

# 单个 IR 执行
python manage.py ir <json>           # 执行一个 IR
python manage.py ir --file 路径.json # 从文件执行

# 演示和示例
python manage.py demo                # 运行演示工作流

# 工作流执行
python manage.py workflow <文件>     # 运行多步骤工作流

# 交互模式
python manage.py session             # 进入 REPL

# 测试
python manage.py test                # 运行测试套件
```

### Benchmark CLI

```bash
# 生成基准数据
./bench-cli generate --count 10 --output bench/data/raw/test.jsonl

# 验证生成的数据
./bench-cli validate bench/data/raw/test.jsonl

# 清理和准备数据
./bench-cli clean bench/data/raw/test.jsonl --output bench/data/benchmark/benchmark.jsonl

# 测试基准
./bench-cli test bench/data/benchmark/benchmark.jsonl --mode mock

# 查看结果
./bench-cli results bench/data/results/latest.jsonl
```

详见 [bench/GUIDE.md](bench/GUIDE.md)。

## 💡 示例

### 编码操作
```json
{
  "op": "Encode",
  "args": {
    "text": "产品发布计划于 2024 Q1",
    "knowledge_type": "event",
    "tags": ["产品", "发布", "2024"],
    "importance": 0.9
  }
}
```

### 带过滤的检索
```json
{
  "op": "Retrieve",
  "args": {
    "query": "产品发布",
    "limit": 10,
    "filters": {
      "tags": ["产品"],
      "min_importance": 0.7
    }
  }
}
```

### 标签建议
```json
{
  "op": "Label",
  "args": {
    "memory_ids": [1, 2, 3],
    "mode": "suggest"
  }
}
```

更多示例见 [examples/](examples/)。

## 🧪 基准测试系统

Text2Mem 包含完整的基准测试流水线：

1. **生成**：使用 LLM 创建测试用例
2. **验证**：确保 Schema 合规
3. **清理**：过滤和去重
4. **测试**：执行并测量性能
5. **分析**：生成报告

```bash
# 快速基准测试运行
./bench-cli generate --count 5
./bench-cli validate bench/data/raw/latest.jsonl
./bench-cli clean bench/data/raw/latest.jsonl
./bench-cli test bench/data/benchmark/benchmark.jsonl
```

详见 [bench/README.md](bench/README.md)。

## 📚 文档

- **[README.md](README.md)** - 本文件
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - 贡献指南
- **[CHANGELOG.md](CHANGELOG.md)** - 版本历史
- **[bench/README.md](bench/README.md)** - 基准测试系统
- **[bench/GUIDE.md](bench/GUIDE.md)** - 完整使用指南
- **[docs/README.md](docs/README.md)** - 文档索引

## 🤝 参与贡献

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)：
- 开发环境设置
- 代码风格指南
- 测试要求
- Pull Request 流程

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE)。

---

<div align="center">

**Built with ❤️ for better AI memory management**  
**为更好的 AI 记忆管理而构建**

[⬆ Back to top / 返回顶部](#text2mem--structured-memory-engine)

</div>

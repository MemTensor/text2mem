<div align="center">

# Benchmark System Complete Guide | Benchmark 系统完整指南

**Comprehensive guide for the Text2Mem benchmark system**  
**Text2Mem 基准测试系统的完整使用指南**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Complete Workflow](#complete-workflow)
3. [Command Reference](#command-reference)
4. [Data Structure](#data-structure)
5. [Common Questions](#common-questions)

---

## 🚀 Quick Start

### First Time Use

```bash
# 1. View benchmark information
./bench-cli info

# 2. Run quick test (few seconds)
./bench-cli run --mode mock -v

# 3. View results
./bench-cli show-result latest
```

### Daily Use

```bash
# Full test
./bench-cli run --mode ollama -v

# View history
./bench-cli list-results

# Compare results
./bench-cli compare <id1> <id2>
```

---

## 🔄 Complete Workflow

### Workflow 1: Daily Testing

```bash
# 1. View benchmark
./bench-cli info

# 2. Run tests
./bench-cli run --mode ollama -v

# 3. View results
./bench-cli show-result latest

# 4. View historical trends
./bench-cli list-results
```

### Workflow 2: Generate New Benchmark

```bash
# Step 1: Edit configuration (optional)
nano bench/generate/config/generation_plan.yaml

# Step 2: Generate data
./bench-cli generate

# Step 3: Validate quality
./bench-cli validate <generation_id>
./bench-cli validate <generation_id> --run-tests

# Step 4: If quality is good, promote to official benchmark
./bench-cli promote <generation_id>

# Step 5: Test new benchmark
./bench-cli run --mode ollama -v
```

### Workflow 3: Debugging Issues

```bash
# Test specific operations only
./bench-cli run --schema-filter Encode -v

# View failure details
./bench-cli show-result latest --show-failed

# Test Chinese only
./bench-cli run --filter "lang:zh" -v
```

---

## 📖 Command Reference

### `run` - Run Tests

```bash
./bench-cli run [OPTIONS]

Options:
  --mode MODE              Test mode: auto/mock/ollama/openai
  --filter EXPR            Sample filter: "lang:zh" or "lang:en"
  --schema-filter OPS      Operation filter: "Encode,Retrieve"
  --schema-indices IDS     Index filter: "0,2"
  --timeout SECONDS        Timeout setting
  --output-id ID           Result ID
  --verbose, -v            Verbose output

Examples:
  ./bench-cli run --mode mock -v              # Mock quick test
  ./bench-cli run --mode ollama -v            # Ollama full test
  ./bench-cli run --filter "lang:zh" -v       # Chinese only
  ./bench-cli run --schema-filter Encode -v   # Encode only
```

### `generate` - Generate New Benchmark

```bash
./bench-cli generate [OPTIONS]

Options:
  --config FILE            Configuration file path
  --output-id ID           Output ID
  --use-generation-dir     Use generation/ directory

Examples:
  ./bench-cli generate                        # Use default config
  ./bench-cli generate --config my_plan.yaml  # Use custom config
```

### `validate` - Validate Data

```bash
./bench-cli validate <generation_id> [OPTIONS]

Options:
  --run-tests              Run test validation
  --verbose, -v            Verbose output

Examples:
  ./bench-cli validate 20251110_100000               # Quick stats
  ./bench-cli validate 20251110_100000 --run-tests   # Full validation
```

### `promote` - Promote to Benchmark

```bash
./bench-cli promote <generation_id> [OPTIONS]

Options:
  --yes, -y                Skip confirmation
  --notes TEXT             Notes

Examples:
  ./bench-cli promote 20251110_100000                    # Promote (needs confirmation)
  ./bench-cli promote 20251110_100000 -y                 # Skip confirmation
  ./bench-cli promote 20251110_100000 --notes "v2.0"
```

**Warning**: This operation will replace the current benchmark, but will automatically backup to `archive/`.

### `list-results` - List Results

```bash
./bench-cli list-results [--limit N]

Examples:
  ./bench-cli list-results            # Show recent 20
  ./bench-cli list-results --limit 5  # Show recent 5
```

### `show-result` - Show Details

```bash
./bench-cli show-result <result_id> [--show-failed]

Examples:
  ./bench-cli show-result latest                 # Latest result
  ./bench-cli show-result 20251110_130000        # Specific result
  ./bench-cli show-result latest --show-failed   # Show failed samples
```

### `compare` - Compare Results

```bash
./bench-cli compare <result_id1> <result_id2>

Examples:
  ./bench-cli compare 20251110_130000 20251110_140000
```

### `info` - Benchmark Information

```bash
./bench-cli info

Shows statistics of current benchmark
```

---

## 📊 Data Structure

### Complete Directory Structure

```
bench/data/
├── benchmark/          # Current benchmark in use
│   ├── benchmark.jsonl # Test samples
│   ├── metadata.json   # Metadata
│   └── stats.json      # Statistics
│
├── results/            # Test history
│   ├── 20251110_130000/
│   │   ├── config.json
│   │   ├── report.json
│   │   ├── passed.jsonl
│   │   └── failed.jsonl
│   └── latest -> 20251110_130000
│
├── raw/                # Generated raw data
│   └── 20251110_100000/
│       ├── stage1.jsonl
│       ├── stage2.jsonl
│       └── stage3.jsonl
│
├── generation/         # Generation workspace (optional)
└── archive/            # Backups
    └── benchmark_backup_*/
```

---

## ❓ Common Questions

### Q: How to generate new benchmark?

A: Complete workflow:
```bash
./bench-cli generate
./bench-cli validate <id> --run-tests
./bench-cli promote <id>
```

### Q: How to run tests?

A: 
```bash
./bench-cli run --mode ollama -v
```

### Q: How to view latest test results?

A: 
```bash
./bench-cli show-result latest
```

### Q: Will promoting benchmark overwrite?

A: Yes, but the system automatically backs up to `bench/data/archive/`

### Q: How to restore old benchmark?

A: Copy from `bench/data/archive/benchmark_backup_*/` back to `bench/data/benchmark/`

### Q: Difference between Mock/Ollama/OpenAI modes?

A:
- **Mock**: Fastest, for quick validation, not realistic
- **Ollama**: Needs local models, realistic testing
- **OpenAI**: Needs API key, realistic testing

### Q: How to test only some samples?

A: Use filter parameters:
```bash
--filter "lang:zh"              # Chinese only
--schema-filter Encode,Retrieve # Specific operations only
```

---

# 中文

## 📋 目录

1. [快速开始](#快速开始-1)
2. [完整工作流](#完整工作流-1)
3. [命令参考](#命令参考-1)
4. [数据结构](#数据结构-1)
5. [常见问题](#常见问题-1)

---

## 🚀 快速开始

### 第一次使用

```bash
# 1. 查看 benchmark 信息
./bench-cli info

# 2. 运行快速测试（几秒钟）
./bench-cli run --mode mock -v

# 3. 查看结果
./bench-cli show-result latest
```

### 日常使用

```bash
# 完整测试
./bench-cli run --mode ollama -v

# 查看历史
./bench-cli list-results

# 对比结果
./bench-cli compare <id1> <id2>
```

---

## 🔄 完整工作流

### 流程 1: 日常测试

```bash
# 1. 查看 benchmark
./bench-cli info

# 2. 运行测试
./bench-cli run --mode ollama -v

# 3. 查看结果
./bench-cli show-result latest

# 4. 查看历史趋势
./bench-cli list-results
```

### 流程 2: 生成新 Benchmark

```bash
# 步骤 1: 编辑配置（可选）
nano bench/generate/config/generation_plan.yaml

# 步骤 2: 生成数据
./bench-cli generate

# 步骤 3: 验证质量
./bench-cli validate <generation_id>
./bench-cli validate <generation_id> --run-tests

# 步骤 4: 如果质量好，提升为正式 benchmark
./bench-cli promote <generation_id>

# 步骤 5: 测试新 benchmark
./bench-cli run --mode ollama -v
```

### 流程 3: 调试问题

```bash
# 只测试特定操作
./bench-cli run --schema-filter Encode -v

# 查看失败详情
./bench-cli show-result latest --show-failed

# 只测试中文
./bench-cli run --filter "lang:zh" -v
```

---

## 📖 命令参考

### `run` - 运行测试

```bash
./bench-cli run [OPTIONS]

选项:
  --mode MODE              测试模式: auto/mock/ollama/openai
  --filter EXPR            样本过滤: "lang:zh" 或 "lang:en"
  --schema-filter OPS      操作过滤: "Encode,Retrieve"
  --schema-indices IDS     索引过滤: "0,2"
  --timeout SECONDS        超时设置
  --output-id ID           结果 ID
  --verbose, -v            详细输出

示例:
  ./bench-cli run --mode mock -v              # Mock 快速测试
  ./bench-cli run --mode ollama -v            # Ollama 完整测试
  ./bench-cli run --filter "lang:zh" -v       # 只测中文
  ./bench-cli run --schema-filter Encode -v   # 只测 Encode
```

### `generate` - 生成新 benchmark

```bash
./bench-cli generate [OPTIONS]

选项:
  --config FILE            配置文件路径
  --output-id ID           输出 ID
  --use-generation-dir     使用 generation/ 目录

示例:
  ./bench-cli generate                        # 使用默认配置
  ./bench-cli generate --config my_plan.yaml  # 使用自定义配置
```

### `validate` - 验证数据

```bash
./bench-cli validate <generation_id> [OPTIONS]

选项:
  --run-tests              运行测试验证
  --verbose, -v            详细输出

示例:
  ./bench-cli validate 20251110_100000               # 快速统计
  ./bench-cli validate 20251110_100000 --run-tests   # 完整验证
```

### `promote` - 提升为 benchmark

```bash
./bench-cli promote <generation_id> [OPTIONS]

选项:
  --yes, -y                跳过确认
  --notes TEXT             备注信息

示例:
  ./bench-cli promote 20251110_100000                    # 提升（需确认）
  ./bench-cli promote 20251110_100000 -y                 # 跳过确认
  ./bench-cli promote 20251110_100000 --notes "v2.0"
```

**警告**: 此操作会替换当前 benchmark，但会自动备份到 `archive/`。

### `list-results` - 列出结果

```bash
./bench-cli list-results [--limit N]

示例:
  ./bench-cli list-results            # 显示最近 20 个
  ./bench-cli list-results --limit 5  # 显示最近 5 个
```

### `show-result` - 显示详情

```bash
./bench-cli show-result <result_id> [--show-failed]

示例:
  ./bench-cli show-result latest                 # 最新结果
  ./bench-cli show-result 20251110_130000        # 特定结果
  ./bench-cli show-result latest --show-failed   # 显示失败样本
```

### `compare` - 对比结果

```bash
./bench-cli compare <result_id1> <result_id2>

示例:
  ./bench-cli compare 20251110_130000 20251110_140000
```

### `info` - Benchmark 信息

```bash
./bench-cli info

显示当前 benchmark 的统计信息
```

---

## 📊 数据结构

### 完整目录结构

```
bench/data/
├── benchmark/          # 当前使用的 benchmark
│   ├── benchmark.jsonl # 测试样本
│   ├── metadata.json   # 元数据
│   └── stats.json      # 统计信息
│
├── results/            # 测试历史
│   ├── 20251110_130000/
│   │   ├── config.json
│   │   ├── report.json
│   │   ├── passed.jsonl
│   │   └── failed.jsonl
│   └── latest -> 20251110_130000
│
├── raw/                # 生成的原始数据
│   └── 20251110_100000/
│       ├── stage1.jsonl
│       ├── stage2.jsonl
│       └── stage3.jsonl
│
├── generation/         # 生成工作区（可选）
└── archive/            # 备份
    └── benchmark_backup_*/
```

---

## ❓ 常见问题

### Q: 如何生成新 benchmark？

A: 完整流程：
```bash
./bench-cli generate
./bench-cli validate <id> --run-tests
./bench-cli promote <id>
```

### Q: 如何运行测试？

A: 
```bash
./bench-cli run --mode ollama -v
```

### Q: 如何查看最新测试结果？

A: 
```bash
./bench-cli show-result latest
```

### Q: 提升 benchmark 会覆盖吗？

A: 会替换，但系统会自动备份到 `bench/data/archive/`

### Q: 如何恢复旧 benchmark？

A: 从 `bench/data/archive/benchmark_backup_*/` 复制回 `bench/data/benchmark/`

### Q: Mock/Ollama/OpenAI 模式的区别？

A:
- **Mock**: 最快，用于快速验证，不真实
- **Ollama**: 需要本地模型，真实测试
- **OpenAI**: 需要 API key，真实测试

### Q: 如何只测试部分样本？

A: 使用过滤参数：
```bash
--filter "lang:zh"              # 只测中文
--schema-filter Encode,Retrieve # 只测特定操作
```

---

<div align="center">

**System Version | 系统版本**: v1.0  
**Last Updated | 最后更新**: 2025-11-10

[⬆ Back to top | 返回顶部](#benchmark-system-complete-guide--benchmark-系统完整指南)

</div>

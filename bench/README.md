<div align="center">

# Text2Mem Benchmark System | Text2Mem 基准测试系统

**Complete benchmark testing system with generation, validation, testing, and management**  
**完整的 Benchmark 测试系统，支持生成、验证、测试、管理全流程**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## 🚀 Quick Start

```bash
# 1. View current benchmark
./bench-cli info

# 2. Run tests
./bench-cli run --mode mock -v

# 3. View results
./bench-cli show-result latest
```

---

## 📖 Core Features

### Daily Testing

```bash
./bench-cli run --mode ollama -v              # Full test
./bench-cli run --filter "lang:zh" -v         # Chinese only
./bench-cli run --schema-filter Encode -v     # Specific operation
```

### Generate New Benchmark

```bash
# Complete workflow: Generate → Validate → Promote
./bench-cli generate
./bench-cli validate <generation_id> --run-tests
./bench-cli promote <generation_id>
```

### Results Management

```bash
./bench-cli list-results                      # View history
./bench-cli show-result latest                # View details
./bench-cli compare <id1> <id2>               # Compare results
```

---

## 📊 Data Structure

```
bench/data/
├── benchmark/      # Current benchmark
├── results/        # Test history
├── raw/            # Generated raw data
└── archive/        # Backups
```

---

## 📚 Complete Documentation

- **[GUIDE.md](GUIDE.md)** - Complete usage guide ⭐
- **[TEST_REPORT.md](TEST_REPORT.md)** - Test report

---

## 🎯 All Commands

```bash
./bench-cli run              # Run tests
./bench-cli generate         # Generate new benchmark
./bench-cli validate <id>    # Validate quality
./bench-cli promote <id>     # Promote to benchmark
./bench-cli list-results     # List history
./bench-cli show-result <id> # View details
./bench-cli compare <id1> <id2>  # Compare
./bench-cli info             # Benchmark information
```

Each command supports `--help` to view detailed parameters.

---

# 中文

## 🚀 快速开始

```bash
# 1. 查看当前 benchmark
./bench-cli info

# 2. 运行测试
./bench-cli run --mode mock -v

# 3. 查看结果
./bench-cli show-result latest
```

---

## 📖 核心功能

### 日常测试

```bash
./bench-cli run --mode ollama -v              # 完整测试
./bench-cli run --filter "lang:zh" -v         # 只测中文
./bench-cli run --schema-filter Encode -v     # 测试特定操作
```

### 生成新 Benchmark

```bash
# 完整流程: 生成 → 验证 → 提升
./bench-cli generate
./bench-cli validate <generation_id> --run-tests
./bench-cli promote <generation_id>
```

### 结果管理

```bash
./bench-cli list-results                      # 查看历史
./bench-cli show-result latest                # 查看详情
./bench-cli compare <id1> <id2>               # 对比结果
```

---

## 📊 数据结构

```
bench/data/
├── benchmark/      # 当前 benchmark
├── results/        # 测试历史
├── raw/            # 生成的原始数据
└── archive/        # 备份
```

---

## 📚 完整文档

- **[GUIDE.md](GUIDE.md)** - 完整使用指南 ⭐
- **[TEST_REPORT.md](TEST_REPORT.md)** - 测试报告

---

## 🎯 所有命令

```bash
./bench-cli run              # 运行测试
./bench-cli generate         # 生成新 benchmark
./bench-cli validate <id>    # 验证质量
./bench-cli promote <id>     # 提升为 benchmark
./bench-cli list-results     # 列出历史
./bench-cli show-result <id> # 查看详情
./bench-cli compare <id1> <id2>  # 对比
./bench-cli info             # Benchmark 信息
```

每个命令都支持 `--help` 查看详细参数。

---

<div align="center">

**System Status | 系统状态**: ✅ Fully Available | 完整可用  
**Version | 版本**: v1.0  
**Last Updated | 最后更新**: 2025-11-10

[⬆ Back to top | 返回顶部](#text2mem-benchmark-system--text2mem-基准测试系统)

</div>

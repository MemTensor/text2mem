# Benchmark 系统重构方案

## 🎯 目标

1. **简化数据流程**: `generate → test → benchmark` (去掉中间冗余)
2. **清晰的版本管理**: 语义化版本 + 时间戳
3. **统一命令**: 一个入口完成所有操作
4. **可追溯性**: 完整的历史记录

---

## 📊 当前问题分析

### 问题 1: 数据冗余
```
当前: raw/ → runs/{id}/tests/ → runs/{id}/cleaned/ → benchmarks/v2/
      ↓        ↓                  ↓                   ↓
      原始     测试结果           清洗后              最终benchmark
```

**问题**: 
- `runs/` 和 `benchmarks/` 存储重复数据
- `v2` 版本号无语义，不知道对应哪个 raw

### 问题 2: 命令混乱
- `build_benchmark.py` - 一键构建
- `tools/pipeline.py` - 流程编排
- `tools/test.py` - 测试
- `tools/clean.py` - 清洗
- `tools/build.py` - 构建

**问题**: 职责重叠，用户不知道该用哪个

### 问题 3: 版本管理不清晰
- `v2` 是什么？和哪个 raw 对应？
- 无法知道生成配置和测试结果
- 无法追溯数据来源

---

## 🎨 新设计

### 核心理念
**一次生成 = 一个 Benchmark 版本**

### 新数据结构

```
bench/data/
├── benchmarks/                    # 核心：所有 benchmark 版本
│   ├── 20251110_120000/          # 基于生成时间的版本 ID
│   │   ├── metadata.json         # 元数据：生成配置、时间、状态
│   │   ├── benchmark.jsonl       # 最终测试数据
│   │   ├── stats.json            # 统计信息
│   │   ├── test_report.json      # 测试报告
│   │   └── raw/                  # 原始生成数据（可选保留）
│   │       ├── stage1.jsonl
│   │       ├── stage2.jsonl
│   │       └── stage3.jsonl
│   │
│   ├── 20251110_150000/          # 另一个版本
│   │   └── ...
│   │
│   ├── latest -> 20251110_150000 # 符号链接：最新版本
│   ├── stable -> 20251110_120000 # 符号链接：稳定版本
│   └── dev -> 20251110_150000    # 符号链接：开发版本
│
├── archive/                       # 归档的旧版本（可选）
│   └── 20251022_184604/
│
└── schema/                        # Schema 定义
    └── test-sample-schema-v1.json
```

**删除**: `raw/` 和 `runs/` 目录（合并到 benchmarks）

### metadata.json 格式

```json
{
  "id": "20251110_120000",
  "version": "1.0.0",               // 语义化版本（可选）
  "name": "Q4 Feature Complete",   // 可读名称（可选）
  "created_at": "2025-11-10T12:00:00Z",
  "status": "stable",               // draft | testing | stable | archived
  
  "generation": {
    "config_file": "generation_plan.yaml",
    "config_hash": "abc123...",     // 配置文件哈希
    "total_samples": 2000,
    "llm_provider": "openai",
    "llm_model": "gpt-4o"
  },
  
  "test_results": {
    "total_samples": 2000,
    "passed": 1163,
    "failed": 837,
    "pass_rate": 0.582,
    "test_duration": 1234.56
  },
  
  "cleaning": {
    "rules_applied": ["filter_failed", "filter_unknown"],
    "samples_before": 2000,
    "samples_after": 1163,
    "filter_report": {...}
  },
  
  "tags": ["chinese", "full-coverage", "v1.0"],
  "notes": "Initial benchmark for v1.0 release"
}
```

---

## 🚀 新命令设计

### 统一入口: `bench-cli`

```bash
# 完整流程：生成 → 测试 → 构建
bench-cli build [OPTIONS]

# 只测试现有数据
bench-cli test <benchmark_id> [OPTIONS]

# 管理命令
bench-cli list              # 列出所有版本
bench-cli info <id>         # 查看版本详情
bench-cli link <id> <name>  # 创建符号链接
bench-cli archive <id>      # 归档版本
bench-cli clean             # 清理临时文件

# 生成命令
bench-cli generate [OPTIONS]  # 只生成数据（调试用）
```

### 命令详解

#### 1. `bench-cli build` - 构建新 benchmark

```bash
# 默认：使用当前配置，自动生成版本 ID
bench-cli build

# 指定版本号和名称
bench-cli build --version 1.0.0 --name "Q4 Release"

# 只使用现有生成数据（跳过生成）
bench-cli build --from-raw bench/data/archive/20251022_184604

# 自定义配置
bench-cli build --config custom_plan.yaml

# 快速测试（小样本）
bench-cli build --samples 100 --quick

# 输出选项
bench-cli build --output-dir custom/path --keep-raw
```

**执行流程**:
1. 读取配置 (generation_plan.yaml)
2. 生成数据 (stage1 → stage2 → stage3)
3. 运行测试
4. 过滤和清洗
5. 生成最终 benchmark
6. 保存元数据和报告
7. 更新 `latest` 符号链接

**输出**:
```
✓ 生成完成: 2000 samples
✓ 测试完成: 1163/2000 passed (58.2%)
✓ 清洗完成: 1163 samples retained
✓ Benchmark 已保存: bench/data/benchmarks/20251110_120000/
✓ 符号链接已更新: latest -> 20251110_120000

Benchmark ID: 20251110_120000
路径: bench/data/benchmarks/20251110_120000/
文件: benchmark.jsonl (1163 samples)

下一步:
  bench-cli test 20251110_120000 --verbose    # 验证 benchmark
  bench-cli link 20251110_120000 stable      # 标记为稳定版
```

#### 2. `bench-cli test` - 测试 benchmark

```bash
# 测试最新版本
bench-cli test latest

# 测试特定版本
bench-cli test 20251110_120000

# 过滤测试
bench-cli test latest --filter "lang:zh"
bench-cli test latest --schema-filter Encode,Retrieve
bench-cli test latest --limit 10

# 详细输出
bench-cli test latest --verbose --output report.json
```

#### 3. `bench-cli list` - 列出版本

```bash
bench-cli list

# 输出示例:
ID                Status    Samples  Pass Rate  Created
20251110_150000  stable    1163     58.2%      2025-11-10 15:00
20251110_120000  testing   1050     52.5%      2025-11-10 12:00
20251022_184604  archived  837      41.9%      2025-10-22 18:46

Aliases:
  latest -> 20251110_150000
  stable -> 20251110_150000
  dev    -> 20251110_120000
```

#### 4. `bench-cli info` - 查看详情

```bash
bench-cli info latest

# 输出示例:
Benchmark: 20251110_150000
Status: stable
Created: 2025-11-10 15:00:00

Generation:
  Config: generation_plan.yaml
  Total: 2000 samples
  LLM: openai/gpt-4o

Test Results:
  Passed: 1163/2000 (58.2%)
  Duration: 20m 34s

Distribution:
  Languages: zh (50%), en (50%)
  Operations: Encode (20%), Retrieve (12%), ...
  Structures: single (90%), workflow (10%)

Files:
  benchmark.jsonl  (1163 samples, 4.2 MB)
  test_report.json (detailed results)
  stats.json       (statistics)
```

#### 5. `bench-cli link` - 管理符号链接

```bash
# 设置稳定版本
bench-cli link 20251110_150000 stable

# 设置开发版本
bench-cli link 20251110_120000 dev

# 删除链接
bench-cli link --remove stable
```

---

## 🔄 迁移计划

### 步骤 1: 创建新工具

```bash
# 新建核心文件
bench/
├── cli.py                  # 新的统一 CLI 入口
├── core/
│   ├── benchmark_manager.py  # Benchmark 管理器
│   └── builder.py            # 构建器（整合 generate + test + clean）
```

### 步骤 2: 迁移现有数据

```bash
# 创建迁移脚本
python bench/migrate.py

# 执行迁移
bench/data/runs/20251022_184604/ → bench/data/benchmarks/20251022_184604/
bench/data/benchmarks/v2/        → 删除（已合并）
```

### 步骤 3: 更新文档

- 更新 README.md
- 更新 GUIDE.md
- 添加迁移指南

### 步骤 4: 废弃旧命令

保留旧命令但显示废弃警告：

```bash
python bench/build_benchmark.py
# ⚠️  Warning: This command is deprecated. Use 'bench-cli build' instead.
```

---

## 📋 实施检查清单

- [ ] 创建 `bench/cli.py` (统一 CLI)
- [ ] 创建 `bench/core/benchmark_manager.py`
- [ ] 创建 `bench/core/builder.py`
- [ ] 更新数据结构
- [ ] 创建迁移脚本 `bench/migrate.py`
- [ ] 更新文档
- [ ] 添加测试
- [ ] 废弃旧命令

---

## 🎯 预期效果

### 用户体验
**之前**:
```bash
# 用户需要记住多个命令
python bench/generate/generate.py
python -m bench.tools.test --raw latest
python -m bench.tools.clean --run latest
python -m bench.tools.build --run latest --version v2  # v2 是什么？
python -m bench run --split benchmark
```

**之后**:
```bash
# 一个命令完成所有操作
bench-cli build

# 或者从现有数据构建
bench-cli build --from-raw 20251022_184604

# 测试
bench-cli test latest --verbose
```

### 数据组织
**之前**:
```
bench/data/
├── raw/20251022_184604/
├── runs/20251022_184604/
└── benchmarks/v2/          # v2 和 raw 的关系不清晰
```

**之后**:
```
bench/data/benchmarks/
├── 20251110_120000/        # 清晰：一个版本 = 完整历史
│   ├── benchmark.jsonl
│   ├── metadata.json       # 记录所有信息
│   └── raw/                # 原始数据（可选）
├── latest -> 20251110_120000
└── stable -> 20251110_120000
```

---

## 💡 额外优化

### 1. 配置模板

```bash
# 初始化配置
bench-cli init --template quick    # 快速测试配置
bench-cli init --template full     # 完整配置
bench-cli init --template chinese  # 中文重点配置
```

### 2. 对比功能

```bash
# 对比两个版本
bench-cli diff 20251110_120000 20251110_150000

# 输出:
Benchmark Comparison:
  Left:  20251110_120000 (1050 samples)
  Right: 20251110_150000 (1163 samples)

Changes:
  + 113 samples added
  Pass rate: 52.5% → 58.2% (+5.7%)
  
Operation distribution changes:
  Encode: 210 → 314 (+104)
  Retrieve: 126 → 152 (+26)
  ...
```

### 3. 导出功能

```bash
# 导出为标准格式
bench-cli export 20251110_120000 --format huggingface
bench-cli export 20251110_120000 --format jsonl --split train:test=0.8:0.2
```

---

这个方案怎么样？我可以开始实施了吗？或者你有什么建议？

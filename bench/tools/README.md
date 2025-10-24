# Bench Tools - 工具集合

Text2Mem Benchmark 的核心工具集，用于数据生成、测试、清洗和构建。

## 📁 工具结构

```
bench/tools/
├── 核心工具（数据处理流程）
│   ├── run_manager.py      # Run目录管理（核心模块）
│   ├── test.py             # 测试运行器
│   ├── clean.py            # 数据清洗
│   ├── build.py            # Benchmark构建
│   ├── pipeline.py         # 完整流程
│   └── stats.py            # 统计分析
│
├── 实用工具
│   ├── clock.py                # 虚拟时钟
│   ├── sql_builder_sqlite.py   # SQL构建器
│   └── create_empty_db.py      # 创建空数据库
│
└── _archive/               # 归档的旧工具
```

## 🚀 快速开始

### 一键完整流程（推荐）

```bash
# 从最新raw数据生成benchmark
python -m bench.tools.pipeline --raw latest --version v2

# 从指定raw生成
python -m bench.tools.pipeline --raw 20251022_184604 --version v2
```

### 分步执行（高级用法）

```bash
# 1. 测试 - 从raw创建run并运行测试
python -m bench.tools.test --raw latest

# 2. 清洗 - 过滤失败样本，应用规则
python -m bench.tools.clean --run latest

# 3. 构建 - 重新分配ID，生成最终benchmark
python -m bench.tools.build --run latest --version v2

# 4. 统计 - 分析样本分布和质量
python -m bench.tools.stats --run latest
```

## 📋 工具详解

### 核心工具

#### 1. run_manager.py - Run目录管理

核心模块，负责管理数据目录结构。

```python
from bench.tools.run_manager import RunManager

manager = RunManager()
latest_raw = manager.get_latest_raw()
run_dir = manager.create_run_from_raw(latest_raw)
```

**目录结构**:
- `raw/` - 原始生成输出
- `runs/` - 测试和清洗后的数据
- `benchmarks/` - 最终benchmark

#### 2. test.py - 测试运行器

从raw创建run并运行测试，识别通过/失败的样本。

```bash
# 从最新raw创建run并测试
python -m bench.tools.test --raw latest

# 从指定raw创建run
python -m bench.tools.test --raw 20251022_184604

# 测试已存在的run
python -m bench.tools.test --run 20251022_184604

# 只测试前N个样本（调试用）
python -m bench.tools.test --raw latest --limit 10
```

**输出**:
- `runs/{RUN_ID}/tests/passed.jsonl` - 通过的样本
- `runs/{RUN_ID}/tests/failed.jsonl` - 失败的样本
- `runs/{RUN_ID}/tests/summary.json` - 测试摘要

#### 3. clean.py - 数据清洗

从测试结果中筛选样本，应用过滤规则。

```bash
# 清洗最新run
python -m bench.tools.clean --run latest

# 清洗指定run
python -m bench.tools.clean --run 20251022_184604

# 不过滤unknown字段
python -m bench.tools.clean --run latest --no-filter-unknown

# 不过滤失败样本
python -m bench.tools.clean --run latest --no-filter-failed
```

**过滤规则**:
1. 过滤测试失败的样本（如果有测试结果）
2. 过滤包含'unknown'的样本
3. 只保留'direct'和'indirect'指令类型
4. 只保留'single'和'workflow'结构
5. 只保留12种核心操作

**输出**:
- `runs/{RUN_ID}/cleaned/cleaned.jsonl` - 清洗后的样本
- `runs/{RUN_ID}/cleaned/metadata.json` - 元数据
- `runs/{RUN_ID}/cleaned/filter_report.json` - 过滤报告

#### 4. build.py - Benchmark构建

从清洗后的数据构建最终benchmark。

```bash
# 从最新run构建benchmark
python -m bench.tools.build --run latest --version v2

# 从指定run构建
python -m bench.tools.build --run 20251022_184604 --version v2

# 不重新分配ID
python -m bench.tools.build --run latest --version v2 --no-rebuild-ids
```

**功能**:
- 重新分配样本ID（按分类分组）
- 生成元数据和统计信息
- 支持版本管理

**输出**:
- `benchmarks/{VERSION}/benchmark.jsonl` - 最终benchmark
- `benchmarks/{VERSION}/metadata.json` - 元数据
- `benchmarks/{VERSION}/stats.json` - 统计信息

#### 5. pipeline.py - 完整流程

自动化执行完整的数据处理流程。

```bash
# 处理最新raw
python -m bench.tools.pipeline --raw latest --version v2

# 处理指定raw
python -m bench.tools.pipeline --raw 20251022_184604 --version v2

# 跳过测试步骤（run必须已存在）
python -m bench.tools.pipeline --raw latest --version v2 --skip-tests

# 显示详细输出
python -m bench.tools.pipeline --raw latest --version v2 --verbose
```

**流程**:
1. 运行测试（创建run）
2. 清洗数据
3. 构建benchmark

#### 6. stats.py - 统计分析

分析样本分布和质量指标。

```bash
# 统计最新run
python -m bench.tools.stats --run latest

# 统计指定run
python -m bench.tools.stats --run 20251022_184604

# 统计指定文件
python -m bench.tools.stats --input stage3.jsonl

# 生成详细报告
python -m bench.tools.stats --run latest --verbose

# 保存报告到指定文件
python -m bench.tools.stats --run latest --output report.json
```

**统计内容**:
- 样本分布（语言、操作、指令类型、结构）
- 质量指标（完整性、有效性）
- 问题检测（unknown字段、缺失字段）
- Top组合统计

### 实用工具

#### 7. clock.py - 虚拟时钟

用于基准测试中的时间模拟。

```python
from bench.tools.clock import VirtualClock

clock = VirtualClock()
# 用于模拟时间相关的操作
```

#### 8. sql_builder_sqlite.py - SQL构建器

编译测试断言为SQL查询。

```python
from bench.tools.sql_builder_sqlite import SQLiteAssertionCompiler

compiler = SQLiteAssertionCompiler()
compiled = compiler.compile(assertion)
```

#### 9. create_empty_db.py - 创建空数据库

创建Text2Mem标准空数据库。

```bash
# 创建内存数据库（测试用）
python bench/tools/create_empty_db.py

# 创建文件数据库
python bench/tools/create_empty_db.py --output /path/to/database.db

# 验证schema
python bench/tools/create_empty_db.py --verify /path/to/database.db
```

## 📊 数据流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Benchmark 数据流程                        │
└─────────────────────────────────────────────────────────────┘

1. Generate (生成)
   └─> bench/data/raw/{TIMESTAMP}/
       ├── stage1.jsonl  (NL指令)
       ├── stage2.jsonl  (IR样本)
       └── stage3.jsonl  (完整样本)

2. Test (测试)
   └─> bench/data/runs/{TIMESTAMP}/tests/
       ├── passed.jsonl   (通过的样本)
       ├── failed.jsonl   (失败的样本)
       └── summary.json   (测试摘要)

3. Clean (清洗)
   └─> bench/data/runs/{TIMESTAMP}/cleaned/
       ├── cleaned.jsonl       (清洗后的样本)
       ├── metadata.json       (元数据)
       └── filter_report.json  (过滤报告)

4. Build (构建)
   └─> bench/data/benchmarks/{VERSION}/
       ├── benchmark.jsonl  (最终benchmark)
       ├── metadata.json    (元数据)
       └── stats.json       (统计信息)
```

## 🔧 高级用法

### 自定义过滤规则

修改 `clean.py` 中的过滤规则：

```python
class DataCleaner:
    ALLOWED_INSTRUCTION_TYPES = {'direct', 'indirect'}
    ALLOWED_STRUCTURES = {'single', 'workflow'}
    ALLOWED_OPERATIONS = {
        'Encode', 'Retrieve', 'Update', 'Delete', 
        'Summarize', 'Label', 'Promote', 'Demote',
        'Expire', 'Lock', 'Merge', 'Split',
    }
```

### 批量处理多个raw

```bash
# 处理所有raw
for raw in bench/data/raw/*/; do
    raw_id=$(basename $raw)
    python -m bench.tools.pipeline --raw $raw_id --version "v_$raw_id"
done
```

### 比较不同版本的benchmark

```bash
# 统计v1
python -m bench.tools.stats --input bench/data/benchmarks/v1/benchmark.jsonl

# 统计v2
python -m bench.tools.stats --input bench/data/benchmarks/v2/benchmark.jsonl
```

## 📝 常见问题

### Q: 如何从头开始生成新的benchmark？

```bash
# 1. 生成原始数据
python bench/generate/generate.py

# 2. 运行完整流程
python -m bench.tools.pipeline --raw latest --version v2
```

### Q: 如何只重新测试而不生成新数据？

```bash
# 从已有raw重新测试
python -m bench.tools.test --raw 20251022_184604
```

### Q: 如何调试测试失败？

```bash
# 1. 只测试前几个样本
python -m bench.tools.test --raw latest --limit 5 --verbose

# 2. 查看失败样本
cat bench/data/runs/latest/tests/failed.jsonl
```

### Q: 如何自定义benchmark版本号？

```bash
# 使用自定义版本号
python -m bench.tools.pipeline --raw latest --version v2.1-custom
```

## 📚 相关文档

- [Benchmark README](../README.md) - 总体说明
- [生成工具文档](../generate/QUICK_REFERENCE.md) - 数据生成
- [工作流文档](../WORKFLOW.md) - 完整工作流程

## 🗂️ 归档工具

已归档的工具保存在 `_archive/` 目录中，包括：
- `clean_benchmark.py` - 旧版清洗工具
- `migrate_data.py` - 数据结构迁移脚本
- `migrate_to_v3.py` - v3迁移脚本
- `verify_setup.py` - 设置验证工具

详见 [_archive/README.md](_archive/README.md)

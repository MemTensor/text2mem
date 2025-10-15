# Bench 目录说明

## 📖 简介

Bench 是 Text2Mem 的测试框架，用于生成、管理和运行测试样本。

## 📁 目录结构

```
bench/
├── core/               # 测试引擎
│   ├── cli.py         # 命令行接口
│   ├── runner.py      # 测试运行器
│   └── metrics/       # 评估指标
│
├── generate/           # 样本生成器
│   ├── generate.py    # 生成入口
│   ├── config/        # 生成配置
│   ├── prompts/       # LLM 提示词
│   ├── seeds/         # 种子数据
│   └── src/           # 生成器源码
│
├── tools/              # 工具脚本
│   ├── clean_benchmark.py    # 清洗 benchmark
│   ├── clock.py              # 虚拟时钟
│   ├── create_empty_db.py    # 创建空数据库
│   └── sql_builder_sqlite.py # SQL 构建器
│
├── data/               # 数据目录 ⭐
│   ├── schemas/       # Schema 定义
│   ├── raw/           # 原始生成输出
│   ├── test_data/     # 测试数据
│   └── benchmark/     # 最终 benchmark
│       ├── v1/
│       └── latest -> v1/
│
└── output/             # 临时输出
    ├── test_results/  # 测试结果
    ├── logs/          # 日志文件
    └── tmp/           # 临时文件
```

## 🔄 数据流程

```
1. Generate (生成样本)
   python bench/generate/generate.py
   ↓ 输出到
   bench/data/raw/YYYYMMDD_HHMMSS/
   ├── stage1.jsonl  # NL指令
   ├── stage2.jsonl  # IR Schema
   ├── stage3.jsonl  # 完整样本
   └── metadata.json

2. Process (处理数据)
   cp data/raw/20251015_131147/stage3.jsonl data/test_data/test_data.jsonl
   或使用处理脚本

3. Clean (清洗过滤)
   python bench/tools/clean_benchmark.py
   ↓ 输出到
   bench/data/benchmark/v1/benchmark.jsonl

4. Test (运行测试)
   python -m bench run --split basic
   ↓ 输出到
   bench/output/test_results/
```

## 🚀 快速开始

### 生成测试样本

```bash
# 基础生成
python bench/generate/generate.py

# 异步生成（更快）
python bench/generate/generate.py --async --max-concurrent 5

# 指定配置文件
python bench/generate/generate.py --plan bench/generate/config/generation_plan.yaml
```

生成的文件会自动保存到 `bench/data/raw/YYYYMMDD_HHMMSS/`

### 处理测试数据

```bash
# 从最新的 raw 复制到 test_data
LATEST=$(ls -t bench/data/raw | head -1)
cp bench/data/raw/$LATEST/stage3.jsonl bench/data/test_data/test_data.jsonl
```

### 清洗 Benchmark

```bash
# 使用默认配置
python bench/tools/clean_benchmark.py

# 指定输入输出
python bench/tools/clean_benchmark.py \
    --input bench/data/test_data/test_data.jsonl \
    --output bench/data/benchmark/v1/benchmark.jsonl
```

### 运行测试

```bash
# 列出测试样本
python -m bench list --split basic

# 运行所有测试
python -m bench run --split basic

# 运行特定测试
python -m bench run --split basic --filter "lang:zh"

# 详细输出
python -m bench run --split basic --verbose
```

## 🔧 工具说明

### generate.py - 样本生成器

生成三个阶段的测试样本：
- Stage 1: 生成自然语言指令
- Stage 2: 生成 IR Schema
- Stage 3: 生成完整样本（包含 expected 结果）

**配置文件**: `bench/generate/config/generation_plan.yaml`

### clean_benchmark.py - Benchmark 清洗器

过滤和清洗测试数据：
- 删除包含 'unknown' 的样本
- 只保留 'direct' 和 'indirect' 指令类型
- 只保留 'single' 和 'workflow' 结构
- 只保留核心操作（Encode, Retrieve, Update, Delete 等）

### core/runner.py - 测试运行器

运行测试并生成报告：
- 初始化数据库
- 执行测试步骤
- 验证断言
- 计算评估指标（Recall@k, MRR 等）

## 📝 数据管理

### raw/ 目录

保留最近 3-5 次生成即可：

```bash
# 清理旧数据
cd bench/data/raw
ls -t | tail -n +4 | xargs rm -rf
```

### test_data/ 目录

中间测试数据，可以从 raw/ 重新生成：

```bash
# 更新测试数据
LATEST=$(ls -t bench/data/raw | head -1)
cp bench/data/raw/$LATEST/stage3.jsonl bench/data/test_data/test_data.jsonl
```

### benchmark/ 目录

最终 benchmark 版本，使用版本管理：

```bash
# 创建新版本
mkdir -p bench/data/benchmark/v2
python bench/tools/clean_benchmark.py \
    --output bench/data/benchmark/v2/benchmark.jsonl

# 更新 latest 链接
cd bench/data/benchmark
ln -sf v2 latest
```

## 🎯 常见任务

### 完整的生成到测试流程

```bash
# 1. 生成样本
python bench/generate/generate.py

# 2. 获取最新生成
LATEST=$(ls -t bench/data/raw | head -1)
echo "最新生成: $LATEST"

# 3. 复制到 test_data
cp bench/data/raw/$LATEST/stage3.jsonl bench/data/test_data/test_data.jsonl

# 4. 清洗生成 benchmark
python bench/tools/clean_benchmark.py

# 5. 运行测试
python -m bench run --split basic --verbose
```

### 查看生成统计

```bash
# 查看最新生成的元数据
LATEST=$(ls -t bench/data/raw | head -1)
cat bench/data/raw/$LATEST/metadata.json | python -m json.tool
```

### 查看 benchmark 统计

```bash
# 统计样本数量
wc -l bench/data/benchmark/v1/benchmark.jsonl

# 查看样本分布
cat bench/data/benchmark/v1/benchmark.jsonl | jq '.class' | sort | uniq -c
```

## ⚙️ 配置文件

### generation_plan.yaml

生成计划配置，包括：
- LLM 配置（provider, model）
- 生成数量和比例
- 场景和操作分布
- 断点恢复设置

### test-sample-schema-v1.json

测试样本的 JSON Schema，定义样本的结构和字段要求。

## 📊 输出文件

### 测试结果

测试结果保存在 `bench/output/test_results/results_*.json`：

```json
{
  "summary": {
    "total": 100,
    "passed": 95,
    "failed": 5,
    "success_rate": 0.95
  },
  "metrics": {
    "recall@5": 0.92,
    "mrr": 0.85
  },
  "failed_tests": [...]
}
```

### 日志文件

日志保存在 `bench/output/logs/`：
- 生成日志
- 测试执行日志
- 错误日志

## 🔍 故障排查

### 生成失败

```bash
# 检查 LLM 连接
python bench/generate/generate.py --help

# 查看断点状态
cat bench/generate/checkpoints/*.json

# 重置断点
rm bench/generate/checkpoints/*.json
```

### 测试失败

```bash
# 查看详细日志
python -m bench run --split basic --verbose

# 查看失败的测试
cat bench/output/test_results/results_*.json | jq '.failed_tests'
```

### 数据问题

```bash
# 验证 JSONL 格式
cat bench/data/test_data/test_data.jsonl | jq empty

# 统计样本数量
wc -l bench/data/test_data/test_data.jsonl
```

## 📚 更多信息

- **快速开始**: 查看 [QUICK_START.md](QUICK_START.md)
- **使用指南**: 查看 [USAGE.md](USAGE.md)
- **源码文档**: 查看各模块的 docstring
- **配置说明**: 查看 `bench/generate/config/README.md`

## 🤝 贡献

如需添加新的测试场景或操作：
1. 更新 `bench/generate/seeds/scenarios.yaml` 和 `operations.yaml`
2. 更新 `bench/generate/config/generation_plan.yaml` 中的分布比例
3. 重新生成测试样本

---

**需要帮助？** 查看 [QUICK_START.md](QUICK_START.md) 或 [USAGE.md](USAGE.md)

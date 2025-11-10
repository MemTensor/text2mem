# Benchmark 系统重新设计方案

## 🎯 核心概念澄清

### 1. Benchmark (基准测试集)
- **定义**: 稳定的、版本化的标准测试数据集
- **用途**: 评估 Text2Mem 系统的性能
- **变更频率**: 很少（类似数据集的版本发布）
- **存储位置**: `bench/data/benchmarks/`

### 2. Test Results (测试结果)
- **定义**: 对 benchmark 运行测试产生的结果
- **用途**: 记录系统在不同配置下的表现
- **变更频率**: 频繁（每次测试都会产生）
- **存储位置**: `bench/data/results/`

### 3. Generation (生成过程)
- **定义**: 使用 LLM 生成测试样本的中间过程
- **用途**: 创建 benchmark 的原材料
- **变更频率**: 按需（想要新 benchmark 时）
- **存储位置**: `bench/data/generation/`

---

## 📊 新的数据结构

```
bench/data/
│
├── benchmarks/                    # 标准测试集（稳定、版本化）
│   ├── v1/
│   │   ├── benchmark.jsonl        # 测试数据
│   │   ├── metadata.json          # 版本信息
│   │   └── stats.json             # 数据统计
│   ├── v2/
│   │   ├── benchmark.jsonl
│   │   ├── metadata.json
│   │   └── stats.json
│   ├── v3/
│   └── latest -> v2               # 当前使用的版本
│
├── results/                       # 测试运行结果（频繁）
│   ├── 20251110_120000/           # 某次测试运行
│   │   ├── config.json            # 运行配置
│   │   │   {
│   │   │     "benchmark_version": "v2",
│   │   │     "mode": "ollama",
│   │   │     "timestamp": "...",
│   │   │     "filters": {...}
│   │   │   }
│   │   ├── report.json            # 测试报告
│   │   │   {
│   │   │     "total": 1163,
│   │   │     "passed": 980,
│   │   │     "failed": 183,
│   │   │     "pass_rate": 0.842,
│   │   │     "duration": 1234.5
│   │   │   }
│   │   ├── passed.jsonl           # 通过的测试 ID
│   │   ├── failed.jsonl           # 失败的测试及错误
│   │   └── details/               # 详细结果（可选）
│   │       ├── t2m-zh-*.json
│   │       └── ...
│   │
│   ├── 20251110_130000/           # 另一次测试
│   └── latest -> 20251110_120000
│
└── generation/                    # 生成过程（中间数据）
    ├── 20251110_100000/           # 某次生成
    │   ├── config.yaml            # 生成配置
    │   ├── raw/                   # 原始生成
    │   │   ├── stage1.jsonl
    │   │   ├── stage2.jsonl
    │   │   └── stage3.jsonl
    │   ├── validation/            # 验证结果
    │   │   ├── passed.jsonl
    │   │   ├── failed.jsonl
    │   │   └── report.json
    │   ├── filtered.jsonl         # 清洗后的候选数据
    │   └── metadata.json          # 生成元数据
    │
    └── latest -> 20251110_100000
```

---

## 🔄 工作流程

### Workflow 1: 创建新 Benchmark（不频繁）

```bash
# 步骤 1: 生成候选数据
bench-cli generate \
  --samples 2000 \
  --config generation_plan.yaml \
  --output-id 20251110_100000

# 输出: bench/data/generation/20251110_100000/

# 步骤 2: 验证生成的数据质量
bench-cli validate-generation 20251110_100000

# 输出: generation/20251110_100000/validation/

# 步骤 3: 提升为正式 benchmark
bench-cli promote \
  --from generation/20251110_100000 \
  --to benchmark/v3 \
  --name "2024 Q4 Release"

# 输出: bench/data/benchmarks/v3/

# 步骤 4: 设置为当前 benchmark
bench-cli use-benchmark v3
```

### Workflow 2: 运行测试（频繁）

```bash
# 使用当前 benchmark 运行测试
bench-cli run --mode ollama

# 指定 benchmark 版本
bench-cli run --benchmark v2 --mode ollama

# 过滤测试
bench-cli run \
  --benchmark v2 \
  --filter "lang:zh" \
  --schema-filter Encode,Retrieve

# 输出: bench/data/results/YYYYMMDD_HHMMSS/
```

### Workflow 3: 查看和对比结果

```bash
# 列出所有测试结果
bench-cli list-results

# 查看某次测试的详细结果
bench-cli show-result 20251110_120000

# 对比两次测试
bench-cli compare \
  results/20251110_120000 \
  results/20251110_130000

# 对比不同模式下的性能
bench-cli compare-modes \
  --benchmark v2 \
  --modes mock,ollama,openai
```

### Workflow 4: 管理 Benchmarks

```bash
# 列出所有 benchmark 版本
bench-cli list-benchmarks

# 查看 benchmark 详情
bench-cli info-benchmark v2

# 对比两个 benchmark 版本
bench-cli compare-benchmarks v1 v2

# 归档旧版本
bench-cli archive-benchmark v1
```

---

## 🎯 命令重新设计

### 核心命令

```bash
bench-cli generate         # 生成候选数据
bench-cli validate-generation  # 验证生成质量
bench-cli promote          # 提升为正式 benchmark
bench-cli run              # 运行测试
bench-cli compare          # 对比结果
bench-cli list-benchmarks  # 列出 benchmarks
bench-cli list-results     # 列出测试结果
```

### 详细用法

```bash
# ========== 生成 Benchmark ==========
bench-cli generate [OPTIONS]
  --samples N              # 样本数量
  --config FILE            # 配置文件
  --output-id ID           # 输出 ID（默认时间戳）

bench-cli validate-generation <generation_id>
  --verbose                # 详细输出

bench-cli promote [OPTIONS]
  --from generation/<id>   # 源数据
  --to benchmark/<version> # 目标版本
  --name "NAME"            # 版本名称

# ========== 运行测试 ==========
bench-cli run [OPTIONS]
  --benchmark VERSION      # Benchmark 版本（默认 latest）
  --mode MODE              # 模式: mock/ollama/openai
  --filter EXPR            # 样本过滤
  --schema-filter OPS      # 操作过滤
  --output-id ID           # 结果 ID（默认时间戳）

# ========== 查看结果 ==========
bench-cli list-results
  --benchmark VERSION      # 只显示特定 benchmark 的结果
  --limit N                # 限制数量

bench-cli show-result <result_id>
  --verbose                # 详细输出
  --show-failed            # 显示失败的测试

bench-cli compare <result_id1> <result_id2>

# ========== 管理 Benchmarks ==========
bench-cli list-benchmarks

bench-cli info-benchmark <version>

bench-cli use-benchmark <version>  # 设置为当前版本

bench-cli archive-benchmark <version>
```

---

## 📦 数据格式

### benchmarks/v2/metadata.json

```json
{
  "version": "v2",
  "name": "2024 Q3 Release",
  "created_at": "2024-10-22T18:46:04Z",
  "status": "stable",
  
  "source": {
    "generation_id": "20251022_184604",
    "generation_config": "generation_plan.yaml",
    "llm_provider": "openai",
    "llm_model": "gpt-4o"
  },
  
  "statistics": {
    "total_samples": 1163,
    "languages": {"zh": 581, "en": 582},
    "operations": {"Encode": 314, "Retrieve": 152, ...},
    "structures": {"single": 1109, "workflow": 54}
  },
  
  "validation": {
    "validated_at": "2024-10-22T19:00:00Z",
    "pass_rate": 1.0,
    "quality_score": 0.95
  },
  
  "tags": ["production", "chinese-support", "full-coverage"],
  "notes": "Initial production benchmark with Chinese support"
}
```

### results/20251110_120000/config.json

```json
{
  "result_id": "20251110_120000",
  "benchmark_version": "v2",
  "benchmark_samples": 1163,
  
  "test_config": {
    "mode": "ollama",
    "embedding_model": "nomic-embed-text",
    "generation_model": "qwen2:0.5b",
    "filters": {
      "lang": null,
      "schema_filter": null
    }
  },
  
  "environment": {
    "text2mem_version": "0.2.0",
    "python_version": "3.10.12",
    "hostname": "research-server"
  },
  
  "timestamp": "2025-11-10T12:00:00Z"
}
```

### results/20251110_120000/report.json

```json
{
  "summary": {
    "total": 1163,
    "passed": 980,
    "failed": 183,
    "pass_rate": 0.842,
    "duration": 1234.5
  },
  
  "by_operation": {
    "Encode": {"total": 314, "passed": 298, "failed": 16},
    "Retrieve": {"total": 152, "passed": 145, "failed": 7},
    ...
  },
  
  "by_language": {
    "zh": {"total": 581, "passed": 489, "failed": 92},
    "en": {"total": 582, "passed": 491, "failed": 91}
  },
  
  "top_failures": [
    {"sample_id": "t2m-zh-...", "error": "...", "count": 5},
    ...
  ]
}
```

---

## 🔄 迁移方案

### 当前状态

```
bench/data/benchmarks/
├── 20251022_184604/    # 这实际上是一次"生成+测试"的混合
│   ├── benchmark.jsonl
│   ├── metadata.json
│   ├── stats.json
│   ├── test_report.json
│   └── raw/
└── v2/
    └── benchmark.jsonl  # 真正的 benchmark
```

### 迁移步骤

```bash
# 1. 保留 v2 作为正式 benchmark
mv bench/data/benchmarks/v2 bench/data/benchmarks/v2_backup

# 2. 重新组织
bench-cli migrate-to-new-structure

# 这会:
# - 保留 v2/benchmark.jsonl 作为正式 benchmark
# - 将 20251022_184604 移到 generation/
# - 创建新的目录结构
```

---

## 💡 关键优势

1. **概念清晰**: Benchmark ≠ Test Results
2. **职责分离**: 生成、验证、测试、对比各司其职
3. **可追溯**: 每个 benchmark 记录来源，每次测试记录配置
4. **易对比**: 可以轻松对比不同模式、不同版本的性能
5. **版本化**: Benchmark 像数据集一样有明确版本

---

这个设计怎么样？我可以开始实施吗？


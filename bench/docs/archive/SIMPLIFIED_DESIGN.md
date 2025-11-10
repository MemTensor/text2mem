# Benchmark 系统简化方案

## 🎯 核心理念

**一个稳定的 Benchmark + 多次测试结果**

- `benchmark.jsonl` - 唯一的标准测试集（你现有的 v2/benchmark.jsonl）
- `results/` - 每次运行测试产生的结果记录

---

## 📊 简化的数据结构

```
bench/data/
│
├── benchmark/                     # 标准测试集（单一、稳定）
│   ├── benchmark.jsonl            # 1163 个测试样本
│   ├── metadata.json              # 基本信息
│   └── stats.json                 # 数据统计
│
├── results/                       # 测试运行历史
│   ├── 20251110_120000/           # 某次测试运行
│   │   ├── config.json            # 运行配置
│   │   ├── report.json            # 测试报告
│   │   ├── passed.jsonl           # 通过的样本 ID
│   │   └── failed.jsonl           # 失败的样本和错误
│   │
│   ├── 20251110_130000/           # 另一次测试
│   └── latest -> 20251110_130000  # 最新测试
│
└── generation/                    # 生成新 benchmark 的工作区（可选）
    └── 20251110_100000/           # 某次生成尝试
        ├── raw/
        ├── validation/
        └── filtered.jsonl
```

---

## 🔄 工作流程

### 日常使用：运行测试

```bash
# 运行测试（使用唯一的 benchmark）
bench-cli run --mode ollama

# 过滤测试
bench-cli run --filter "lang:zh" --schema-filter Encode,Retrieve

# 输出到: bench/data/results/20251110_120000/
```

### 查看结果

```bash
# 列出所有测试历史
bench-cli list-results

# 查看最新测试
bench-cli show-result latest

# 对比两次测试
bench-cli compare 20251110_120000 20251110_130000
```

### 更新 Benchmark（很少做）

```bash
# 只有当你想要全新的 benchmark 时才用
bench-cli generate --samples 2000 --output 20251110_100000
bench-cli validate 20251110_100000
bench-cli replace-benchmark --from generation/20251110_100000
```

---

## 🎯 命令设计

```bash
# ========== 运行测试 ==========
bench-cli run [OPTIONS]
  --mode MODE              # mock/ollama/openai
  --filter EXPR            # 样本过滤
  --schema-filter OPS      # 操作过滤
  --output-id ID           # 结果 ID（默认时间戳）

# ========== 查看结果 ==========
bench-cli list-results     # 列出所有测试历史
bench-cli show-result <id> # 查看详细结果
bench-cli compare <id1> <id2>  # 对比两次测试

# ========== Benchmark 信息 ==========
bench-cli info             # 查看 benchmark 基本信息

# ========== 生成新 Benchmark（可选）==========
bench-cli generate [OPTIONS]     # 生成候选数据
bench-cli validate <gen_id>      # 验证质量
bench-cli replace-benchmark --from <gen_id>  # 替换当前 benchmark
```

---

## 📦 数据格式

### benchmark/metadata.json

```json
{
  "total_samples": 1163,
  "created_at": "2024-10-22T18:46:04Z",
  "last_updated": "2024-10-22T18:46:04Z",
  
  "statistics": {
    "languages": {"zh": 581, "en": 582},
    "operations": {
      "Encode": 314,
      "Retrieve": 152,
      "Label": 174,
      "Summarize": 136,
      "Update": 105
    },
    "structures": {"single": 1109, "workflow": 54}
  },
  
  "notes": "Standard benchmark for Text2Mem evaluation"
}
```

### results/20251110_120000/config.json

```json
{
  "result_id": "20251110_120000",
  "benchmark_samples": 1163,
  "timestamp": "2025-11-10T12:00:00Z",
  
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
    "python_version": "3.10.12"
  }
}
```

### results/20251110_120000/report.json

```json
{
  "summary": {
    "total": 1163,
    "passed": 980,
    "failed": 183,
    "pass_rate": 0.843,
    "duration_seconds": 1234.5
  },
  
  "by_operation": {
    "Encode": {"total": 314, "passed": 298, "failed": 16, "pass_rate": 0.949},
    "Retrieve": {"total": 152, "passed": 145, "failed": 7, "pass_rate": 0.954}
  },
  
  "by_language": {
    "zh": {"total": 581, "passed": 489, "failed": 92, "pass_rate": 0.842},
    "en": {"total": 582, "passed": 491, "failed": 91, "pass_rate": 0.844}
  }
}
```

---

## 🔄 从现有数据迁移

### 当前状态

```
bench/data/benchmarks/
├── v2/
│   └── benchmark.jsonl  ← 你真正的 benchmark（1163 samples）
├── 20251022_184604/     ← 这是生成过程的中间数据
└── ...
```

### 迁移步骤

```bash
# 1. 提取真正的 benchmark
mkdir -p bench/data/benchmark
cp bench/data/benchmarks/v2/benchmark.jsonl bench/data/benchmark/
cp bench/data/benchmarks/v2/stats.json bench/data/benchmark/

# 2. 生成 metadata
bench-cli init-metadata

# 3. 移动生成数据到 generation（可选）
mkdir -p bench/data/generation
mv bench/data/benchmarks/20251022_184604 bench/data/generation/

# 4. 创建 results 目录
mkdir -p bench/data/results

# 5. 清理旧结构（可选）
rm -rf bench/data/benchmarks
```

---

## 💡 使用示例

### 场景 1: 日常测试

```bash
# 早上用 mock 模式快速验证
bench-cli run --mode mock

# 下午用 ollama 完整测试
bench-cli run --mode ollama

# 查看对比
bench-cli compare latest-1 latest
```

### 场景 2: 只测试中文

```bash
bench-cli run --filter "lang:zh" --mode ollama

# 查看结果
bench-cli show-result latest
```

### 场景 3: 测试特定操作

```bash
bench-cli run --schema-filter Encode,Retrieve --mode ollama
```

### 场景 4: 查看历史趋势

```bash
# 列出最近 10 次测试
bench-cli list-results --limit 10

# 输出示例:
# ID               Mode     Pass Rate  Duration  Timestamp
# 20251110_150000  ollama   84.3%      1234s     2025-11-10 15:00
# 20251110_120000  ollama   82.1%      1289s     2025-11-10 12:00
# 20251109_180000  mock     99.9%      45s       2025-11-09 18:00
```

---

## 🎯 关键优势

1. **极简结构** - 只有一个 benchmark，概念清晰
2. **职责分离** - benchmark（测试什么）vs results（测试结果）
3. **历史追踪** - 保留所有测试结果，可以看到性能趋势
4. **易于对比** - 不同配置、不同时间的测试结果
5. **按需更新** - benchmark 很少改变，results 频繁产生

---

## 📋 实施步骤

1. **迁移数据** ✅
   - 提取 v2/benchmark.jsonl 作为唯一 benchmark
   - 移动生成数据到 generation/

2. **更新代码** ✅
   - 修改 bench-cli 支持新结构
   - 简化命令（去掉版本管理）

3. **测试验证** ✅
   - 运行几次测试
   - 验证 results 正确生成

4. **文档更新** ✅
   - 更新 README
   - 添加使用示例

---

这个设计怎么样？要开始实施吗？


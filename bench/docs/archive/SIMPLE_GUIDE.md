# Benchmark 系统使用指南 (简化版)

## 🎯 核心理念

**一个稳定的 Benchmark + 多次测试结果**

```
bench/data/
├── benchmark/        # 唯一的标准测试集 (1163 samples)
└── results/          # 测试历史记录
    ├── 20251110_130000/
    ├── 20251110_140000/
    └── latest -> ...
```

---

## 🚀 快速开始

### 1. 查看 Benchmark 信息

```bash
./bench-cli-simple info
```

输出：
```
📊 Benchmark Information
Total Samples: 1163
Languages: zh: 581, en: 582
Operations: Encode: 314, Retrieve: 152, ...
```

### 2. 运行测试

```bash
# 基本测试
./bench-cli-simple run --mode mock --verbose

# 使用 ollama
./bench-cli-simple run --mode ollama --verbose

# 只测试中文
./bench-cli-simple run --filter "lang:zh" --mode ollama --verbose

# 只测试特定操作
./bench-cli-simple run --schema-filter Encode,Retrieve --mode ollama --verbose
```

### 3. 查看结果

```bash
# 列出所有测试历史
./bench-cli-simple list-results

# 查看最新结果
./bench-cli-simple show-result latest

# 查看特定结果
./bench-cli-simple show-result 20251110_130000

# 显示失败的样本
./bench-cli-simple show-result latest --show-failed
```

### 4. 对比结果

```bash
# 对比两次测试
./bench-cli-simple compare 20251110_130000 20251110_140000
```

---

## 📖 命令参考

### `run` - 运行测试

```bash
./bench-cli-simple run [OPTIONS]

Options:
  --mode MODE              测试模式: mock/ollama/openai (默认: auto)
  --filter EXPR            样本过滤: "lang:zh" 或 "op:Encode"
  --schema-filter OPS      操作过滤: "Encode,Retrieve"
  --schema-indices IDS     索引过滤: "0,2"
  --timeout SECONDS        超时设置
  --output-id ID           结果 ID (默认: 时间戳)
  --verbose, -v            详细输出
```

**示例**:
```bash
# Mock 模式快速测试
./bench-cli-simple run --mode mock -v

# Ollama 完整测试
./bench-cli-simple run --mode ollama -v

# 只测试中文 Encode 操作
./bench-cli-simple run --filter "lang:zh" --schema-filter Encode -v

# 自定义结果 ID
./bench-cli-simple run --mode ollama --output-id my_test_001 -v
```

### `list-results` - 列出测试历史

```bash
./bench-cli-simple list-results [OPTIONS]

Options:
  --limit N               限制显示数量 (默认: 20)
```

**输出示例**:
```
ID                   Mode     Pass Rate    Duration    Timestamp
20251110_140000      ollama   84.3%        1234s       2025-11-10 14:00
20251110_130000      ollama   82.1%        1289s       2025-11-10 13:00
20251110_120000      mock     99.9%        45s         2025-11-10 12:00
```

### `show-result` - 查看结果详情

```bash
./bench-cli-simple show-result <result_id> [OPTIONS]

Arguments:
  result_id              结果 ID 或 "latest"

Options:
  --show-failed          显示失败的样本
```

**输出示例**:
```
📊 Test Result: 20251110_140000

⚙️  Configuration:
  Mode: ollama
  Benchmark Samples: 1163

📈 Summary:
  Total: 1163
  Passed: 980
  Failed: 183
  Pass Rate: 84.3%
  Duration: 1234.5s

📋 By Operation:
  Encode       298/314  (94.9%)
  Retrieve     145/152  (95.4%)
  ...

🌐 By Language:
  zh     489/581  (84.2%)
  en     491/582  (84.4%)
```

### `compare` - 对比两次测试

```bash
./bench-cli-simple compare <result_id1> <result_id2>
```

**输出示例**:
```
📊 Result Comparison

Left:  20251110_130000
Right: 20251110_140000

📈 Summary:
Metric               Left            Right           Change
Total                1163            1163            +0
Passed               956             980             +24
Pass Rate            82.1%           84.3%           +2.2%
Duration (s)         1289.0          1234.0          -55.0
```

### `info` - 查看 Benchmark 信息

```bash
./bench-cli-simple info
```

---

## 💡 使用场景

### 场景 1: 每日测试

```bash
# 早上用 mock 模式快速验证
./bench-cli-simple run --mode mock -v

# 下午用 ollama 完整测试
./bench-cli-simple run --mode ollama -v

# 晚上对比结果
./bench-cli-simple list-results --limit 5
```

### 场景 2: 调试特定操作

```bash
# 只测试 Encode 和 Retrieve
./bench-cli-simple run --schema-filter Encode,Retrieve -v

# 查看失败的样本
./bench-cli-simple show-result latest --show-failed
```

### 场景 3: 中英文对比

```bash
# 测试中文
./bench-cli-simple run --filter "lang:zh" --mode ollama

# 测试英文
./bench-cli-simple run --filter "lang:en" --mode ollama

# 对比结果
./bench-cli-simple list-results
```

### 场景 4: 性能趋势分析

```bash
# 连续几天运行测试
./bench-cli-simple run --mode ollama -v  # Day 1
./bench-cli-simple run --mode ollama -v  # Day 2
./bench-cli-simple run --mode ollama -v  # Day 3

# 查看历史
./bench-cli-simple list-results
```

---

## 📊 数据结构

### benchmark/

```
bench/data/benchmark/
├── benchmark.jsonl   # 1163 个测试样本
├── metadata.json     # 基本信息
└── stats.json        # 统计数据
```

### results/

```
bench/data/results/
├── 20251110_130000/
│   ├── config.json       # 测试配置
│   ├── report.json       # 测试报告
│   ├── passed.jsonl      # 通过的样本 ID
│   └── failed.jsonl      # 失败的样本和错误
├── 20251110_140000/
└── latest -> 20251110_140000
```

---

## 🎯 关键优势

1. **简单明了** - 只有一个 benchmark，概念清晰
2. **历史追踪** - 保留所有测试结果，可以看趋势
3. **灵活过滤** - 支持语言、操作、索引等多种过滤
4. **易于对比** - 快速对比不同配置或时间的测试
5. **详细报告** - 按操作、语言分组的详细统计

---

## ❓ 常见问题

### Q: Benchmark 数据在哪里？
A: `bench/data/benchmark/benchmark.jsonl` (1163 个样本)

### Q: 测试结果保存在哪里？
A: `bench/data/results/YYYYMMDD_HHMMSS/`

### Q: 如何查看最新的测试结果？
A: `./bench-cli-simple show-result latest`

### Q: 可以删除旧的测试结果吗？
A: 可以，直接删除 `bench/data/results/` 下的对应目录

### Q: Benchmark 会自动更新吗？
A: 不会，benchmark 是稳定的。只有当你想要全新的测试集时才需要更新

---

## 🚀 下一步

1. **运行第一次测试**:
   ```bash
   ./bench-cli-simple run --mode mock -v
   ```

2. **查看结果**:
   ```bash
   ./bench-cli-simple show-result latest
   ```

3. **开始日常使用**:
   - 每天运行测试
   - 对比结果
   - 追踪性能趋势

---

**系统版本**: Simplified v1.0  
**最后更新**: 2025-11-10

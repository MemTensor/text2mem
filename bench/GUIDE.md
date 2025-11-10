# Benchmark 系统完整指南

## 📋 目录

1. [快速开始](#快速开始)
2. [完整工作流](#完整工作流)
3. [命令参考](#命令参考)
4. [数据结构](#数据结构)
5. [常见问题](#常见问题)

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
  ./bench-cli run --schema-filter Encode -v  # 只测 Encode
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
  ./bench-cli generate --config my_plan.yaml # 使用自定义配置
```

### `validate` - 验证数据

```bash
./bench-cli validate <generation_id> [OPTIONS]

选项:
  --run-tests              运行测试验证
  --verbose, -v            详细输出

示例:
  ./bench-cli validate 20251110_100000               # 快速统计
  ./bench-cli validate 20251110_100000 --run-tests  # 完整验证
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
  ./bench-cli show-result 20251110_130000         # 特定结果
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

### benchmark/

**当前使用的测试标准**

- `benchmark.jsonl` - 所有测试样本
- `metadata.json` - 创建时间、来源等
- `stats.json` - 语言、操作分布统计

### results/

**测试历史记录**

每次运行 `./bench-cli run` 都会创建新目录：

- `config.json` - 测试配置
- `report.json` - 测试报告（通过率、分组统计）
- `passed.jsonl` - 通过的样本 ID
- `failed.jsonl` - 失败的样本和错误信息
- `latest` - 软链接指向最新结果

### raw/

**生成的原始数据**

运行 `./bench-cli generate` 的输出：

- `stage1.jsonl` - NL 自然语言指令
- `stage2.jsonl` - IR 中间表示
- `stage3.jsonl` - Expected 期望结果

### archive/

**自动备份**

每次 `./bench-cli promote` 都会自动备份当前 benchmark。

---

## 💡 使用场景

### 场景 1: 每日测试

```bash
# 早上快速验证
./bench-cli run --mode mock -v

# 下午完整测试
./bench-cli run --mode ollama -v

# 查看历史趋势
./bench-cli list-results
```

### 场景 2: 生成新版本

```bash
# 1. 编辑配置
nano bench/generate/config/generation_plan.yaml

# 2. 生成
./bench-cli generate

# 3. 验证（假设 ID 为 20251110_150000）
./bench-cli validate 20251110_150000 --run-tests

# 4. 如果质量好，提升
./bench-cli promote 20251110_150000

# 5. 测试新 benchmark
./bench-cli run --mode ollama -v
```

### 场景 3: 调试问题

```bash
# 只测试有问题的操作
./bench-cli run --schema-filter Encode -v

# 查看失败详情
./bench-cli show-result latest --show-failed
```

### 场景 4: A/B 测试

```bash
# 测试配置 A
./bench-cli run --mode ollama --output-id test_a -v

# 测试配置 B
./bench-cli run --mode openai --output-id test_b -v

# 对比结果
./bench-cli compare test_a test_b
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

### Q: 可以删除旧的测试结果吗？

A: 可以，直接删除 `bench/data/results/` 下的对应目录

---

## ⚠️ 注意事项

### 生成 benchmark 前

1. 确保配置文件正确: `bench/generate/config/generation_plan.yaml`
2. 确保有足够的 API 配额（OpenAI）
3. 生成过程可能需要较长时间

### 提升 benchmark 前

1. 务必先验证: `./bench-cli validate <id> --run-tests`
2. 检查通过率是否合理 (建议 > 50%)
3. 确认数据分布符合预期

### 运行测试时

1. Mock 模式最快，但不真实
2. Ollama 模式需要本地模型运行
3. OpenAI 模式需要 API key

---

## 📁 重要文件

- **配置**: `bench/generate/config/generation_plan.yaml`
- **Benchmark**: `bench/data/benchmark/benchmark.jsonl`
- **测试结果**: `bench/data/results/`
- **生成数据**: `bench/data/raw/`
- **备份**: `bench/data/archive/`

---

**系统版本**: v1.0  
**最后更新**: 2025-11-10

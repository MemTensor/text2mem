# 🎉 完整的 Benchmark 系统已就绪！

## ✅ 系统概述

完整功能的 Benchmark 系统，支持：

1. **运行测试** - 使用现有 benchmark 进行测试
2. **生成新 benchmark** - 完整的生成流程
3. **验证质量** - 测试生成的数据
4. **提升 benchmark** - 将验证通过的数据设为正式 benchmark
5. **结果管理** - 查看、对比测试历史

---

## 📊 数据结构

```
bench/data/
├── benchmark/          # 当前使用的 benchmark (1163 samples)
│   ├── benchmark.jsonl
│   ├── metadata.json
│   └── stats.json
│
├── results/            # 测试历史
│   ├── 20251110_130000/
│   └── latest -> ...
│
├── raw/                # 生成的原始数据
│   └── 20251110_100000/
│       └── stage3.jsonl
│
├── generation/         # 生成工作区（可选）
└── archive/            # 备份
```

---

## 🚀 完整工作流程

### 流程 1: 日常测试（使用现有 benchmark）

```bash
# 1. 查看 benchmark 信息
./bench-cli info

# 2. 运行测试
./bench-cli run --mode ollama -v

# 3. 查看结果
./bench-cli show-result latest

# 4. 查看历史
./bench-cli list-results
```

### 流程 2: 生成新 benchmark（完整流程）

```bash
# 步骤 1: 生成候选数据
./bench-cli generate

# 系统会运行生成脚本，输出到 bench/data/raw/YYYYMMDD_HHMMSS/

# 步骤 2: 验证数据质量
./bench-cli validate 20251110_100000

# 快速查看统计信息

# 步骤 3: 运行测试验证
./bench-cli validate 20251110_100000 --run-tests

# 使用 mock 模式测试所有样本

# 步骤 4: 提升为正式 benchmark
./bench-cli promote 20251110_100000

# 会自动备份当前 benchmark，然后替换

# 步骤 5: 验证新 benchmark
./bench-cli info
./bench-cli run --mode ollama -v
```

---

## 📖 命令详解

### `run` - 运行测试

```bash
./bench-cli run [OPTIONS]

选项:
  --mode MODE              测试模式: auto/mock/ollama/openai
  --filter EXPR            样本过滤: "lang:zh"
  --schema-filter OPS      操作过滤: "Encode,Retrieve"
  --schema-indices IDS     索引过滤: "0,2"
  --timeout SECONDS        超时
  --output-id ID           结果 ID
  --verbose, -v            详细输出

示例:
  ./bench-cli run --mode mock -v              # Mock 模式快速测试
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

**注意**: 生成会调用 `bench/generate/generate.py`，确保配置文件正确。

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
  ./bench-cli promote 20251110_100000 --notes "v2 release"
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

## 💡 使用场景

### 场景 1: 每日测试

```bash
# 早上快速验证
./bench-cli run --mode mock -v

# 下午完整测试
./bench-cli run --mode ollama -v

# 查看对比
./bench-cli list-results
```

### 场景 2: 生成新版本 benchmark

```bash
# 1. 编辑配置
nano bench/generate/config/generation_plan.yaml

# 2. 生成
./bench-cli generate

# 3. 验证（假设生成 ID 为 20251110_150000）
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

## 🎯 关键特性

1. **完整流程** ✅
   - 生成 → 验证 → 提升 → 测试
   
2. **安全保障** ✅
   - 自动备份现有 benchmark
   - 确认提示防止误操作
   
3. **灵活过滤** ✅
   - 语言过滤
   - 操作过滤
   - 索引过滤
   
4. **历史追踪** ✅
   - 完整的测试历史
   - 结果对比
   
5. **质量验证** ✅
   - 自动过滤无效数据
   - 测试验证通过率

---

## ⚠️ 注意事项

### 生成 benchmark 前

1. 确保配置文件正确: `bench/generate/config/generation_plan.yaml`
2. 确保有足够的 API 配额（如果使用 OpenAI）
3. 生成过程可能需要较长时间

### 提升 benchmark 前

1. 务必先验证: `./bench-cli validate <id> --run-tests`
2. 检查通过率是否合理 (建议 > 50%)
3. 确认数据分布符合预期

### 运行测试时

1. Mock 模式最快，但不真实
2. Ollama 模式需要本地模型
3. OpenAI 模式需要 API key

---

## 📁 重要文件位置

- **配置**: `bench/generate/config/generation_plan.yaml`
- **Benchmark**: `bench/data/benchmark/benchmark.jsonl`
- **测试结果**: `bench/data/results/`
- **生成数据**: `bench/data/raw/`
- **备份**: `bench/data/archive/`

---

## 🆘 常见问题

**Q: 如何生成新 benchmark？**  
A: `./bench-cli generate` → `./bench-cli validate <id> --run-tests` → `./bench-cli promote <id>`

**Q: 如何运行测试？**  
A: `./bench-cli run --mode ollama -v`

**Q: 如何查看测试结果？**  
A: `./bench-cli show-result latest`

**Q: 提升 benchmark 会覆盖吗？**  
A: 会，但系统会自动备份到 `bench/data/archive/`

**Q: 如何恢复旧 benchmark？**  
A: 从 `bench/data/archive/benchmark_backup_YYYYMMDD_HHMMSS/` 复制回来

---

## 🚀 立即开始

```bash
# 1. 查看当前 benchmark
./bench-cli info

# 2. 运行第一次测试
./bench-cli run --mode mock -v

# 3. 查看结果
./bench-cli show-result latest

# 4. 开始使用！
```

---

**系统版本**: Complete v1.0  
**完成时间**: 2025-11-10  
**状态**: ✅ 完整可用

包含完整的生成、验证、测试流程！

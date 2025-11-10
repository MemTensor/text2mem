# Text2Mem Benchmark

## 🎉 系统重构完成！(v2.0)

**重大更新**: Benchmark 系统已完成重构，带来更简单、更强大的体验！

### ✨ 新特性

- ✅ **统一 CLI 工具** - 一个命令完成所有操作 (`bench-cli`)
- ✅ **简化数据结构** - 从 3 层目录简化为 1 层
- ✅ **清晰版本管理** - 时间戳 ID + 符号链接 (latest, stable, dev)
- ✅ **完整可追溯性** - 每个版本记录完整元数据和测试报告
- ✅ **向后兼容** - 旧命令仍可用（有废弃警告）
- ✅ **自动化迁移** - 安全迁移现有数据

> 📖 **迁移指南**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 完整使用文档 ⭐  
> 📖 **重构方案**: [REFACTOR_PLAN.md](REFACTOR_PLAN.md) - 设计文档  
> 📖 **完成报告**: [REFACTOR_COMPLETE.md](REFACTOR_COMPLETE.md) - 验收报告

## 🚀 快速开始

### 首次使用 - 迁移现有数据

如果你有现有的 benchmark 数据，先运行迁移：

```bash
python bench/migrate.py
```

### 构建新 Benchmark

```bash
# 一键构建 (生成 → 测试 → 清洗 → 构建)
./bench-cli build

# 快速测试 (100 样本)
./bench-cli build --samples 100

# 从现有数据构建
./bench-cli build --from-raw bench/data/archive/20251022_184604
```

### 测试和管理

```bash
# 列出所有版本
./bench-cli list

# 测试 benchmark
./bench-cli test latest --verbose

# 查看版本详情
./bench-cli info latest

# 标记稳定版本
./bench-cli link latest stable
```

## 数据流程

```
1. Generate → bench/data/raw/YYYYMMDD_HHMMSS/
                ├── stage1.jsonl  (NL指令)
                ├── stage2.jsonl  (IR样本)
                └── stage3.jsonl  (完整样本)

2. Test → bench/data/runs/YYYYMMDD_HHMMSS/tests/
            ├── passed.jsonl   (通过的样本)
            ├── failed.jsonl   (失败的样本)
            └── summary.json   (测试摘要)

3. Clean → bench/data/runs/YYYYMMDD_HHMMSS/cleaned/
             └── cleaned.jsonl  (清洗后的样本)

4. Build → bench/data/benchmarks/v2/
             ├── benchmark.jsonl  (最终benchmark)
             └── metadata.json
```

## Schema 过滤功能 🆕

运行 benchmark 时可以灵活选择测试哪些 schema：

```bash
# 测试所有 schema（默认）
python -m bench run --split benchmark

# 只测试 Encode 操作
python -m bench run --split benchmark --schema-filter Encode

# 测试多个操作
python -m bench run --split benchmark --schema-filter Encode,Retrieve,Update

# 按索引测试（测试第1和第3个 schema）
python -m bench run --split benchmark --schema-indices 0,2

# 组合过滤
python -m bench run --split benchmark --filter "lang:zh" --schema-filter Encode
```

**用途**：
- ✅ **生成时**：默认测试所有 schema（验证完整性）
- ✅ **运行时**：可选择性测试（灵活验证特定功能）

## 分步执行（可选）

如果需要更细粒度的控制：

```bash
# 1. 生成原始数据
python bench/generate/generate.py

# 2. 测试
python -m bench.tools.test --raw latest

# 3. 清洗  
python -m bench.tools.clean --run latest

# 4. 构建
python -m bench.tools.build --run latest --version v2
```

## 工具说明

- **generate/generate.py** - 生成原始测试数据（3阶段）
- **tools/test.py** - 运行测试，创建run
- **tools/clean.py** - 清洗数据，过滤失败样本
- **tools/build.py** - 构建最终benchmark
- **tools/pipeline.py** - 完整自动化流程

## 配置

主配置文件：`bench/generate/config/generation_plan.yaml`

关键配置项：

```yaml
plan:
  total_samples: 2000
  batch_size: 10

operation_proportions:
  encode: 0.20
  retrieve: 0.12
  # ...

# 语言分布配置（新增）
characteristics:
  lang:
    zh: 50%  # 50%中文
    en: 50%  # 50%英文

llm:
  provider: "openai"
  model: "gpt-4o"
```

## 文档

- [README_REFACTORED.md](README_REFACTORED.md) - 详细的重构说明和最佳实践
- [WORKFLOW.md](WORKFLOW.md) - 完整工作流程文档
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考

## 语言支持

系统现在支持自动生成中英文混合的测试样本：

- 在 `characteristics.lang` 中配置语言比例
- 系统会自动选择对应的prompt模板（中文/英文）
- 生成的样本ID会包含语言标记（例如：`t2m-zh-*` 或 `t2m-en-*`）

示例：

```yaml
characteristics:
  lang:
    zh: 60%  # 60%中文样本
    en: 40%  # 40%英文样本
```


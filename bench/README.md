# Text2Mem Benchmark

## ✨ 新特性

- ✅ **完整的中英文支持** - 根据配置自动生成中文或英文测试样本
- ✅ **清晰的数据流程** - raw → runs → benchmarks
- ✅ **简化的工具集** - 生成、测试、清洗、构建一体化
- ✅ **自动化流程** - 一键完成测试到benchmark的全流程

> 📖 **详细重构说明请查看**: [README_REFACTORED.md](README_REFACTORED.md)

## 快速开始

### 1. 生成测试数据

```bash
# 编辑配置：bench/generate/config/generation_plan.yaml
# 设置语言分布: characteristics.lang: {zh: 50%, en: 50%}
python bench/generate/generate.py
# → 输出到: bench/data/raw/YYYYMMDD_HHMMSS/
```

### 2. 测试、清洗并构建Benchmark

```bash
# 运行完整流程
python -m bench.tools.pipeline --raw latest --version v2
# → 输出到: bench/data/benchmarks/v2/
```

### 3. 验证Benchmark

```bash
python -m bench run --split benchmark --verbose
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


# Text2Mem Benchmark 工作流程详细文档

## 目录结构

```
bench/
├── data/
│   ├── raw/YYYYMMDD_HHMMSS/          # 生成的原始数据
│   ├── runs/YYYYMMDD_HHMMSS/         # 测试运行数据
│   ├── benchmarks/v{N}/              # 最终benchmark
│   └── db/                           # 临时数据库
├── generate/                         # 生成工具
├── tools/                            # 处理工具
└── core/                             # 核心代码
```

## 完整工作流程

### 阶段1：生成原始数据

```bash
python bench/generate/generate.py
```

**输入**: `bench/generate/config/generation_plan.yaml`

**输出**: `bench/data/raw/YYYYMMDD_HHMMSS/`
- `stage1.jsonl` - NL自然语言指令
- `stage2.jsonl` - IR中间表示（包含schema）
- `stage3.jsonl` - 完整样本（包含expected结果）

**说明**:
- 三阶段生成：NL指令 → IR样本 → 完整样本
- 支持断点恢复（checkpoint文件保存进度）
- 使用LLM生成，配置在generation_plan.yaml中

### 阶段2：运行测试

```bash
python -m bench.tools.test --raw latest
```

**输入**: `bench/data/raw/YYYYMMDD_HHMMSS/stage3.jsonl`

**输出**: `bench/data/runs/YYYYMMDD_HHMMSS/tests/`
- `summary.json` - 测试摘要（通过/失败统计）
- `passed.jsonl` - 通过测试的样本ID列表
- `failed.jsonl` - 失败样本ID及错误信息
- `details.jsonl` - 每个样本的详细测试结果

**说明**:
- 创建run目录，run_id默认与raw_id相同
- 对每个样本运行实际测试（调用runner.run_sample）
- 记录成功/失败状态和错误信息
- 实时显示测试进度

### 阶段3：清洗数据

```bash
python -m bench.tools.clean --run latest
```

**输入**:
- `bench/data/raw/YYYYMMDD_HHMMSS/stage3.jsonl` (原始样本)
- `bench/data/runs/YYYYMMDD_HHMMSS/tests/passed.jsonl` (通过的样本ID)

**输出**: `bench/data/runs/YYYYMMDD_HHMMSS/cleaned/`
- `cleaned.jsonl` - 清洗后的样本（只包含通过测试的）
- `metadata.json` - 元数据（来源、时间等）
- `stats.json` - 统计信息（操作分布、语言分布等）
- `filter_report.json` - 过滤报告（各种规则过滤掉的数量）

**过滤规则**:
1. 过滤测试失败的样本
2. 过滤包含'unknown'字段的样本
3. 只保留允许的指令类型：direct, indirect
4. 只保留允许的结构：single, workflow
5. 只保留允许的操作（12种核心操作）

**说明**:
- 根据测试结果过滤失败样本
- 应用额外的质量规则
- 生成详细的过滤报告

### 阶段4：构建Benchmark

```bash
python -m bench.tools.build --run latest --version v2
```

**输入**: `bench/data/runs/YYYYMMDD_HHMMSS/cleaned/cleaned.jsonl`

**输出**: `bench/data/benchmarks/v2/`
- `benchmark.jsonl` - 最终benchmark数据
- `metadata.json` - 元数据（版本、来源、时间等）
- `stats.json` - 统计信息（操作分布等）

**同时**:
- 更新 `bench/data/benchmarks/latest` 符号链接 → v2

**说明**:
- 重新分配样本ID（t2m-{lang}-{type}-{struct}-{op}-{idx:03d}）
- 保存原始ID到_original_id字段
- 生成完整的元数据和统计信息
- 更新latest符号链接便于快速访问

### 阶段5：验证Benchmark

```bash
python -m bench run --split benchmark --verbose
```

**输入**: `bench/data/benchmarks/latest/benchmark.jsonl`

**说明**:
- 对最终benchmark运行测试验证
- 确保所有样本都能通过测试
- 生成详细的运行报告

## 一键流程

```bash
python -m bench.tools.pipeline --raw latest --version v2
```

等价于依次执行：
1. test (阶段2)
2. clean (阶段3)
3. build (阶段4)

## 数据格式

### stage1.jsonl (NL指令)
```json
{
  "instruction": "请记录这次会议的要点...",
  "context": "[会议记录] ...",
  "classification": {
    "instruction_type": "direct",
    "structure": "single",
    "lang": "zh"
  },
  "scenario_info": {
    "scenario": "meeting_notes",
    "operation": "encode"
  },
  "batch_id": 0
}
```

### stage2.jsonl (IR样本)
```json
{
  "id": "t2m-zh-direct-single-enc-001",
  "class": {
    "instruction_type": "direct",
    "structure": "single",
    "lang": "zh"
  },
  "nl": {
    "zh": "请记录会议要点..."
  },
  "prerequisites": [],
  "schema_list": [{
    "stage": "ENC",
    "op": "Encode",
    "args": {
      "payload": {
        "text": "...",
        "knowledge_type": "fact"
      },
      "tags": ["会议", "记录"]
    }
  }],
  "init_db": null
}
```

### stage3.jsonl (完整样本)
```json
{
  "id": "t2m-zh-direct-single-enc-001",
  "class": { ... },
  "nl": { ... },
  "prerequisites": [ ... ],
  "schema_list": [ ... ],
  "init_db": null,
  "expected": {
    "state": {
      "item_count": 1,
      "items": [{
        "id": "...",
        "payload": { ... },
        "tags": ["会议", "记录"]
      }]
    }
  }
}
```

### passed.jsonl (测试结果)
```json
{
  "sample_id": "t2m-zh-direct-single-enc-001",
  "passed": true,
  "duration": 0.523
}
```

### cleaned.jsonl (清洗后)
与stage3格式相同，但只包含通过测试的样本

### benchmark.jsonl (最终benchmark)
与cleaned格式相同，但ID被重新分配

## 常用命令

```bash
# 查看raw列表
ls -lt bench/data/raw/

# 查看最新raw的内容
ls -lh bench/data/raw/$(ls -t bench/data/raw/ | head -1)/

# 查看run列表
ls -lt bench/data/runs/

# 查看测试结果
cat bench/data/runs/$(ls -t bench/data/runs/ | head -1)/tests/summary.json | python -m json.tool

# 查看benchmark版本
ls -l bench/data/benchmarks/

# 查看benchmark统计
cat bench/data/benchmarks/latest/stats.json | python -m json.tool

# 统计样本数量
wc -l bench/data/raw/*/stage*.jsonl
wc -l bench/data/runs/*/cleaned/cleaned.jsonl
wc -l bench/data/benchmarks/*/benchmark.jsonl
```

## 环境变量

```bash
# LLM配置
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://..."

# 测试配置
export TEXT2MEM_BENCH_SPLIT="benchmark"
export TEXT2MEM_BENCH_VERBOSE="true"
export TEXT2MEM_BENCH_TIMEOUT="120"
```

## 故障排除

### stage3.jsonl为空

**现象**: stage3.jsonl文件大小为0

**原因**: LLM API调用失败（如401 Unauthorized）

**排查**:
```bash
# 查看checkpoint中的错误
cat bench/generate/output/.checkpoint_samples_by_proportion.json | python -m json.tool | grep -A5 "errors"
```

**解决**:
1. 检查API密钥：`echo $OPENAI_API_KEY`
2. 检查API URL：generation_plan.yaml中的base_url
3. 修复后重新运行（支持断点恢复）

### 清洗保留了错误数量的样本

**现象**: 日志显示"5个通过测试"但"17个样本保留"

**原因**: 可能filter_failed被设置为False

**排查**:
```bash
# 查看日志中的过滤参数
grep "filter_failed" logs.txt
```

**解决**: 确保在调用clean时filter_failed=True

### benchmark找不到

**现象**: `python -m bench run --split benchmark` 报错找不到文件

**原因**: latest符号链接不存在或指向错误版本

**排查**:
```bash
ls -l bench/data/benchmarks/latest
```

**解决**:
```bash
cd bench/data/benchmarks
ln -sf v2 latest
```

### 测试进度不显示

**现象**: 运行test时没有看到进度输出

**原因**: 日志级别设置过高

**解决**: 确保使用--verbose或设置环境变量：
```bash
export TEXT2MEM_BENCH_VERBOSE="true"
```

## 配置详解

### generation_plan.yaml

```yaml
# 总体配置
plan:
  name: "samples_by_proportion"  # 计划名称
  total_samples: 2000            # 总样本数
  batch_size: 10                 # 每批生成数量
  resume_from_checkpoint: true   # 支持断点恢复

# 场景比例（总和=1.0）
scenario_proportions:
  incident_postmortem: 0.25
  meeting_notes: 0.25
  project_tracking: 0.25
  knowledge_base: 0.25

# 操作比例（总和=1.0）
operation_proportions:
  encode: 0.20      # 编码/记录
  retrieve: 0.12    # 检索
  update: 0.13      # 更新
  delete: 0.05      # 删除
  summarize: 0.08   # 摘要
  label: 0.12       # 标签
  promote: 0.08     # 提升
  demote: 0.07      # 降级
  lock: 0.04        # 锁定
  merge: 0.04       # 合并
  split: 0.04       # 拆分
  expire: 0.03      # 过期

# 样本特征分布
characteristics:
  instruction_style:
    direct: 85%     # 直接指令
    indirect: 15%   # 间接指令
  structure:
    single: 90%     # 单操作
    workflow: 10%   # 多操作工作流
  lang:
    zh: 50%        # 中文
    en: 50%        # 英文

# LLM配置
llm:
  provider: "openai"
  model: "gpt-4o"
  api_key_env: "OPENAI_API_KEY"
  base_url: ""
  temperature: 0.7
  max_tokens: 4000
  timeout: 120

# 三阶段配置
stages:
  stage1_nl_generation:
    enabled: true
    temperature: 0.7
    batch_size: 8
  stage2_ir_generation:
    enabled: true
    temperature: 0.5
    batch_size: 1
  stage3_expected_generation:
    enabled: true
    temperature: 0.5
    batch_size: 1

# 输出配置
output:
  base_dir: "bench/data/raw"
  format: "jsonl"
  keep_intermediate: true
```

## 性能优化

### 生成加速
- 使用异步生成：`generation_controller_async.py`
- 调整batch_size：平衡速度和质量
- 使用更快的模型（如gpt-3.5-turbo）

### 测试加速
- 使用--limit参数只测试部分样本
- 调整timeout参数避免卡住
- 并行测试（未来可实现）

## 注意事项

1. **数据不会丢失**: 所有中间数据都保存，可以追溯
2. **断点恢复**: generate支持断点恢复，中断后继续
3. **ID管理**: build会重新分配ID，原ID保存在_original_id
4. **时间戳**: 所有目录使用YYYYMMDD_HHMMSS格式
5. **符号链接**: latest是符号链接，方便访问最新版本
6. **过滤是不可逆的**: clean后无法恢复被过滤的样本
7. **测试是真实运行**: test会真的创建数据库和运行操作

## 开发指南

### 添加新操作

1. 在generation_plan.yaml中定义操作
2. 在prompts/目录添加提示词模板
3. 在clean.py的ALLOWED_OPERATIONS添加操作名
4. 在runner中实现操作逻辑

### 修改过滤规则

编辑 `bench/tools/clean.py`:
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

### 自定义统计

编辑 `bench/tools/build.py` 的 `_generate_stats()` 方法添加新的统计维度

## 相关文档

- [README.md](README.md) - 快速开始
- [generate/QUICK_REFERENCE.md](generate/QUICK_REFERENCE.md) - 生成工具参考

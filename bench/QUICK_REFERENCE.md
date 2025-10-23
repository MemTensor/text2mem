# Text2Mem Benchmark - 快速参考

## 数据流程
```
Generate → raw/ → Test → runs/ → Clean → Build → benchmarks/
```

## 一键运行
```bash
# 完整流程（推荐）
python -m bench.tools.pipeline --raw latest --version v2
```

## 分步执行
```bash
# 1. 生成数据（需要LLM API）
python bench/generate/generate.py

# 2. 测试
python -m bench.tools.test --raw latest

# 3. 清洗  
python -m bench.tools.clean --run latest

# 4. 构建
python -m bench.tools.build --run latest --version v2

# 5. 验证
python -m bench run --split benchmark --verbose
```

## 查看数据
```bash
# 查看raw
ls -lt bench/data/raw/ | head -3

# 查看runs
ls -lt bench/data/runs/ | head -3

# 查看benchmark
ls -l bench/data/benchmarks/

# 查看统计
cat bench/data/benchmarks/latest/stats.json | python -m json.tool
```

## 配置文件
```
bench/generate/config/generation_plan.yaml
```

主要配置：
- `total_samples`: 总样本数（默认2000）
- `operation_proportions`: 操作比例
- `llm`: LLM配置（provider, model, api_key）

## 目录结构
```
bench/
├── data/
│   ├── raw/              # 生成的原始数据
│   ├── runs/             # 测试运行数据
│   └── benchmarks/       # 最终benchmark
│       └── latest → vN   # 符号链接
├── generate/             # 生成工具
├── tools/                # 处理工具
└── core/                 # 核心代码
```

## 文档
- `README.md` - 快速开始
- `WORKFLOW.md` - 详细流程
- `CHANGES.md` - 变更总结
- `USAGE_GUIDE.sh` - 使用指南

## 常见问题

**Q: stage3.jsonl为空？**
A: LLM API失败，检查 `$OPENAI_API_KEY` 和配置

**Q: benchmark找不到？**  
A: 运行 `cd bench/data/benchmarks && ln -sf v2 latest`

**Q: 测试没进度？**
A: 添加 `--verbose` 参数

## 关键特性
- ✅ 数据持久化
- ✅ 断点恢复
- ✅ ID自动分配
- ✅ 版本管理
- ✅ 自动过滤
- ✅ 实时输出

## 帮助命令
```bash
python -m bench.tools.pipeline --help
python -m bench run --help
bash bench/USAGE_GUIDE.sh
```

"""
Bench tools - Benchmark处理工具集合

## 核心工具（data处理流程）

- **run_manager**: Rundirectorymanage模块（核心）
- **test**: testrun器 - fromrawcreaterun并runtest
- **clean**: data清洗工具 - 过滤failedsample，应用规则
- **build**: Benchmarkbuild器 - 重新分配ID，generate最终benchmark
- **pipeline**: 完整流程工具 - 一键completetesttobenchmark的全流程
- **stats**: 统计分析工具 - 分析sample分布和质量

## 实用工具

- **clock**: 虚拟时钟 - 用于基准test中的time模拟
- **sql_builder_sqlite**: SQLbuild器 - 编译test断言为SQLquery
- **create_empty_db**: create空data库 - generatestandard的Text2Memdata库

## Useexample

```python
# 完整流程（推荐）
python -m bench.tools.pipeline --raw latest --version v2

# 分步execute
python -m bench.tools.test --raw latest      # 1. test
python -m bench.tools.clean --run latest     # 2. 清洗
python -m bench.tools.build --run latest --version v2  # 3. build

# 统计分析
python -m bench.tools.stats --run latest
```

## data流程

```
raw/ (generate输出)
  ↓
[test] → runs/ (testresult)
  ↓
[clean] → runs/.../cleaned/ (清洗后)
  ↓
[build] → benchmarks/ (最终benchmark)
```
"""

__all__ = [
    'run_manager',
    'test',
    'clean',
    'build',
    'pipeline',
    'stats',
    'clock',
    'sql_builder_sqlite',
    'create_empty_db',
]

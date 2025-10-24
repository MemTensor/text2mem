"""
Bench tools - Benchmark处理工具集合

## 核心工具（数据处理流程）

- **run_manager**: Run目录管理模块（核心）
- **test**: 测试运行器 - 从raw创建run并运行测试
- **clean**: 数据清洗工具 - 过滤失败样本，应用规则
- **build**: Benchmark构建器 - 重新分配ID，生成最终benchmark
- **pipeline**: 完整流程工具 - 一键完成测试到benchmark的全流程
- **stats**: 统计分析工具 - 分析样本分布和质量

## 实用工具

- **clock**: 虚拟时钟 - 用于基准测试中的时间模拟
- **sql_builder_sqlite**: SQL构建器 - 编译测试断言为SQL查询
- **create_empty_db**: 创建空数据库 - 生成标准的Text2Mem数据库

## 使用示例

```python
# 完整流程（推荐）
python -m bench.tools.pipeline --raw latest --version v2

# 分步执行
python -m bench.tools.test --raw latest      # 1. 测试
python -m bench.tools.clean --run latest     # 2. 清洗
python -m bench.tools.build --run latest --version v2  # 3. 构建

# 统计分析
python -m bench.tools.stats --run latest
```

## 数据流程

```
raw/ (生成输出)
  ↓
[test] → runs/ (测试结果)
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

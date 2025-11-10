# Benchmark 系统重构完成 ✅

## 🎉 主要改进

### 1. **简化的数据结构**

**之前**:
```
bench/data/
├── raw/YYYYMMDD_HHMMSS/      # 原始生成数据
├── runs/YYYYMMDD_HHMMSS/     # 测试运行数据
└── benchmarks/v2/            # 最终 benchmark (版本不清晰)
```

**之后**:
```
bench/data/
└── benchmarks/
    ├── 20251110_120000/      # 一个完整的 benchmark 版本
    │   ├── benchmark.jsonl   # 最终测试数据
    │   ├── metadata.json     # 完整元数据
    │   ├── stats.json        # 统计信息
    │   ├── test_report.json  # 测试报告
    │   └── raw/              # 原始数据（可选）
    ├── latest -> 20251110_120000  # 最新版本
    └── stable -> 20251110_120000  # 稳定版本
```

### 2. **统一的命令行工具**

**之前** (需要记住多个命令):
```bash
python bench/generate/generate.py
python -m bench.tools.test --raw latest
python -m bench.tools.clean --run latest
python -m bench.tools.build --run latest --version v2
python -m bench run --split benchmark
```

**之后** (一个工具完成所有):
```bash
# 构建新 benchmark
./bench-cli build

# 测试 benchmark
./bench-cli test latest --verbose

# 管理版本
./bench-cli list
./bench-cli info 20251110_120000
./bench-cli link 20251110_120000 stable
```

### 3. **清晰的版本管理**

- **版本 ID**: 使用时间戳 `YYYYMMDD_HHMMSS` (清晰、可排序)
- **符号链接**: `latest`, `stable`, `dev` (语义化别名)
- **完整元数据**: 每个版本记录生成配置、测试结果、清洗报告

### 4. **可追溯性**

每个 benchmark 版本包含:
- ✅ 生成配置 (config_file, config_hash)
- ✅ 测试结果 (passed, failed, pass_rate)
- ✅ 清洗报告 (filter rules, before/after)
- ✅ 统计信息 (operations, languages, structures)
- ✅ 原始数据 (可选保留 raw/)

---

## 🚀 快速开始

### 安装

无需额外安装，只需确保已安装 Text2Mem：

```bash
pip install -e .
```

### 构建第一个 Benchmark

```bash
# 一键构建 (生成 → 测试 → 清洗 → 构建)
./bench-cli build

# 快速测试 (100 样本)
./bench-cli build --samples 100

# 从现有数据构建
./bench-cli build --from-raw bench/data/archive/20251022_184604
```

### 测试 Benchmark

```bash
# 测试最新版本
./bench-cli test latest --verbose

# 测试特定版本
./bench-cli test 20251110_120000

# 过滤测试
./bench-cli test latest --filter "lang:zh"
./bench-cli test latest --schema-filter Encode,Retrieve
```

### 管理版本

```bash
# 列出所有版本
./bench-cli list

# 查看详情
./bench-cli info latest

# 设置稳定版本
./bench-cli link 20251110_120000 stable

# 归档旧版本
./bench-cli archive 20251022_184604
```

---

## 📋 数据迁移

如果你有现有的 benchmark 数据，运行迁移脚本：

```bash
python bench/migrate.py
```

迁移脚本会：
1. ✅ 备份现有数据到 `bench/data/_backup_/`
2. ✅ 将 `runs/` 转换为新的 `benchmarks/` 结构
3. ✅ 生成完整的 metadata.json
4. ✅ 创建 `latest` 符号链接
5. ✅ 保留旧数据（供手动清理）

**安全保证**: 所有原始数据都会备份，不会丢失！

---

## 📖 完整命令参考

### `bench-cli build` - 构建 benchmark

```bash
# 基本用法
./bench-cli build

# 指定版本 ID
./bench-cli build --version 20251110_120000

# 从现有 raw 数据
./bench-cli build --from-raw path/to/raw/

# 快速测试 (小样本)
./bench-cli build --samples 100

# 自定义配置
./bench-cli build --config custom_plan.yaml

# 不保留原始数据
./bench-cli build --no-keep-raw
```

### `bench-cli test` - 测试 benchmark

```bash
# 测试最新版本
./bench-cli test latest

# 详细输出
./bench-cli test latest --verbose

# 按语言过滤
./bench-cli test latest --filter "lang:zh"

# 按操作过滤
./bench-cli test latest --schema-filter Encode,Retrieve

# 限制样本数
./bench-cli test latest --limit 10

# 保存报告
./bench-cli test latest --output report.json
```

### `bench-cli list` - 列出版本

```bash
# 列出所有版本
./bench-cli list

# 包含归档版本
./bench-cli list --all
```

### `bench-cli info` - 查看详情

```bash
# 查看版本详情
./bench-cli info latest
./bench-cli info 20251110_120000
```

### `bench-cli link` - 管理符号链接

```bash
# 创建链接
./bench-cli link 20251110_120000 stable
./bench-cli link 20251110_120000 dev

# 删除链接
./bench-cli link stable --remove
```

### `bench-cli archive` - 归档版本

```bash
# 归档旧版本
./bench-cli archive 20251022_184604
```

### `bench-cli delete` - 删除版本

```bash
# 删除版本 (需要确认)
./bench-cli delete 20251022_184604

# 跳过确认
./bench-cli delete 20251022_184604 --yes

# 强制删除 (即使被符号链接引用)
./bench-cli delete 20251022_184604 --force
```

### `bench-cli clean` - 清理临时文件

```bash
# 清理所有临时文件
./bench-cli clean
```

---

## 🔄 工作流示例

### 场景 1: 开发新功能

```bash
# 1. 快速构建测试 benchmark
./bench-cli build --samples 100

# 2. 验证
./bench-cli test latest --verbose

# 3. 如果测试通过，标记为 dev 版本
./bench-cli link latest dev
```

### 场景 2: 构建生产 benchmark

```bash
# 1. 编辑配置（增加样本数）
nano bench/generate/config/generation_plan.yaml

# 2. 完整构建
./bench-cli build

# 3. 全面测试
./bench-cli test latest --verbose

# 4. 标记为稳定版本
./bench-cli link latest stable
```

### 场景 3: 对比两个版本

```bash
# 1. 查看所有版本
./bench-cli list

# 2. 查看详情
./bench-cli info 20251110_120000
./bench-cli info 20251110_150000

# 3. 测试对比
./bench-cli test 20251110_120000 --verbose
./bench-cli test 20251110_150000 --verbose
```

---

## 📊 数据格式

### metadata.json

```json
{
  "id": "20251110_120000",
  "created_at": "2025-11-10T12:00:00Z",
  "status": "stable",
  
  "generation": {
    "config_file": "generation_plan.yaml",
    "config_hash": "abc123...",
    "total_samples": 2000,
    "llm_provider": "openai",
    "llm_model": "gpt-4o"
  },
  
  "test_results": {
    "total_samples": 2000,
    "passed": 1163,
    "failed": 837,
    "pass_rate": 0.582,
    "test_duration": 1234.56
  },
  
  "cleaning": {
    "rules_applied": ["filter_failed", "filter_unknown"],
    "samples_before": 2000,
    "samples_after": 1163
  },
  
  "tags": ["chinese", "full-coverage"],
  "notes": "Initial benchmark for v1.0 release"
}
```

### benchmark.jsonl

每行一个测试样本（与之前格式相同）：

```json
{
  "id": "t2m-zh-direct-single-encode-001",
  "class": {...},
  "nl": {...},
  "prerequisites": [...],
  "schema_list": [...],
  "expected": {...}
}
```

---

## 🆚 旧命令映射

| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `python bench/build_benchmark.py` | `./bench-cli build` | 一键构建 |
| `python -m bench.tools.pipeline --raw latest --version v2` | `./bench-cli build` | 完整流程 |
| `python -m bench run --split benchmark` | `./bench-cli test latest` | 测试 benchmark |
| `python -m bench.tools.test --raw latest` | (已整合到 build) | 运行测试 |
| `python -m bench.tools.clean --run latest` | (已整合到 build) | 清洗数据 |
| `python -m bench.tools.build --run latest --version v2` | (已整合到 build) | 构建 benchmark |

**废弃警告**: 旧命令仍然可用，但会显示警告提示

---

## ❓ 常见问题

### Q: 旧数据会丢失吗？
A: 不会！迁移脚本会完整备份所有数据到 `bench/data/_backup_/`

### Q: 如何回滚到旧系统？
A: 从备份目录恢复：
```bash
cp -r bench/data/_backup_/YYYYMMDD_HHMMSS/* bench/data/
```

### Q: 版本 ID 能自定义吗？
A: 可以，使用 `--version` 参数：
```bash
./bench-cli build --version 20251110_120000
```

### Q: 如何删除旧的 runs/ 和 raw/ 目录？
A: 迁移完成并验证后，手动删除：
```bash
rm -rf bench/data/runs bench/data/raw bench/data/benchmarks/v2
```

### Q: 原始生成数据会保留吗？
A: 默认保留在 `raw/` 子目录。使用 `--no-keep-raw` 跳过。

---

## 🎯 下一步

1. ✅ 运行迁移脚本: `python bench/migrate.py`
2. ✅ 测试新命令: `./bench-cli list`
3. ✅ 构建第一个 benchmark: `./bench-cli build --samples 100`
4. ✅ 查看文档: [REFACTOR_PLAN.md](REFACTOR_PLAN.md)

---

## 📚 相关文档

- [REFACTOR_PLAN.md](REFACTOR_PLAN.md) - 完整重构方案
- [README.md](README.md) - Benchmark 概览
- [GUIDE.md](GUIDE.md) - 使用指南
- [WORKFLOW.md](WORKFLOW.md) - 工作流程详解

---

**重构完成时间**: 2025-11-10  
**重构版本**: v2.0.0  
**向后兼容**: 是 (旧命令仍可用)

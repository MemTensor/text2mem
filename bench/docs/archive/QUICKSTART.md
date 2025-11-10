# 🎉 Benchmark 重构完成！欢迎使用 v2.0

恭喜！Text2Mem Benchmark 系统已完成重构。

## ✨ 立即开始

### 第一步：迁移现有数据（如果有）

```bash
python bench/migrate.py
```

迁移脚本会：
- ✅ 自动备份所有数据
- ✅ 转换为新的结构
- ✅ 生成完整元数据
- ✅ 创建符号链接

### 第二步：验证迁移

```bash
# 查看所有版本
./bench-cli list

# 查看最新版本详情
./bench-cli info latest
```

### 第三步：构建新 Benchmark

```bash
# 快速测试（100 样本）
./bench-cli build --samples 100

# 完整构建（2000 样本）
./bench-cli build
```

## 📖 常用命令

```bash
# ========== 构建 ==========
./bench-cli build                    # 完整构建
./bench-cli build --samples 100      # 快速测试
./bench-cli build --from-raw <path>  # 从现有数据

# ========== 测试 ==========
./bench-cli test latest --verbose    # 详细测试
./bench-cli test latest --filter "lang:zh"  # 过滤测试
./bench-cli test latest --schema-filter Encode,Retrieve  # 操作过滤

# ========== 管理 ==========
./bench-cli list                     # 列出所有版本
./bench-cli info <version_id>        # 查看详情
./bench-cli link <version_id> stable # 标记稳定版本
./bench-cli archive <version_id>     # 归档旧版本

# ========== 清理 ==========
./bench-cli clean                    # 清理临时文件
```

## 📚 完整文档

- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - 完整使用指南 ⭐
- **[REFACTOR_PLAN.md](REFACTOR_PLAN.md)** - 设计方案
- **[REFACTOR_COMPLETE.md](REFACTOR_COMPLETE.md)** - 完成报告
- **[README.md](README.md)** - Benchmark 概览

## 🆚 新旧对比

### 之前（5 个命令）

```bash
python bench/generate/generate.py
python -m bench.tools.test --raw latest
python -m bench.tools.clean --run latest
python -m bench.tools.build --run latest --version v2
python -m bench run --split benchmark
```

### 现在（1 个命令）

```bash
./bench-cli build
```

## 💡 提示

### 清理旧数据

迁移完成并验证无误后，可以删除旧目录：

```bash
rm -rf bench/data/runs
rm -rf bench/data/raw
rm -rf bench/data/benchmarks/v2
```

备份目录会保留在 `bench/data/_backup_/` 供参考。

### 旧命令仍可用

所有旧命令仍然可以使用，但会显示废弃警告：

```bash
python bench/build_benchmark.py
# ⚠️  WARNING: This command is DEPRECATED
# 请使用: ./bench-cli build
```

## 🎯 快速参考

| 任务 | 命令 |
|------|------|
| 构建新 benchmark | `./bench-cli build` |
| 快速测试 | `./bench-cli build --samples 100` |
| 测试 benchmark | `./bench-cli test latest --verbose` |
| 查看所有版本 | `./bench-cli list` |
| 查看版本详情 | `./bench-cli info latest` |
| 标记稳定版 | `./bench-cli link latest stable` |
| 归档旧版本 | `./bench-cli archive <version_id>` |
| 清理临时文件 | `./bench-cli clean` |

## 🆘 需要帮助？

- 查看命令帮助: `./bench-cli <command> --help`
- 阅读完整文档: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- 查看示例: [REFACTOR_COMPLETE.md](REFACTOR_COMPLETE.md)

---

**重构时间**: 2025-11-10  
**版本**: v2.0.0  
**状态**: ✅ 已完成

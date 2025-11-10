# 🎉 Benchmark 系统已重新设计完成！

## ✅ 已完成

你的 Benchmark 系统已经按照简化架构重新实施：

### 核心理念
**一个稳定的 Benchmark + 多次测试结果历史**

### 数据结构
```
bench/data/
├── benchmark/        # 唯一的标准测试集 (1163 samples)
│   ├── benchmark.jsonl
│   ├── metadata.json
│   └── stats.json
│
└── results/          # 测试历史记录（将来的测试结果会保存在这里）
    ├── 20251110_130000/
    └── latest -> ...
```

---

## 🚀 立即开始使用

### 1. 查看 Benchmark 信息

```bash
./bench-cli-simple info
```

你会看到：
```
📊 Benchmark Information
Total Samples: 1163
Languages: en: 1162, command: 1
Operations: Encode: 314, Label: 174, Retrieve: 152, ...
```

### 2. 运行第一次测试

```bash
# Mock 模式（快速测试，几秒钟）
./bench-cli-simple run --mode mock --verbose

# Ollama 模式（完整测试，需要几分钟）
./bench-cli-simple run --mode ollama --verbose
```

### 3. 查看测试结果

```bash
# 查看最新结果
./bench-cli-simple show-result latest

# 列出所有测试历史
./bench-cli-simple list-results
```

---

## 📖 完整命令参考

```bash
# ========== 运行测试 ==========
./bench-cli-simple run --mode mock -v                    # 快速测试
./bench-cli-simple run --mode ollama -v                  # 完整测试
./bench-cli-simple run --filter "lang:zh" -v             # 只测中文
./bench-cli-simple run --schema-filter Encode,Retrieve -v # 只测特定操作

# ========== 查看结果 ==========
./bench-cli-simple list-results                          # 列出历史
./bench-cli-simple show-result latest                    # 最新结果
./bench-cli-simple show-result latest --show-failed      # 显示失败的样本

# ========== 对比结果 ==========
./bench-cli-simple compare 20251110_130000 20251110_140000

# ========== Benchmark 信息 ==========
./bench-cli-simple info                                  # 查看 benchmark 统计
```

---

## 💡 常用场景

### 场景 1: 每日测试

```bash
# 早上快速验证
./bench-cli-simple run --mode mock -v

# 下午完整测试
./bench-cli-simple run --mode ollama -v

# 查看历史趋势
./bench-cli-simple list-results
```

### 场景 2: 调试问题

```bash
# 只测试有问题的部分
./bench-cli-simple run --schema-filter Encode -v

# 查看失败详情
./bench-cli-simple show-result latest --show-failed
```

### 场景 3: 中英文对比

```bash
# 测试中文性能
./bench-cli-simple run --filter "lang:zh" --mode ollama -v

# 测试英文性能
./bench-cli-simple run --filter "lang:en" --mode ollama -v

# 查看对比
./bench-cli-simple list-results
```

---

## 📚 详细文档

- **[SIMPLE_GUIDE.md](bench/SIMPLE_GUIDE.md)** - 完整使用指南 ⭐
- **[SIMPLIFIED_DESIGN.md](bench/SIMPLIFIED_DESIGN.md)** - 设计方案
- **[SIMPLIFIED_COMPLETE.md](bench/SIMPLIFIED_COMPLETE.md)** - 完成报告

---

## 🎯 核心优势

1. **极简清晰** - 只有一个 benchmark，概念简单
2. **职责分离** - benchmark (测什么) vs results (测试记录)
3. **历史追踪** - 保留所有测试结果，可以看趋势
4. **灵活过滤** - 支持语言、操作、索引等多种过滤
5. **易于对比** - 快速对比不同配置或时间的测试

---

## 🔄 数据说明

### Benchmark (标准测试集)
- **位置**: `bench/data/benchmark/`
- **内容**: 1163 个测试样本
- **用途**: 评估 Text2Mem 系统性能的标准题库
- **更新**: 很少改变（只有需要全新测试集时）

### Results (测试历史)
- **位置**: `bench/data/results/`
- **内容**: 每次测试的详细结果
- **用途**: 记录系统在不同配置/时间下的表现
- **更新**: 每次运行测试都会产生新记录

---

## ❓ 常见问题

**Q: 我现在应该用哪个命令？**  
A: 使用新的 `./bench-cli-simple`，简单易用！

**Q: 旧的 bench-cli 还能用吗？**  
A: 可以，但推荐使用新的 `bench-cli-simple`，更简单清晰。

**Q: Benchmark 会自动更新吗？**  
A: 不会，benchmark 是稳定的标准测试集。只有当你想要全新的测试集时才需要更新。

**Q: 可以删除旧的测试结果吗？**  
A: 可以，直接删除 `bench/data/results/` 下的对应目录即可。

**Q: 如何清理旧的数据结构？**  
A: 验证新系统工作正常后，可以删除：
```bash
rm -rf bench/data/benchmarks bench/data/runs bench/data/raw bench/data/_backup_
```

---

## 🎊 总结

**之前的问题**:
- ❌ 数据结构复杂 (raw → runs → benchmarks/v2)
- ❌ 版本管理混乱 (v2 是什么？)
- ❌ 职责混杂 (benchmark 和 test results 混在一起)

**现在的解决方案**:
- ✅ 数据结构简单 (benchmark + results)
- ✅ 无版本困扰 (单一稳定 benchmark)
- ✅ 职责清晰 (测试标准 vs 测试记录)

**用户体验**:
```bash
# 之前：需要理解复杂的版本和流程
python bench/generate/generate.py
python -m bench.tools.test --raw latest
python -m bench.tools.clean --run latest
python -m bench.tools.build --run latest --version v2
python -m bench run --split benchmark

# 现在：一个命令搞定
./bench-cli-simple run -v
```

---

## 🚀 现在就开始吧！

```bash
# 1. 查看 benchmark 信息
./bench-cli-simple info

# 2. 运行第一次测试
./bench-cli-simple run --mode mock -v

# 3. 查看结果
./bench-cli-simple show-result latest

# 4. 开始日常使用！
```

---

**系统版本**: Simplified v1.0  
**完成时间**: 2025-11-10  
**状态**: ✅ 已完成并可用

祝使用愉快！🎉

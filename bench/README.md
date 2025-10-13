# Text2Mem Bench

Text2Mem的端到端测试框架，验证核心功能的正确性和稳定性。

## 🚀 快速开始

```bash
# 运行基础测试（Mock模式，最快）
python -m bench run --split basic

# 使用Ollama（推荐，免费+高质量）
python -m bench run --split basic --mode ollama

# 使用OpenAI（最高质量）
python -m bench run --split basic --mode openai --timeout 120
```

## 📚 完整文档

- **[GUIDE.md](GUIDE.md)** - 完整使用指南
- **[QUICKREF.md](QUICKREF.md)** - 快速参考卡
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 架构设计
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 故障排查

## 🎯 测试架构（v1.3）

```
空表 → Prerequisites → 测试操作 → 验证
```

**特点**：
- 🚀 **更快** - 不需要预生成数据（从140秒降至5秒）
- 🎯 **更清晰** - 每个测试自包含，prerequisites明确定义
- 🔧 **更易维护** - 无外部依赖，不依赖预填充数据
- 📦 **更小** - 代码库减少88%

## 📊 测试模式

| 模式 | 速度 | 成本 | 质量 | 使用场景 |
|------|------|------|------|----------|
| **mock** | ⚡⚡⚡ | 免费 | N/A | 开发调试 |
| **ollama** | ⚡⚡ | 免费 | 高 | 日常验证 |
| **openai** | ⚡ | ~$0.01 | 最高 | 生产质检 |

## 📁 目录结构

```
bench/
├── README.md              # 本文档
├── GUIDE.md               # 完整指南
├── QUICKREF.md            # 快速参考
├── ARCHITECTURE.md        # 架构说明
├── TROUBLESHOOTING.md     # 故障排查
│
├── core/                  # 核心实现
│   ├── runner.py          # 测试运行器
│   ├── cli.py             # CLI接口
│   └── metrics.py         # 指标统计
│
├── tools/                 # 工具脚本
│   ├── clock.py              # 虚拟时钟
│   ├── create_empty_db.py    # 创建/验证空表
│   ├── sample_generator.py   # 样本生成器
│   ├── sql_builder_sqlite.py # SQL断言编译器
│   └── test_openai_api.py    # OpenAI API测试
│
├── data/v1/
│   ├── test_samples/      # 测试样本定义（JSONL）
│   └── db/                # 临时数据库（运行时创建）
│       └── README.md      # 数据库目录说明
│
└── output/                # 测试结果输出
```

## 🛠️ 常用命令

### 运行测试
```bash
# 基础运行
python -m bench run --split basic

# 过滤测试
python -m bench run --split basic --filter "op:Encode"
python -m bench run --split basic --filter "lang:zh"

# 详细输出
python -m bench run --split basic --verbose

# 设置超时
python -m bench run --split basic --timeout 60
```

### 列出测试
```bash
python -m bench list --split basic
```

### 生成测试模板
```bash
python -m bench generate --op Encode --lang zh
```

### 工具
```bash
# 创建空数据库
python bench/tools/create_empty_db.py --output test.db

# 验证数据库schema
python bench/tools/create_empty_db.py --verify test.db

# 测试OpenAI API
python bench/tools/test_openai_api.py
```

## 🔧 配置

### 环境变量（推荐使用.env文件）

```bash
# Ollama模式（推荐）
TEXT2MEM_EMBEDDING_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_PROVIDER=ollama
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b

# OpenAI模式
TEXT2MEM_EMBEDDING_PROVIDER=openai
TEXT2MEM_GENERATION_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_API_BASE=https://api.openai.com/v1  # 可选
```

## 📝 测试样本格式

```json
{
  "id": "test-id",
  "nl": "测试描述",
  "init_db": null,
  "prerequisites": [
    {
      "stage": "PREP",
      "op": "Encode",
      "args": {
        "payload": {"text": "前置数据"},
        "type": "note"
      }
    }
  ],
  "schema_list": [
    {
      "stage": "ENC",
      "op": "Encode",
      "args": {
        "payload": {"text": "测试数据"},
        "type": "note"
      }
    }
  ]
}
```

## 🎊 v1.3 改进

从v1.3开始，测试框架经过重大重构：

### 删除
- ❌ 3个预填充数据库（DB-100-PKM等）
- ❌ 整个生成框架（bench/generation/）
- ❌ 8个过时脚本和工具
- 💾 节省约620KB（88%减少）

### 改进
- ✅ 所有测试从空表开始
- ✅ 使用prerequisites动态准备数据
- ✅ 移除fixture_loader（改用prerequisites）
- ✅ 完整的schema支持
- ✅ 速度提升96%（OpenAI模式）

### 新增
- ✅ create_empty_db.py - 创建/验证空表工具
- ✅ 统一的文档体系
- ✅ 快速参考卡

## 🐛 常见问题

### Timeout超时
```bash
# 增加超时时间（OpenAI模式可能需要更长时间）
python -m bench run --split basic --timeout 120
```

### Ollama连接失败
```bash
# 确保Ollama正在运行
ollama serve

# 拉取所需模型
ollama pull nomic-embed-text
ollama pull qwen2:0.5b
```

### OpenAI API错误
```bash
# 测试API连接
python bench/tools/test_openai_api.py

# 检查环境变量
echo $OPENAI_API_KEY
echo $OPENAI_API_BASE
```

## 💡 开发提示

- Mock模式最快，适合开发调试
- Ollama模式推荐日常使用（免费+高质量）
- OpenAI模式用于最终验证
- 测试从空表开始，通过prerequisites准备数据
- 不需要预生成embeddings
- 每个测试独立运行，互不影响

## 📊 测试结果示例

```
============================================================
📈 Summary
============================================================
Samples:    21/21 passed (100.0%)
Assertions: 15/15 passed (100.0%)
Total time: 0.20s (avg: 0.01s/sample)

Operation success rates:
  Encode: 100.0% (3/3)      ✅
  Retrieve: 100.0% (3/3)    ✅
  Label: 100.0% (2/2)       ✅
  Update: 100.0% (3/3)      ✅
  Delete: 100.0% (2/2)      ✅
  Promote: 100.0% (3/3)     ✅
  Demote: 100.0% (2/2)      ✅
  Lock: 100.0% (2/2)        ✅
  Summarize: 100.0% (3/3)   ✅
```

---

**版本**: v1.3  
**更新**: 2025-01-05

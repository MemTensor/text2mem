# Text2Mem: 文本记忆处理系统

Text2Mem 是一个基于 IR Schema v1.3 的"可跑通的 Python 链路"实现，提供完整的：

**校验（JSON Schema） → 解析建模（Pydantic） → 映射执行（SQLite 原型 / Memory API 适配） → 结果返回**

## 项目结构

```
Text2Mem/
├── docs/                     # 文档目录
│   ├── CHANGELOG.md          # 变更日志
│   ├── INSTALL.md            # 安装说明
│   └── PERSONAL_KNOWLEDGE_BASE_DEMO.md # 个人知识库演示说明
├── examples/                 # 示例IR和工作流
│   ├── sample_ir_*.json      # 各类IR操作示例
│   └── workflow_*.json       # 工作流示例
├── scripts/                  # 脚本目录
│   ├── run_demo.py           # 示例运行脚本
│   ├── run_workflow.py       # 工作流运行脚本
│   └── text2mem_cli.py       # 命令行入口工具
├── tests/                    # 测试目录
│   ├── data/                 # 测试数据
│   └── test_*.py             # 测试模块
├── text2mem/                 # 核心代码
│   ├── adapters/             # 适配器实现
│   ├── engine.py             # Text2Mem 引擎
│   ├── models.py             # Pydantic 模型
│   ├── schema/               # IR schema定义
│   └── validate.py           # JSON Schema 校验
├── environment.yml           # Conda环境配置
├── pyproject.toml            # 项目元数据和依赖
└── README.md                 # 项目说明文档
```

## 环境与安装

详细配置说明请参考 [docs/CONFIG.md](docs/CONFIG.md)。

### 使用 Conda (推荐)

```bash
# 创建并激活环境
conda env create -f environment.yml
conda activate text2mem
```

详细安装说明请参考 [docs/INSTALL.md](docs/INSTALL.md)。

### 支持的模型服务

#### Ollama (默认)

Ollama配置保存在根目录 `.env` 中。可通过 `python manage.py config --provider ollama` 生成默认配置，或手动编辑以下键：

```
TEXT2MEM_EMBEDDING_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_PROVIDER=ollama
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
```

#### OpenAI API

安装OpenAI支持:

```bash
# 使用pip
pip install "text2mem[cloud]"

# 或者在conda环境中
conda activate text2mem
pip install openai>=1.6.0
```

设置OpenAI API配置:

```bash
# 设置环境变量
export OPENAI_API_KEY="your-api-key-here"
export TEXT2MEM_EMBEDDING_PROVIDER="openai"
export TEXT2MEM_EMBEDDING_MODEL="text-embedding-3-small"
export TEXT2MEM_GENERATION_PROVIDER="openai"
export TEXT2MEM_GENERATION_MODEL="gpt-3.5-turbo"
```

或通过`python manage.py config --provider openai`生成默认的OpenAI配置。

## 快速开始

### 运行演示

```bash
# 运行个人知识库演示 (自动检测可用的模型)
python scripts/demos/personal_knowledge_base.py

# 使用模拟模型运行演示 (无需Ollama或OpenAI)
python scripts/demos/personal_knowledge_base.py --mode mock

# 了解更多演示选项
python scripts/demos/personal_knowledge_base.py --help
```

关于个人知识库演示的详细信息，请参考 [docs/PERSONAL_KNOWLEDGE_BASE_DEMO.md](docs/PERSONAL_KNOWLEDGE_BASE_DEMO.md)。

### 使用命令行工具

```bash
# 列出所有示例
text2mem list

# 运行特定示例
text2mem run --file examples/sample_ir_encode.json

# 运行工作流
text2mem workflow examples/workflow_project_management.json
```

### 直接运行脚本

```bash
# 运行特定示例
python scripts/run_demo.py --file examples/sample_ir_encode.json

# 使用持久化数据库
python scripts/run_demo.py --file examples/sample_ir_encode.json --db ./text2mem.db

# 列出所有示例
python scripts/run_demo.py --list

# 运行所有示例
python scripts/run_demo.py --verbose

# 运行项目管理工作流
python scripts/run_workflow.py examples/workflow_project_management.json --verbose
```

### 使用 Makefile

```bash
# 运行所有测试
make test

# 运行所有示例
make run

# 运行工作流
make workflow

# 查看可用命令
make help
```

### 创建新项目

```bash
# 创建新的 Text2Mem 项目
bash scripts/create_project.sh my_memory_project
cd my_memory_project
```

## 支持的IR操作

Text2Mem支持以下IR操作：

1. **Encode**: 创建新记忆
2. **Label**: 为记忆添加标签或特性
3. **Update**: 更新记忆的属性
4. **Merge**: 合并多个记忆
5. **Promote**: 提升记忆的重要性
6. **Demote**: 降低记忆的重要性
7. **Delete**: 删除记忆
8. **Retrieve**: 检索记忆
9. **Lock**: 锁定记忆
10. **Expire**: 设置记忆过期时间
11. **Clarify**: 澄清记忆信息
12. **Split**: 拆分记忆
13. **Summarize**: 总结记忆

## 开发

请查看 [docs/INSTALL.md](docs/INSTALL.md) 获取开发环境设置指南。

## 变更日志

请查看 [docs/CHANGELOG.md](docs/CHANGELOG.md) 获取版本历史和变更说明。

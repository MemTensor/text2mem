# Text2Mem 配置指南

完整的环境配置、模型选择和参数设置说明。

---

## 目录

- [配置架构](#配置架构)
- [快速配置](#快速配置)
- [环境变量](#环境变量)
- [模型选择](#模型选择)
- [配置验证](#配置验证)

---

## 配置架构

Text2Mem 采用 **Provider 与 Service 分离** 的架构：

- **Provider**：提供模型接口（EmbeddingModel / GenerationModel）
  - Mock: 模拟模型，用于测试
  - Ollama: 本地运行的开源模型
  - OpenAI: 云端 API 服务

- **Service**：封装高阶能力
  - encode (文本编码)
  - semantic_search (语义搜索)
  - summarize (生成摘要)
  - label (标签建议)
  - split (文本拆分)

---

## 快速配置

### 方式 1: 使用 manage.py (推荐)

```bash
# Mock 模式 (测试/开发)
python manage.py config --provider mock

# Ollama 模式 (本地运行)
python manage.py config --provider ollama \
  --embed-model nomic-embed-text \
  --gen-model qwen2.5:0.5b

# OpenAI 模式 (云端API)
python manage.py config --provider openai \
  --openai-key sk-xxx \
  --embed-model text-embedding-3-small \
  --gen-model gpt-4o-mini
```

### 方式 2: 编程方式

```python
from text2mem.services.service_factory import create_models_service

# 自动根据环境选择
service = create_models_service(mode="auto")

# 或强制指定 provider
service = create_models_service(mode="openai")  # "mock" / "ollama" / "openai"
```

### 方式 3: 手动编辑 .env

```bash
# 复制模板
cp .env.example .env

# 编辑配置
nano .env
```

---

## 环境变量

### 通用配置

适用于所有 Provider：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `TEXT2MEM_DB_PATH` | 数据库文件路径 | `./text2mem.db` |
| `TEXT2MEM_DB_WAL` | 是否启用 WAL 模式 | `true` |
| `TEXT2MEM_DB_TIMEOUT` | 数据库超时(秒) | `30` |
| `TEXT2MEM_LOG_LEVEL` | 日志级别 | `INFO` |
| `TEXT2MEM_TEMPERATURE` | 生成模型温度 | `0.7` |
| `TEXT2MEM_MAX_TOKENS` | 生成最大 token 数 | `512` |
| `TEXT2MEM_TOP_P` | 生成采样 top-p | `0.9` |

### OpenAI 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | **必须设置** |
| `OPENAI_API_BASE` | 自定义 API 端点 | `https://api.openai.com/v1` |
| `OPENAI_ORGANIZATION` | 组织 ID | 无 |
| `TEXT2MEM_EMBEDDING_PROVIDER` | 固定为 "openai" | `openai` |
| `TEXT2MEM_EMBEDDING_MODEL` | 嵌入模型名称 | `text-embedding-3-small` |
| `TEXT2MEM_GENERATION_PROVIDER` | 固定为 "openai" | `openai` |
| `TEXT2MEM_GENERATION_MODEL` | 生成模型名称 | `gpt-4o-mini` |

### Ollama 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `TEXT2MEM_EMBEDDING_PROVIDER` | 固定为 "ollama" | `ollama` |
| `TEXT2MEM_EMBEDDING_MODEL` | 嵌入模型名称 | `nomic-embed-text` |
| `TEXT2MEM_OLLAMA_BASE_URL` | Ollama 服务 URL | `http://localhost:11434` |
| `TEXT2MEM_GENERATION_PROVIDER` | 固定为 "ollama" | `ollama` |
| `TEXT2MEM_GENERATION_MODEL` | 生成模型名称 | `qwen2.5:0.5b` |

### Mock 配置

Mock 模式无需额外配置，自动使用虚拟模型。

---

## 模型选择

### OpenAI 推荐模型

#### 嵌入模型

| 模型 | 维度 | 特点 | 适用场景 |
|-----|------|------|---------|
| `text-embedding-3-small` | 1536 | **推荐**，性能好，成本低 | 通用场景 |
| `text-embedding-3-large` | 3072 | 更高精度，成本较高 | 高精度需求 |
| `text-embedding-ada-002` | 1536 | 旧版模型 | 兼容性 |

#### 生成模型

| 模型 | 特点 | 适用场景 |
|-----|------|---------|
| `gpt-4o-mini` | **推荐**，快速且成本低 | 通用场景 |
| `gpt-4o` | 最新模型，高质量输出 | 高质量需求 |
| `gpt-4-turbo` | 较新模型，质量与成本适中 | 平衡场景 |
| `gpt-3.5-turbo` | 快速响应，成本最低 | 简单任务 |

### Ollama 推荐模型

#### 嵌入模型

| 模型 | 维度 | 特点 |
|-----|------|------|
| `nomic-embed-text` | 768 | **推荐**，性能好 |
| `mxbai-embed-large` | 1024 | 可选高性能模型 |

#### 生成模型

| 模型 | 参数量 | 特点 |
|-----|-------|------|
| `qwen2.5:0.5b` | 0.5B | **推荐**，轻量级 |
| `llama3:8b` | 8B | 高质量，需更多资源 |
| `mistral:7b` | 7B | 替代选项 |

---

## 配置验证

### 检查环境状态

```bash
python manage.py status
```

输出示例：
```
============================================================
📊 Text2Mem 环境状态
============================================================

[环境文件]
  ✅ .env 已配置 -> /path/to/.env

[模型配置]
  Provider: openai
  嵌入模型: openai:text-embedding-3-small
  生成模型: openai:gpt-4o-mini
  OpenAI API Key: ✅ 已设置

[数据库]
  路径: ./text2mem.db
  状态: ✅ 存在

[依赖工具]
  ollama: ✅ 可用
  pytest: ✅ 可用
```

### 查看模型详情

```bash
python manage.py models-info
```

输出示例：
```
============================================================
🤖 模型配置详情
============================================================

[总体配置]
  Provider: openai

[嵌入模型]
  Provider: openai
  Model: text-embedding-3-small

[生成模型]
  Provider: openai
  Model: gpt-4o-mini

[OpenAI 配置]
  API Key: ✅ 已设置 (sk-pYqTN...)
  API Base: https://api.openai.com/v1
```

### 运行冒烟测试

```bash
# 测试当前配置
python manage.py models-smoke

# 测试特定 provider
python manage.py models-smoke openai
python manage.py models-smoke ollama
python manage.py models-smoke mock
```

---

## 切换配置

### 在不同 Provider 之间切换

```bash
# 切换到 Ollama
python manage.py config --provider ollama

# 切换到 OpenAI
python manage.py config --provider openai --openai-key sk-xxx

# 切换到 Mock
python manage.py config --provider mock
```

### 更新单个环境变量

```bash
# 更新生成模型
python manage.py set-env TEXT2MEM_GENERATION_MODEL gpt-4o

# 更新嵌入模型
python manage.py set-env TEXT2MEM_EMBEDDING_MODEL text-embedding-3-large

# 更新数据库路径
python manage.py set-env TEXT2MEM_DB_PATH /path/to/custom.db
```

---

## 语言与国际化 (i18n)

### 默认语言

- 默认输出语言：英语 (en)
- 可通过环境变量全局设置

### 配置方式

```bash
# 设置为中文
export TEXT2MEM_LANG=zh

# 设置为英文
export TEXT2MEM_LANG=en
```

### 语言解析顺序

1. 显式传入的 `meta.lang` 或调用参数 `lang`
2. 环境变量 `TEXT2MEM_LANG`
3. 自动检测输入是否包含中文
4. 回落到英文 (en)

### 使用示例

```python
# 全局设置中文
import os
os.environ['TEXT2MEM_LANG'] = 'zh'

# 单次调用使用英文
result = engine.execute({
    "stage": "RET",
    "op": "Retrieve",
    "meta": {"lang": "en"}
})
```

---

## Ollama 特殊说明

### 安装 Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# 下载安装包: https://ollama.com/download
```

### 启动 Ollama 服务

```bash
ollama serve
```

### 拉取模型

```bash
# 使用 manage.py (推荐)
python manage.py setup-ollama

# 或手动拉取
ollama pull nomic-embed-text
ollama pull qwen2.5:0.5b
```

### 验证 Ollama

```bash
# 检查服务状态
curl http://localhost:11434/api/version

# 列出已安装模型
ollama list
```

---

## 故障排除

### OpenAI API 错误

**问题**: 401 Unauthorized

**解决**:
```bash
# 检查 API Key
echo $OPENAI_API_KEY

# 重新设置
python manage.py config --provider openai --openai-key sk-xxx
```

### Ollama 连接失败

**问题**: Connection refused

**解决**:
```bash
# 启动 Ollama 服务
ollama serve

# 检查服务状态
curl http://localhost:11434/api/version
```

### 模型未找到

**问题**: Model 'xxx' not found

**解决**:
```bash
# Ollama: 拉取模型
python manage.py setup-ollama

# OpenAI: 检查模型名称
python manage.py models-info
```

---

## 相关文档

- [README.md](../README.md) - 项目主文档
- [CHANGELOG.md](CHANGELOG.md) - 变更日志
- [Environment Configuration Guide](ENVIRONMENT_CONFIGURATION.md) - 详细环境配置

---

## 帮助命令

```bash
# 查看所有配置命令
python manage.py help config
python manage.py help set-env
python manage.py help setup-ollama
python manage.py help setup-openai
```

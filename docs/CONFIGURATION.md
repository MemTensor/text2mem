<div align="center">

# Text2Mem Configuration Guide | Text2Mem 配置指南

**Complete environment configuration, model selection, and parameter settings**  
**完整的环境配置、模型选择和参数设置说明**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## Table of Contents

- [Configuration Architecture](#configuration-architecture)
- [Quick Setup](#quick-setup)
- [Environment Variables](#environment-variables)
- [Model Selection](#model-selection)
- [Configuration Validation](#configuration-validation)
- [Troubleshooting](#troubleshooting)

---

## Configuration Architecture

Text2Mem uses a **Provider and Service separation** architecture:

- **Provider**: Provides model interfaces (EmbeddingModel / GenerationModel)
  - Mock: Simulated models for testing
  - Ollama: Locally running open-source models
  - OpenAI: Cloud API service

- **Service**: Encapsulates high-level capabilities
  - encode (text encoding)
  - semantic_search (semantic search)
  - summarize (generate summary)
  - label (label suggestion)
  - split (text splitting)

---

## Quick Setup

### Method 1: Using manage.py (Recommended)

```bash
# Mock mode (testing/development)
python manage.py config --provider mock

# Ollama mode (local running)
python manage.py config --provider ollama \
  --embed-model nomic-embed-text \
  --gen-model qwen2.5:0.5b

# OpenAI mode (cloud API)
python manage.py config --provider openai \
  --openai-key sk-xxx \
  --embed-model text-embedding-3-small \
  --gen-model gpt-4o-mini
```

### Method 2: Programmatic

```python
from text2mem.services.service_factory import create_models_service

# Automatically select based on environment
service = create_models_service(mode="auto")

# Or force specify provider
service = create_models_service(mode="openai")  # "mock" / "ollama" / "openai"
```

### Method 3: Manual .env Edit

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

---

## Environment Variables

### Common Configuration

Applicable to all Providers:

| Variable | Description | Default |
|---------|------|--------|
| `TEXT2MEM_DB_PATH` | Database file path | `./text2mem.db` |
| `TEXT2MEM_DB_WAL` | Enable WAL mode | `true` |
| `TEXT2MEM_DB_TIMEOUT` | Database timeout(s) | `30` |
| `TEXT2MEM_LOG_LEVEL` | Log level | `INFO` |
| `TEXT2MEM_TEMPERATURE` | Generation temperature | `0.7` |
| `TEXT2MEM_MAX_TOKENS` | Max generation tokens | `512` |
| `TEXT2MEM_TOP_P` | Generation top-p sampling | `0.9` |

### OpenAI Configuration

| Variable | Description | Default |
|---------|------|--------|
| `OPENAI_API_KEY` | OpenAI API key | **Must set** |
| `OPENAI_API_BASE` | Custom API endpoint | `https://api.openai.com/v1` |
| `OPENAI_ORGANIZATION` | Organization ID | None |
| `TEXT2MEM_EMBEDDING_PROVIDER` | Fixed to "openai" | `openai` |
| `TEXT2MEM_EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `TEXT2MEM_GENERATION_PROVIDER` | Fixed to "openai" | `openai` |
| `TEXT2MEM_GENERATION_MODEL` | Generation model name | `gpt-4o-mini` |

### Ollama Configuration

| Variable | Description | Default |
|---------|------|--------|
| `TEXT2MEM_EMBEDDING_PROVIDER` | Fixed to "ollama" | `ollama` |
| `TEXT2MEM_EMBEDDING_MODEL` | Embedding model name | `nomic-embed-text` |
| `TEXT2MEM_OLLAMA_BASE_URL` | Ollama service URL | `http://localhost:11434` |
| `TEXT2MEM_GENERATION_PROVIDER` | Fixed to "ollama" | `ollama` |
| `TEXT2MEM_GENERATION_MODEL` | Generation model name | `qwen2.5:0.5b` |

### Mock Configuration

Mock mode requires no additional configuration, automatically uses virtual models.

---

## Model Selection

### OpenAI Recommended Models

#### Embedding Models

| Model | Dimensions | Features | Use Case |
|-----|------|------|---------|
| `text-embedding-3-small` | 1536 | **Recommended**, good performance, low cost | General |
| `text-embedding-3-large` | 3072 | Higher precision, higher cost | High precision needs |
| `text-embedding-ada-002` | 1536 | Legacy model | Compatibility |

#### Generation Models

| Model | Features | Use Case |
|-----|------|---------|
| `gpt-4o-mini` | **Recommended**, fast and low cost | General |
| `gpt-4o` | Latest model, high quality output | High quality needs |
| `gpt-4-turbo` | Newer model, balanced quality and cost | Balanced scenarios |
| `gpt-3.5-turbo` | Fast response, lowest cost | Simple tasks |

### Ollama Recommended Models

#### Embedding Models

| Model | Dimensions | Features |
|-----|------|------|
| `nomic-embed-text` | 768 | **Recommended**, good performance |
| `mxbai-embed-large` | 1024 | Optional high-performance model |

#### Generation Models

| Model | Parameters | Features |
|-----|-------|------|
| `qwen2.5:0.5b` | 0.5B | **Recommended**, lightweight |
| `llama3:8b` | 8B | High quality, needs more resources |
| `mistral:7b` | 7B | Alternative option |

---

## Configuration Validation

### Check Environment Status

```bash
python manage.py status
```

Output example:
```
============================================================
📊 Text2Mem Environment Status
============================================================

[Environment File]
  ✅ .env configured -> /path/to/.env

[Model Configuration]
  Provider: openai
  Embedding model: openai:text-embedding-3-small
  Generation model: openai:gpt-4o-mini
  OpenAI API Key: ✅ Set

[Database]
  Path: ./text2mem.db
  Status: ✅ Exists

[Dependencies]
  ollama: ✅ Available
  pytest: ✅ Available
```

### View Model Details

```bash
python manage.py models-info
```

Output example:
```
============================================================
🤖 Model Configuration Details
============================================================

[General Configuration]
  Provider: openai

[Embedding Model]
  Provider: openai
  Model: text-embedding-3-small

[Generation Model]
  Provider: openai
  Model: gpt-4o-mini

[OpenAI Configuration]
  API Key: ✅ Set (sk-pYqTN...)
  API Base: https://api.openai.com/v1
```

### Run Smoke Tests

```bash
# Test current configuration
python manage.py models-smoke

# Test specific provider
python manage.py models-smoke openai
python manage.py models-smoke ollama
python manage.py models-smoke mock
```

---

## Troubleshooting

### OpenAI API Errors

**Problem**: 401 Unauthorized

**Solution**:
```bash
# Check API Key
echo $OPENAI_API_KEY

# Reset
python manage.py config --provider openai --openai-key sk-xxx
```

### Ollama Connection Failed

**Problem**: Connection refused

**Solution**:
```bash
# Start Ollama service
ollama serve

# Check service status
curl http://localhost:11434/api/version
```

### Model Not Found

**Problem**: Model 'xxx' not found

**Solution**:
```bash
# Ollama: Pull model
python manage.py setup-ollama

# OpenAI: Check model name
python manage.py models-info
```

---

# 中文

## 目录

- [配置架构](#配置架构-1)
- [快速配置](#快速配置-1)
- [环境变量](#环境变量-1)
- [模型选择](#模型选择-1)
- [配置验证](#配置验证-1)
- [故障排除](#故障排除-1)

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

<div align="center">

**Last Updated | 最后更新**: 2025-11-10

[⬆ Back to top | 返回顶部](#text2mem-configuration-guide--text2mem-配置指南)

</div>

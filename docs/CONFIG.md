# Text2Mem 配置说明文档

## 配置概述

Text2Mem 支持“Provider 与 Service 分离”的模型配置：

- Provider：仅提供模型接口（EmbeddingModel / GenerationModel），如 Mock、Ollama、OpenAI。
- Service：统一封装 encode / semantic_search / summarize / label / split 等高阶能力。

推荐通过工厂统一创建 Service：

```python
from text2mem.services.service_factory import create_models_service
service = create_models_service(mode="auto")  # auto/mock/ollama/openai
```

主要提供商：
1. **OpenAI API** - 云端API服务，需要API密钥
2. **Ollama** - 本地运行的开源模型服务

## 环境变量说明

### 通用配置

这些设置适用于任何模型服务:

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| TEXT2MEM_DB_PATH | 数据库文件路径 | ./text2mem.db |
| TEXT2MEM_DB_WAL | 是否启用WAL模式 | true |
| TEXT2MEM_DB_TIMEOUT | 数据库超时(秒) | 30 |
| TEXT2MEM_LOG_LEVEL | 日志级别 | INFO |
| TEXT2MEM_TEMPERATURE | 生成模型温度 | 0.7 |
| TEXT2MEM_MAX_TOKENS | 生成最大token数 | 512 |
| TEXT2MEM_TOP_P | 生成采样top-p | 0.9 |

### 模型服务提供商设置

每个提供商都有其特定的配置变量:

#### OpenAI API

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| OPENAI_API_KEY | OpenAI API密钥 | 必须设置 |
| OPENAI_API_BASE | 自定义API端点 | https://api.openai.com/v1 |
| OPENAI_ORGANIZATION | 组织ID | 无 |
| TEXT2MEM_EMBEDDING_PROVIDER | 固定为"openai" | openai |
| TEXT2MEM_EMBEDDING_MODEL | 嵌入模型名称 | text-embedding-3-small |
| TEXT2MEM_GENERATION_PROVIDER | 固定为"openai" | openai |
| TEXT2MEM_GENERATION_MODEL | 生成模型名称 | gpt-3.5-turbo |

#### Ollama

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| TEXT2MEM_EMBEDDING_PROVIDER | 固定为"ollama" | ollama |
| TEXT2MEM_EMBEDDING_MODEL | 嵌入模型名称 | nomic-embed-text |
| TEXT2MEM_EMBEDDING_BASE_URL | Ollama服务URL | http://localhost:11434 |
| TEXT2MEM_GENERATION_PROVIDER | 固定为"ollama" | ollama |
| TEXT2MEM_GENERATION_MODEL | 生成模型名称 | qwen2:0.5b |
| TEXT2MEM_GENERATION_BASE_URL | Ollama服务URL | http://localhost:11434 |

## 推荐模型

### OpenAI

#### 嵌入模型

- **text-embedding-3-small**: 推荐默认模型，1536维，性能好且成本低
- **text-embedding-3-large**: 更高精度，3072维，成本较高
- **text-embedding-ada-002**: 旧版模型，1536维

#### 生成模型

- **gpt-3.5-turbo**: 推荐默认模型，响应速度快，成本低
- **gpt-4o**: 最新模型，高质量输出，成本较高
- **gpt-4-turbo**: 较新模型，质量与成本适中

### Ollama

#### 嵌入模型

- **nomic-embed-text**: 推荐默认模型，768维
- **mxbai-embed-large**: 可选高性能模型，1024维

#### 生成模型

- **qwen2:0.5b**: 推荐默认模型，轻量级
- **llama3**: 高质量选项，需要更多资源
- **mistral**: 替代选项

## 切换配置方法

1. **使用管理脚本**:
   ```bash
   # 生成OpenAI配置
   python manage.py config --provider openai
   
   # 生成Ollama配置
   python manage.py config --provider ollama
   ```

2. **手动编辑**:
   编辑`.env`文件，注释/取消注释相应的配置部分

3. **编程方式**（无需 CLI）：

```python
from text2mem.services.service_factory import create_models_service

# 固定 provider
service = create_models_service(mode="openai")  # 或 "ollama" / "mock"

# 自动根据 .env/环境选择
service = create_models_service(mode="auto")
```

## 检查配置状态

```bash
python manage.py status
```

## 依赖安装

```bash
# 安装OpenAI依赖
pip install "text2mem[cloud]"
# 或
pip install openai>=1.6.0

# Ollama无需额外Python依赖，但需要本地运行Ollama服务
# 详见: https://ollama.com
```

## 语言与国际化（i18n）

- 默认输出语言：英语（en）。
- 全局默认可通过环境变量设置：

   - TEXT2MEM_LANG=en    # 英文（默认）
   - TEXT2MEM_LANG=zh    # 中文

- 运行时的语言解析顺序：
   1) 显式传入的 meta.lang 或调用参数 lang
   2) 环境变量 TEXT2MEM_LANG
   3) 自动检测输入是否包含中文（若包含则按中文）
   4) 回落到英文（en）

- 示例：

   - 全局设置中文：在 shell 中 export TEXT2MEM_LANG=zh
   - 单次调用使用英文：请求中带上 meta.lang="en"

注：Schema 文档默认以英文描述，关键字段提供并行的 x-description-zh 以便中文阅读，无需每次指定语言。

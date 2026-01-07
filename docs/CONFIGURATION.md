<div align="center">

# Configuration Guide | 配置指南

**Complete configuration guide for all providers**  
**所有提供者的完整配置指南**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## 📋 Table of Contents

1. [Quick Setup](#quick-setup)
2. [Provider Configuration](#provider-configuration)
3. [Advanced Configuration](#advanced-configuration)
4. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Setup

### Step 1: Copy Environment Template

```bash
cp .env.example .env
```

The default `.env.example` uses **mock provider** (no LLM required, perfect for testing).

### Step 2: Choose Your Provider

Edit `.env` and set `TEXT2MEM_PROVIDER`:

#### Option A: Mock (Testing, No LLM)
```bash
TEXT2MEM_PROVIDER=mock
# No additional configuration needed
```

#### Option B: Ollama (Local Models)
```bash
TEXT2MEM_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
OLLAMA_BASE_URL=http://localhost:11434
```

**Setup Ollama:**
```bash
# Install Ollama from https://ollama.ai
ollama pull nomic-embed-text
ollama pull qwen2:0.5b

# Start Ollama server
ollama serve
```

#### Option C: OpenAI (Cloud API)
```bash
TEXT2MEM_PROVIDER=openai
TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_API_BASE=https://api.openai.com/v1
```

### Step 3: Verify Configuration

```bash
python manage.py status
```

Expected output:
```
✅ Environment configured
✅ Provider: mock/ollama/openai
✅ Models loaded
```

---

## 🔧 Provider Configuration

### Mock Provider

**Purpose**: Testing and development without LLM

**Configuration**:
```bash
TEXT2MEM_PROVIDER=mock
```

**Features**:
- ✅ No API keys or models required
- ✅ Instant responses
- ✅ Deterministic outputs
- ⚠️ Not realistic for production

**Use Cases**:
- Unit testing
- CI/CD pipelines
- Quick prototyping
- Documentation examples

---

### Ollama Provider

**Purpose**: Local LLM inference with privacy

**Requirements**:
- Ollama installed (https://ollama.ai)
- Sufficient RAM (8GB+ recommended)
- Downloaded models

**Configuration**:
```bash
TEXT2MEM_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
OLLAMA_BASE_URL=http://localhost:11434
```

**Recommended Models**:

| Task | Model | Size | RAM | Quality |
|------|-------|------|-----|---------|
| Embedding | `nomic-embed-text` | 274MB | 1GB | ⭐⭐⭐⭐ |
| Embedding | `mxbai-embed-large` | 669MB | 2GB | ⭐⭐⭐⭐⭐ |
| Generation | `qwen2:0.5b` | 352MB | 1GB | ⭐⭐⭐ |
| Generation | `llama3.2:3b` | 2GB | 4GB | ⭐⭐⭐⭐ |
| Generation | `qwen2.5:7b` | 4.7GB | 8GB | ⭐⭐⭐⭐⭐ |

**Setup Steps**:
```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull models
ollama pull nomic-embed-text
ollama pull qwen2:0.5b

# 3. Verify models
ollama list

# 4. Start server (if not running)
ollama serve

# 5. Test connection
curl http://localhost:11434/api/version
```

**Features**:
- ✅ Complete privacy (no data leaves your machine)
- ✅ No usage costs
- ✅ Works offline
- ⚠️ Requires local compute resources

---

### OpenAI Provider

**Purpose**: Cloud-based LLM with best quality

**Requirements**:
- OpenAI API key
- Active billing account

**Configuration**:
```bash
TEXT2MEM_PROVIDER=openai
TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_API_BASE=https://api.openai.com/v1
```

**Recommended Models**:

| Task | Model | Cost/1M tokens | Quality |
|------|-------|----------------|---------|
| Embedding | `text-embedding-3-small` | $0.02 | ⭐⭐⭐⭐ |
| Embedding | `text-embedding-3-large` | $0.13 | ⭐⭐⭐⭐⭐ |
| Generation | `gpt-4o-mini` | $0.15/$0.60 | ⭐⭐⭐⭐ |
| Generation | `gpt-4o` | $2.50/$10.00 | ⭐⭐⭐⭐⭐ |

**Setup Steps**:
```bash
# 1. Get API key from https://platform.openai.com/api-keys

# 2. Edit .env
nano .env

# 3. Add your key
OPENAI_API_KEY=sk-your-actual-key-here

# 4. Verify
python manage.py status
```

**Features**:
- ✅ Best quality and performance
- ✅ No local setup required
- ✅ Scales automatically
- ⚠️ Requires internet and API costs

---

## ⚙️ Advanced Configuration

### Using .env.local

For local development with sensitive data:

```bash
# Copy the local example
cp .env.local.example .env.local

# Edit with your real credentials
nano .env.local
```

**`.env.local` is automatically ignored by git** and takes precedence over `.env`.

**Priority order**: `.env.local` > `.env` > environment variables

---

### Database Configuration

```bash
# SQLite database path
TEXT2MEM_DB_PATH=./text2mem.db

# Use in-memory database (testing only)
TEXT2MEM_DB_PATH=:memory:
```

---

### Model-Specific Settings

#### Ollama Custom Host
```bash
OLLAMA_BASE_URL=http://custom-host:11434
```

#### OpenAI Custom Base URL (for proxies or compatible APIs)
```bash
OPENAI_API_BASE=https://your-proxy.com/v1
```

#### Embedding Dimensions
```bash
# Auto-detected by default, but can override
TEXT2MEM_EMBEDDING_DIM=768
```

---

### Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TEXT2MEM_PROVIDER` | `mock` | Provider: mock/ollama/openai |
| `TEXT2MEM_EMBEDDING_MODEL` | - | Embedding model name |
| `TEXT2MEM_GENERATION_MODEL` | - | Generation model name |
| `TEXT2MEM_DB_PATH` | `./text2mem.db` | SQLite database path |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | OpenAI API base URL |

---

## 🆘 Troubleshooting

### Common Issues

#### Issue: "Provider not configured"

**Cause**: `.env` file missing or incomplete

**Solution**:
```bash
cp .env.example .env
python manage.py config
```

---

#### Issue: "Ollama connection failed"

**Cause**: Ollama server not running or wrong URL

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# If not, start Ollama
ollama serve

# If using custom host, check URL in .env
echo $OLLAMA_BASE_URL
```

---

#### Issue: "Model not found (Ollama)"

**Cause**: Model not pulled

**Solution**:
```bash
# List available models
ollama list

# Pull missing model
ollama pull nomic-embed-text
ollama pull qwen2:0.5b
```

---

#### Issue: "OpenAI API error 401"

**Cause**: Invalid or missing API key

**Solution**:
```bash
# Check API key in .env
grep OPENAI_API_KEY .env

# Get new key from https://platform.openai.com/api-keys
# Update .env with valid key
```

---

#### Issue: "OpenAI API error 429"

**Cause**: Rate limit exceeded or insufficient quota

**Solution**:
- Check your usage at https://platform.openai.com/usage
- Verify billing settings
- Wait for rate limit reset
- Upgrade your plan if needed

---

#### Issue: "Database locked"

**Cause**: Multiple processes accessing same database

**Solution**:
```bash
# Use different database per process
TEXT2MEM_DB_PATH=./test_db.db

# Or use in-memory database for testing
TEXT2MEM_DB_PATH=:memory:
```

---

### Security Best Practices

#### ⚠️ Never Commit Real API Keys

1. **Use `.env.local` for secrets**
   - Add real API keys to `.env.local`
   - Keep `.env` with placeholder values

2. **Verify .gitignore**
   ```bash
   grep "\.env\.local" .gitignore
   ```

3. **Rotate compromised keys immediately**
   - Revoke old key at provider dashboard
   - Generate new key
   - Update `.env.local`

4. **Use environment variables in CI/CD**
   - Never hardcode secrets in code
   - Use GitHub Secrets or similar

---

### Performance Tuning

#### Ollama Performance

**Faster inference**:
- Use smaller models (qwen2:0.5b instead of qwen2.5:7b)
- Increase RAM allocation
- Use GPU if available

**Check Ollama stats**:
```bash
ollama ps
```

#### OpenAI Performance

**Reduce costs**:
- Use `gpt-4o-mini` instead of `gpt-4o`
- Use `text-embedding-3-small` instead of `text-embedding-3-large`
- Implement caching for repeated queries

**Monitor usage**:
- https://platform.openai.com/usage

---

## 🔍 Configuration Verification

### Quick Verification Script

```bash
#!/bin/bash
echo "=== Text2Mem Configuration Check ==="

# Check .env exists
if [ -f .env ]; then
    echo "✅ .env found"
else
    echo "❌ .env not found"
    exit 1
fi

# Check provider
PROVIDER=$(grep TEXT2MEM_PROVIDER .env | cut -d'=' -f2)
echo "Provider: $PROVIDER"

# Provider-specific checks
if [ "$PROVIDER" = "ollama" ]; then
    echo "Checking Ollama..."
    curl -s http://localhost:11434/api/version && echo "✅ Ollama running" || echo "❌ Ollama not running"
elif [ "$PROVIDER" = "openai" ]; then
    echo "Checking OpenAI..."
    grep -q "sk-" .env && echo "✅ API key found" || echo "❌ API key missing"
fi

# Test with manage.py
python manage.py status
```

---

# 中文

## 📋 目录

1. [快速配置](#快速配置)
2. [提供者配置](#提供者配置)
3. [高级配置](#高级配置)
4. [故障排除](#故障排除-1)

---

## 🚀 快速配置

### 步骤 1：复制环境模板

```bash
cp .env.example .env
```

默认的 `.env.example` 使用 **mock 提供者**（无需 LLM，适合测试）。

### 步骤 2：选择提供者

编辑 `.env` 并设置 `TEXT2MEM_PROVIDER`：

#### 选项 A：Mock（测试用，无需 LLM）
```bash
TEXT2MEM_PROVIDER=mock
# 无需额外配置
```

#### 选项 B：Ollama（本地模型）
```bash
TEXT2MEM_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
OLLAMA_BASE_URL=http://localhost:11434
```

**设置 Ollama：**
```bash
# 从 https://ollama.ai 安装 Ollama
ollama pull nomic-embed-text
ollama pull qwen2:0.5b

# 启动 Ollama 服务器
ollama serve
```

#### 选项 C：OpenAI（云端 API）
```bash
TEXT2MEM_PROVIDER=openai
TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-你的实际密钥
OPENAI_API_BASE=https://api.openai.com/v1
```

### 步骤 3：验证配置

```bash
python manage.py status
```

预期输出：
```
✅ 环境已配置
✅ Provider: mock/ollama/openai
✅ 模型已加载
```

---

## 🔧 提供者配置

### Mock 提供者

**用途**：无需 LLM 的测试和开发

**配置**：
```bash
TEXT2MEM_PROVIDER=mock
```

**特性**：
- ✅ 无需 API 密钥或模型
- ✅ 即时响应
- ✅ 确定性输出
- ⚠️ 不适合生产环境

**使用场景**：
- 单元测试
- CI/CD 流水线
- 快速原型
- 文档示例

---

### Ollama 提供者

**用途**：本地 LLM 推理，保护隐私

**要求**：
- 安装 Ollama (https://ollama.ai)
- 足够的 RAM（建议 8GB+）
- 下载的模型

**配置**：
```bash
TEXT2MEM_PROVIDER=ollama
TEXT2MEM_EMBEDDING_MODEL=nomic-embed-text
TEXT2MEM_GENERATION_MODEL=qwen2:0.5b
OLLAMA_BASE_URL=http://localhost:11434
```

**推荐模型**：

| 任务 | 模型 | 大小 | RAM | 质量 |
|------|------|------|-----|------|
| 向量嵌入 | `nomic-embed-text` | 274MB | 1GB | ⭐⭐⭐⭐ |
| 向量嵌入 | `mxbai-embed-large` | 669MB | 2GB | ⭐⭐⭐⭐⭐ |
| 文本生成 | `qwen2:0.5b` | 352MB | 1GB | ⭐⭐⭐ |
| 文本生成 | `llama3.2:3b` | 2GB | 4GB | ⭐⭐⭐⭐ |
| 文本生成 | `qwen2.5:7b` | 4.7GB | 8GB | ⭐⭐⭐⭐⭐ |

**设置步骤**：
```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 拉取模型
ollama pull nomic-embed-text
ollama pull qwen2:0.5b

# 3. 验证模型
ollama list

# 4. 启动服务器（如果未运行）
ollama serve

# 5. 测试连接
curl http://localhost:11434/api/version
```

**特性**：
- ✅ 完全隐私（数据不离开本机）
- ✅ 无使用成本
- ✅ 可离线工作
- ⚠️ 需要本地计算资源

---

### OpenAI 提供者

**用途**：云端 LLM，质量最佳

**要求**：
- OpenAI API 密钥
- 活跃的计费账户

**配置**：
```bash
TEXT2MEM_PROVIDER=openai
TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-你的实际密钥
OPENAI_API_BASE=https://api.openai.com/v1
```

**推荐模型**：

| 任务 | 模型 | 成本/百万tokens | 质量 |
|------|------|----------------|------|
| 向量嵌入 | `text-embedding-3-small` | $0.02 | ⭐⭐⭐⭐ |
| 向量嵌入 | `text-embedding-3-large` | $0.13 | ⭐⭐⭐⭐⭐ |
| 文本生成 | `gpt-4o-mini` | $0.15/$0.60 | ⭐⭐⭐⭐ |
| 文本生成 | `gpt-4o` | $2.50/$10.00 | ⭐⭐⭐⭐⭐ |

**设置步骤**：
```bash
# 1. 从 https://platform.openai.com/api-keys 获取 API 密钥

# 2. 编辑 .env
nano .env

# 3. 添加密钥
OPENAI_API_KEY=sk-你的实际密钥

# 4. 验证
python manage.py status
```

**特性**：
- ✅ 质量和性能最佳
- ✅ 无需本地设置
- ✅ 自动扩展
- ⚠️ 需要互联网和 API 成本

---

## ⚙️ 高级配置

### 使用 .env.local

用于本地开发的敏感数据：

```bash
# 复制本地示例
cp .env.local.example .env.local

# 编辑真实凭据
nano .env.local
```

**`.env.local` 会自动被 git 忽略**，优先级高于 `.env`。

**优先级顺序**：`.env.local` > `.env` > 环境变量

---

### 数据库配置

```bash
# SQLite 数据库路径
TEXT2MEM_DB_PATH=./text2mem.db

# 使用内存数据库（仅测试）
TEXT2MEM_DB_PATH=:memory:
```

---

### 模型特定设置

#### Ollama 自定义主机
```bash
OLLAMA_BASE_URL=http://custom-host:11434
```

#### OpenAI 自定义基础 URL（用于代理或兼容 API）
```bash
OPENAI_API_BASE=https://your-proxy.com/v1
```

#### 向量嵌入维度
```bash
# 默认自动检测，但可以覆盖
TEXT2MEM_EMBEDDING_DIM=768
```

---

### 环境变量参考

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `TEXT2MEM_PROVIDER` | `mock` | 提供者：mock/ollama/openai |
| `TEXT2MEM_EMBEDDING_MODEL` | - | 向量嵌入模型名称 |
| `TEXT2MEM_GENERATION_MODEL` | - | 文本生成模型名称 |
| `TEXT2MEM_DB_PATH` | `./text2mem.db` | SQLite 数据库路径 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务器 URL |
| `OPENAI_API_KEY` | - | OpenAI API 密钥 |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | OpenAI API 基础 URL |

---

## 🆘 故障排除

### 常见问题

#### 问题："Provider not configured"

**原因**：`.env` 文件缺失或不完整

**解决方案**：
```bash
cp .env.example .env
python manage.py config
```

---

#### 问题："Ollama connection failed"

**原因**：Ollama 服务器未运行或 URL 错误

**解决方案**：
```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/version

# 如果没有，启动 Ollama
ollama serve

# 如果使用自定义主机，检查 .env 中的 URL
echo $OLLAMA_BASE_URL
```

---

#### 问题："Model not found (Ollama)"

**原因**：模型未拉取

**解决方案**：
```bash
# 列出可用模型
ollama list

# 拉取缺失的模型
ollama pull nomic-embed-text
ollama pull qwen2:0.5b
```

---

#### 问题："OpenAI API error 401"

**原因**：API 密钥无效或缺失

**解决方案**：
```bash
# 检查 .env 中的 API 密钥
grep OPENAI_API_KEY .env

# 从 https://platform.openai.com/api-keys 获取新密钥
# 使用有效密钥更新 .env
```

---

#### 问题："OpenAI API error 429"

**原因**：超出速率限制或配额不足

**解决方案**：
- 在 https://platform.openai.com/usage 检查使用情况
- 验证计费设置
- 等待速率限制重置
- 如需升级计划

---

#### 问题："Database locked"

**原因**：多个进程访问同一数据库

**解决方案**：
```bash
# 每个进程使用不同的数据库
TEXT2MEM_DB_PATH=./test_db.db

# 或使用内存数据库测试
TEXT2MEM_DB_PATH=:memory:
```

---

### 安全最佳实践

#### ⚠️ 永远不要提交真实 API 密钥

1. **使用 `.env.local` 存储密钥**
   - 将真实 API 密钥添加到 `.env.local`
   - 保持 `.env` 使用占位符值

2. **验证 .gitignore**
   ```bash
   grep "\.env\.local" .gitignore
   ```

3. **立即轮换泄露的密钥**
   - 在提供者控制台撤销旧密钥
   - 生成新密钥
   - 更新 `.env.local`

4. **在 CI/CD 中使用环境变量**
   - 永远不要在代码中硬编码密钥
   - 使用 GitHub Secrets 或类似工具

---

### 性能调优

#### Ollama 性能

**更快的推理**：
- 使用较小的模型（qwen2:0.5b 而不是 qwen2.5:7b）
- 增加 RAM 分配
- 如果可用，使用 GPU

**检查 Ollama 状态**：
```bash
ollama ps
```

#### OpenAI 性能

**降低成本**：
- 使用 `gpt-4o-mini` 而不是 `gpt-4o`
- 使用 `text-embedding-3-small` 而不是 `text-embedding-3-large`
- 为重复查询实现缓存

**监控使用情况**：
- https://platform.openai.com/usage

---

## 🔍 配置验证

### 快速验证脚本

```bash
#!/bin/bash
echo "=== Text2Mem 配置检查 ==="

# 检查 .env 是否存在
if [ -f .env ]; then
    echo "✅ .env 已找到"
else
    echo "❌ .env 未找到"
    exit 1
fi

# 检查提供者
PROVIDER=$(grep TEXT2MEM_PROVIDER .env | cut -d'=' -f2)
echo "提供者: $PROVIDER"

# 提供者特定检查
if [ "$PROVIDER" = "ollama" ]; then
    echo "检查 Ollama..."
    curl -s http://localhost:11434/api/version && echo "✅ Ollama 运行中" || echo "❌ Ollama 未运行"
elif [ "$PROVIDER" = "openai" ]; then
    echo "检查 OpenAI..."
    grep -q "sk-" .env && echo "✅ API 密钥已找到" || echo "❌ API 密钥缺失"
fi

# 使用 manage.py 测试
python manage.py status
```

---

<div align="center">

**Last Updated | 最后更新**: 2026-01-07  
**Version | 版本**: v1.2.0

[⬆ Back to top | 返回顶部](#configuration-guide--配置指南)

</div>

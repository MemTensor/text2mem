<div align="center">

# Configuration File Guide | 配置文件说明

**Guide for benchmark generation configuration files**  
**基准生成配置文件指南**

</div>

---

[English](#english) | [中文](#中文)

---

# English

## 📁 File List

| File | Purpose | Status |
|------|---------|--------|
| `generation_plan.yaml` | Main configuration file | ✅ Active |
| `generation_plan_examples.yaml` | Configuration examples | 📖 Reference |
| `config.yaml` | Legacy config (compatibility) | ⚠️ Kept |

## 🔑 API Key and Base URL Configuration

### Three Configuration Methods

#### 1. Use Environment Variables (Recommended) ⭐

**Pros**: Secure, simple, won't expose to Git

```bash
# Set environment variables
export OPENAI_API_KEY=sk-your-key
export OPENAI_API_BASE=https://api.openai.com/v1  # Optional
```

```yaml
# Don't set in config file
llm:
  provider: openai
  model: gpt-4-turbo-preview
  # api_key and base_url auto-read from environment
```

#### 2. Use Environment Variable Placeholders (Team Collaboration) ⭐

**Pros**: Config file can be committed to Git without exposing real keys

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  api_key: "${OPENAI_API_KEY}"        # Placeholder
  base_url: "${OPENAI_API_BASE}"      # Placeholder
```

Team members set their own environment variables:
```bash
export OPENAI_API_KEY=sk-their-own-key
```

#### 3. Direct Configuration (Not Recommended) ⚠️

**Cons**: Exposes keys, not secure

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  api_key: "sk-your-actual-key"       # ⚠️ Will expose
  base_url: "https://api.openai.com/v1"
```

## 📊 Configuration Priority

### API Key Reading Order

1. **Direct config setting**: `api_key: 'sk-xxx'`
2. **Config placeholder**: `api_key: '${OPENAI_API_KEY}'`
3. **System environment variable**: 
   - OpenAI: `OPENAI_API_KEY`
   - Anthropic: `ANTHROPIC_API_KEY`

### Base URL Reading Order

1. **Direct config setting**: `base_url: 'https://...'`
2. **Config placeholder**: `base_url: '${OPENAI_API_BASE}'`
3. **System environment variable**:
   - OpenAI: `OPENAI_API_BASE` or `OPENAI_BASE_URL`
   - Ollama: `OLLAMA_HOST` or `OLLAMA_BASE_URL`
4. **Use default**:
   - OpenAI: `https://api.openai.com/v1`
   - Ollama: `http://localhost:11434`
   - Anthropic: `https://api.anthropic.com`

## 🌐 Different Provider Configurations

### OpenAI

```bash
# Set environment variables
export OPENAI_API_KEY=sk-your-key

# Optional: use proxy
export OPENAI_API_BASE=https://your-proxy.com/v1
```

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  # Or use gpt-3.5-turbo (cheaper)
```

### Ollama (Local/Remote)

```bash
# Local (default)
ollama serve

# Or use remote Ollama
export OLLAMA_HOST=http://192.168.1.100:11434
```

```yaml
llm:
  provider: ollama
  model: qwen2:7b
  # base_url: http://localhost:11434  # Optional, default value
  timeout: 120  # Ollama may need more time
```

### Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
```

```yaml
llm:
  provider: anthropic
  model: claude-3-opus-20240229
```

## 📝 Common Configuration Scenarios

### Scenario 1: Development Testing

```yaml
plan:
  total_samples: 10
  batch_size: 2

llm:
  provider: openai
  model: gpt-3.5-turbo  # Cheaper
  temperature: 0.7
  max_tokens: 1000      # Reduce cost
```

### Scenario 2: Production

```yaml
plan:
  total_samples: 100
  batch_size: 10

llm:
  provider: openai
  model: gpt-4-turbo-preview
  temperature: 0.7
  max_tokens: 4000
```

### Scenario 3: Using Proxy

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  base_url: "https://your-openai-proxy.com/v1"
```

### Scenario 4: Local Ollama (Free)

```yaml
llm:
  provider: ollama
  model: qwen2:7b
  base_url: http://localhost:11434
  timeout: 120
```

## 🧪 Test Configuration

Verify configuration is correct:

```bash
# Run config test
python bench/generate/tests/test_llm_config.py

# Run system test
python bench/generate/tests/test_system.py
```

## 💡 Best Practices

1. ✅ **Use environment variables** - Don't write API keys in config files
2. ✅ **Use placeholders** - Use `${VAR_NAME}` in team configs
3. ✅ **Configure .gitignore** - Ensure files with real keys won't be committed
4. ✅ **Test first** - Test with small samples first
5. ✅ **Document** - Explain which environment variables need to be set

## ⚠️ Security Tips

- ❌ **Don't** write API keys directly in config files
- ❌ **Don't** commit config files with real keys to Git
- ❌ **Don't** share config files publicly
- ✅ **Use** environment variables or key management systems
- ✅ **Rotate** API keys regularly

## 📚 Related Documentation

- [QUICKSTART.md](../docs/QUICKSTART.md) - Quick setup guide
- [EXAMPLES.md](../docs/EXAMPLES.md) - Usage examples
- [generation_plan_examples.yaml](generation_plan_examples.yaml) - 8 config examples

---

# 中文

## 📁 文件列表

| 文件 | 用途 | 状态 |
|------|------|------|
| `generation_plan.yaml` | 主配置文件 | ✅ 使用中 |
| `generation_plan_examples.yaml` | 配置示例集合 | 📖 参考 |
| `config.yaml` | 旧版配置（兼容） | ⚠️ 保留 |

## 🔑 API Key 和 Base URL 配置

### 三种配置方式

#### 1. 使用环境变量（推荐）⭐

**优点**: 安全、简单、不会暴露到 Git

```bash
# 设置环境变量
export OPENAI_API_KEY=sk-your-key
export OPENAI_API_BASE=https://api.openai.com/v1  # 可选
```

```yaml
# 配置文件中不设置
llm:
  provider: openai
  model: gpt-4-turbo-preview
  # api_key 和 base_url 不配置，自动从环境变量读取
```

#### 2. 使用环境变量占位符（团队协作推荐）⭐

**优点**: 配置文件可以提交到 Git，但不会暴露真实 key

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  api_key: "${OPENAI_API_KEY}"        # 占位符
  base_url: "${OPENAI_API_BASE}"      # 占位符
```

团队成员各自设置环境变量：
```bash
export OPENAI_API_KEY=sk-their-own-key
```

#### 3. 直接配置（不推荐）⚠️

**缺点**: 会暴露 key，不安全

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  api_key: "sk-your-actual-key"       # ⚠️ 会暴露
  base_url: "https://api.openai.com/v1"
```

## 📊 配置优先级

### API Key 读取顺序

1. **配置文件直接设置**: `api_key: 'sk-xxx'`
2. **配置文件环境变量占位符**: `api_key: '${OPENAI_API_KEY}'`
3. **系统环境变量**: 
   - OpenAI: `OPENAI_API_KEY`
   - Anthropic: `ANTHROPIC_API_KEY`

### Base URL 读取顺序

1. **配置文件直接设置**: `base_url: 'https://...'`
2. **配置文件环境变量占位符**: `base_url: '${OPENAI_API_BASE}'`
3. **系统环境变量**:
   - OpenAI: `OPENAI_API_BASE` 或 `OPENAI_BASE_URL`
   - Ollama: `OLLAMA_HOST` 或 `OLLAMA_BASE_URL`
4. **使用默认值**:
   - OpenAI: `https://api.openai.com/v1`
   - Ollama: `http://localhost:11434`
   - Anthropic: `https://api.anthropic.com`

## 🌐 不同提供商的配置

### OpenAI

```bash
# 设置环境变量
export OPENAI_API_KEY=sk-your-key

# 可选：使用代理
export OPENAI_API_BASE=https://your-proxy.com/v1
```

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  # 或使用 gpt-3.5-turbo（更便宜）
```

### Ollama（本地/远程）

```bash
# 本地（默认）
ollama serve

# 或使用远程 Ollama
export OLLAMA_HOST=http://192.168.1.100:11434
```

```yaml
llm:
  provider: ollama
  model: qwen2:7b
  # base_url: http://localhost:11434  # 可选，默认值
  timeout: 120  # Ollama 可能需要更长时间
```

### Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
```

```yaml
llm:
  provider: anthropic
  model: claude-3-opus-20240229
```

## 📝 常见配置场景

### 场景1: 开发测试

```yaml
plan:
  total_samples: 10
  batch_size: 2

llm:
  provider: openai
  model: gpt-3.5-turbo  # 便宜
  temperature: 0.7
  max_tokens: 1000      # 减少消耗
```

### 场景2: 生产环境

```yaml
plan:
  total_samples: 100
  batch_size: 10

llm:
  provider: openai
  model: gpt-4-turbo-preview
  temperature: 0.7
  max_tokens: 4000
```

### 场景3: 使用代理

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  base_url: "https://your-openai-proxy.com/v1"
```

### 场景4: 本地 Ollama（免费）

```yaml
llm:
  provider: ollama
  model: qwen2:7b
  base_url: http://localhost:11434
  timeout: 120
```

## 🧪 测试配置

验证配置是否正确：

```bash
# 运行配置测试
python bench/generate/tests/test_llm_config.py

# 运行系统测试
python bench/generate/tests/test_system.py
```

## 💡 最佳实践

1. ✅ **使用环境变量** - 不要在配置文件中写 API key
2. ✅ **使用占位符** - 团队协作时在配置中使用 `${VAR_NAME}`
3. ✅ **配置 .gitignore** - 确保不会提交含有真实 key 的文件
4. ✅ **测试优先** - 先用小样本测试配置
5. ✅ **文档化** - 在团队中说明需要设置哪些环境变量

## ⚠️ 安全提示

- ❌ **不要**在配置文件中直接写 API key
- ❌ **不要**将含有真实 key 的配置文件提交到 Git
- ❌ **不要**在公开的地方分享配置文件
- ✅ **使用**环境变量或密钥管理系统
- ✅ **定期轮换** API key

## 📚 相关文档

- [QUICKSTART.md](../docs/QUICKSTART.md) - 快速配置指南
- [EXAMPLES.md](../docs/EXAMPLES.md) - 使用示例
- [generation_plan_examples.yaml](generation_plan_examples.yaml) - 8个配置示例

---

<div align="center">

**Last Updated | 最后更新**: 2026-01-07  
**Version | 版本**: v3.0

[⬆ Back to top | 返回顶部](#configuration-file-guide--配置文件说明)

</div>

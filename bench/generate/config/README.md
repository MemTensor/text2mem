# 配置文件说明

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

**更新时间**: 2025-01-07  
**版本**: v3.0

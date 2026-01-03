# Configuration Guide

## Quick Start

### 1. Copy Environment Template

```bash
cp .env.example .env
```

The default `.env` uses **mock provider** (no LLM required, perfect for testing).

### 2. Choose Your Provider

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
```

#### Option C: OpenAI (Cloud API)
```bash
TEXT2MEM_PROVIDER=openai
TEXT2MEM_EMBEDDING_MODEL=text-embedding-3-small
TEXT2MEM_GENERATION_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_API_BASE=https://api.openai.com/v1
```

### 3. Verify Configuration

```bash
python manage.py status
```

## Advanced Configuration

### Using .env.local

For local development with sensitive data:

```bash
# Copy the local example
cp .env.local.example .env.local

# Edit with your real credentials
nano .env.local
```

**`.env.local` is automatically ignored by git** and takes precedence over `.env`.

## Security Best Practices

### ⚠️ Never Commit Real API Keys

1. **Use `.env.local` for secrets**
2. **Keep `.env` with placeholder values**
3. **Rotate compromised keys immediately**

See full documentation at [docs/CONFIGURATION.md](docs/CONFIGURATION.md.old)

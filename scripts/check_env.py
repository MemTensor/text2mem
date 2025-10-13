#!/usr/bin/env python3
"""
Environment Configuration Checker for Text2Mem

Validates environment variables and prints current configuration.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text2mem.core.config import load_env_vars

def check_env():
    """Check and display environment configuration."""
    load_env_vars()
    
    print("=" * 80)
    print("Text2Mem Environment Configuration")
    print("=" * 80)
    
    # Database Configuration
    print("\n📁 Database Configuration:")
    print(f"  DB_PATH:    {os.getenv('TEXT2MEM_DB_PATH', '(default: ./text2mem.db)')}")
    print(f"  DB_WAL:     {os.getenv('TEXT2MEM_DB_WAL', '(default: true)')}")
    print(f"  DB_TIMEOUT: {os.getenv('TEXT2MEM_DB_TIMEOUT', '(default: 30)')}s")
    
    # Model Provider Configuration
    print("\n🤖 Model Provider Configuration:")
    provider = os.getenv('TEXT2MEM_PROVIDER') or os.getenv('MODEL_SERVICE') or '(default: ollama)'
    print(f"  PROVIDER:            {provider}")
    print(f"  EMBEDDING_PROVIDER:  {os.getenv('TEXT2MEM_EMBEDDING_PROVIDER', f'(inherits: {provider})')}")
    print(f"  GENERATION_PROVIDER: {os.getenv('TEXT2MEM_GENERATION_PROVIDER', f'(inherits: {provider})')}")
    
    # Embedding Model Configuration
    print("\n🔢 Embedding Model Configuration:")
    print(f"  MODEL: {os.getenv('TEXT2MEM_EMBEDDING_MODEL', '(default: provider-specific)')}")
    
    # Generation Model Configuration
    print("\n💬 Generation Model Configuration:")
    print(f"  MODEL:       {os.getenv('TEXT2MEM_GENERATION_MODEL', '(default: provider-specific)')}")
    print(f"  TEMPERATURE: {os.getenv('TEXT2MEM_TEMPERATURE', '(default: 0.7)')}")
    print(f"  MAX_TOKENS:  {os.getenv('TEXT2MEM_MAX_TOKENS', '(default: 512)')}")
    print(f"  TOP_P:       {os.getenv('TEXT2MEM_TOP_P', '(default: 0.9)')}")
    
    # OpenAI Configuration
    print("\n🔑 OpenAI Configuration:")
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
        print(f"  API_KEY:      {masked_key}")
    else:
        print(f"  API_KEY:      (not set)")
    print(f"  API_BASE:     {os.getenv('OPENAI_API_BASE', '(default: https://api.openai.com/v1)')}")
    print(f"  ORGANIZATION: {os.getenv('OPENAI_ORGANIZATION', '(not set)')}")
    
    # Ollama Configuration
    print("\n🦙 Ollama Configuration:")
    print(f"  BASE_URL: {os.getenv('OLLAMA_BASE_URL', '(default: http://localhost:11434)')}")
    
    # Request Configuration
    print("\n⚙️ Request Configuration:")
    print(f"  TIMEOUT:     {os.getenv('TEXT2MEM_REQUEST_TIMEOUT', '(default: 60)')}s")
    print(f"  MAX_RETRIES: {os.getenv('TEXT2MEM_MAX_RETRIES', '(default: 3)')}")
    print(f"  BATCH_SIZE:  {os.getenv('TEXT2MEM_BATCH_SIZE', '(default: 10)')}")
    
    # Search Configuration
    print("\n🔍 Search/Retrieval Configuration:")
    print(f"  ALPHA (semantic):    {os.getenv('TEXT2MEM_SEARCH_ALPHA', '(default: 0.7)')}")
    print(f"  BETA (keyword):      {os.getenv('TEXT2MEM_SEARCH_BETA', '(default: 0.3)')}")
    print(f"  PHRASE_BONUS:        {os.getenv('TEXT2MEM_SEARCH_PHRASE_BONUS', '(default: 0.2)')}")
    print(f"  DEFAULT_LIMIT:       {os.getenv('TEXT2MEM_SEARCH_DEFAULT_LIMIT', '(default: 10)')}")
    print(f"  MAX_LIMIT:           {os.getenv('TEXT2MEM_SEARCH_MAX_LIMIT', '(default: 100)')}")
    print(f"  DEFAULT_K:           {os.getenv('TEXT2MEM_SEARCH_DEFAULT_K', '(default: 5)')}")
    
    # Bench Testing Configuration
    print("\n🧪 Bench Testing Configuration:")
    timeout = os.getenv('TEXT2MEM_BENCH_TIMEOUT')
    print(f"  TIMEOUT:  {timeout + 's' if timeout else '(no timeout)'}")
    print(f"  SPLIT:    {os.getenv('TEXT2MEM_BENCH_SPLIT', '(default: basic)')}")
    print(f"  MODE:     {os.getenv('TEXT2MEM_BENCH_MODE', '(default: auto)')}")
    print(f"  VERBOSE:  {os.getenv('TEXT2MEM_BENCH_VERBOSE', '(default: false)')}")
    
    # Bench Generation Configuration
    print("\n🔧 Bench Generation Configuration:")
    print(f"  PROVIDER:    {os.getenv('TEXT2MEM_BENCH_GEN_PROVIDER', '(default: openai)')}")
    print(f"  MODEL:       {os.getenv('TEXT2MEM_BENCH_GEN_MODEL', '(default: gpt-4o-mini)')}")
    print(f"  TEMPERATURE: {os.getenv('TEXT2MEM_BENCH_GEN_TEMPERATURE', '(default: 0.7)')}")
    print(f"  MAX_TOKENS:  {os.getenv('TEXT2MEM_BENCH_GEN_MAX_TOKENS', '(default: 4000)')}")
    print(f"  TIMEOUT:     {os.getenv('TEXT2MEM_BENCH_GEN_TIMEOUT', '(default: 120)')}s")
    
    # Logging Configuration
    print("\n📝 Logging Configuration:")
    print(f"  LOG_LEVEL: {os.getenv('TEXT2MEM_LOG_LEVEL', '(default: INFO)')}")
    print(f"  LANG:      {os.getenv('TEXT2MEM_LANG', '(default: en)')}")
    
    # Validation
    print("\n" + "=" * 80)
    print("Validation:")
    print("=" * 80)
    
    issues = []
    warnings = []
    
    # Check provider-specific requirements
    provider_lower = provider.lower() if isinstance(provider, str) else ''
    
    if 'openai' in provider_lower:
        if not os.getenv('OPENAI_API_KEY'):
            issues.append("❌ OPENAI_API_KEY is required when using OpenAI provider")
    
    if 'ollama' in provider_lower:
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        if 'localhost' in ollama_url or '127.0.0.1' in ollama_url:
            warnings.append("⚠️  Using localhost Ollama - ensure Ollama is running locally")
    
    # Check bench generation if using LLM generation
    bench_gen_provider = os.getenv('TEXT2MEM_BENCH_GEN_PROVIDER', 'openai')
    if bench_gen_provider == 'openai' and not os.getenv('OPENAI_API_KEY'):
        warnings.append("⚠️  Bench generation uses OpenAI but OPENAI_API_KEY is not set")
    
    # Check timeout values
    bench_timeout = os.getenv('TEXT2MEM_BENCH_TIMEOUT')
    if bench_timeout:
        try:
            timeout_val = float(bench_timeout)
            if timeout_val <= 0:
                warnings.append(f"⚠️  TEXT2MEM_BENCH_TIMEOUT={bench_timeout} is invalid (should be > 0 or empty)")
            elif timeout_val < 30:
                warnings.append(f"⚠️  TEXT2MEM_BENCH_TIMEOUT={bench_timeout}s might be too short for complex tests")
        except ValueError:
            issues.append(f"❌ TEXT2MEM_BENCH_TIMEOUT={bench_timeout} is not a valid number")
    
    # Check search configuration
    try:
        alpha = float(os.getenv('TEXT2MEM_SEARCH_ALPHA', '0.7'))
        if not 0.0 <= alpha <= 1.0:
            warnings.append(f"⚠️  TEXT2MEM_SEARCH_ALPHA={alpha} should be between 0.0 and 1.0")
    except ValueError:
        issues.append(f"❌ TEXT2MEM_SEARCH_ALPHA is not a valid number")
    
    try:
        beta = float(os.getenv('TEXT2MEM_SEARCH_BETA', '0.3'))
        if not 0.0 <= beta <= 1.0:
            warnings.append(f"⚠️  TEXT2MEM_SEARCH_BETA={beta} should be between 0.0 and 1.0")
    except ValueError:
        issues.append(f"❌ TEXT2MEM_SEARCH_BETA is not a valid number")
    
    try:
        alpha = float(os.getenv('TEXT2MEM_SEARCH_ALPHA', '0.7'))
        beta = float(os.getenv('TEXT2MEM_SEARCH_BETA', '0.3'))
        if alpha + beta > 1.2:
            warnings.append(f"⚠️  SEARCH_ALPHA + SEARCH_BETA = {alpha + beta:.2f} > 1.2 (might produce unexpected scores)")
    except ValueError:
        pass  # Already reported above
    
    try:
        phrase_bonus = float(os.getenv('TEXT2MEM_SEARCH_PHRASE_BONUS', '0.2'))
        if not 0.0 <= phrase_bonus <= 1.0:
            warnings.append(f"⚠️  TEXT2MEM_SEARCH_PHRASE_BONUS={phrase_bonus} should be between 0.0 and 1.0")
    except ValueError:
        issues.append(f"❌ TEXT2MEM_SEARCH_PHRASE_BONUS is not a valid number")
    
    # Print results
    if not issues and not warnings:
        print("✅ Configuration looks good!")
    else:
        if issues:
            print("\nIssues found:")
            for issue in issues:
                print(f"  {issue}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  {warning}")
    
    print("\n" + "=" * 80)
    
    # Return exit code
    return 1 if issues else 0

if __name__ == "__main__":
    sys.exit(check_env())

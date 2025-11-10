#!/usr/bin/env python3
"""
Text2Mem Project Management Utility

Provides a unified entry point for environment setup, demos, testing, 
and interactive features.

Quick Start:
  python manage.py status                     # Check environment status
  python manage.py config --provider ollama   # Configure environment
  python manage.py demo                       # Run demo
  python manage.py session                    # Enter interactive mode

Detailed Help:
  python manage.py help [command]             # View command help
"""
import os
import sys
import subprocess
import json
import argparse
import textwrap
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, List
from pathlib import Path

# Import core utilities
from scripts.cli_core import (
    echo, load_env_file, ENV_PATH as CORE_ENV_PATH,
    build_models_service_from_env as _build_models_service_from_env,
    build_engine_and_adapter as _build_engine_and_adapter,
)
from scripts.config_helpers import generate_grouped_env
from scripts.env_utils import which

ROOT = Path(__file__).parent
ENV_PATH = CORE_ENV_PATH

# Load environment variables on startup
ENV_VARS = load_env_file(ENV_PATH) if ENV_PATH.exists() else {}


@dataclass(frozen=True)
class CommandInfo:
    """Metadata for a CLI command."""
    name: str
    handler: Callable[[], Optional[int]]
    summary: str
    group: str
    aliases: Tuple[str, ...] = ()
    description: Optional[str] = None

    def matches(self, candidate: str) -> bool:
        """Check whether a command name or alias matches."""
        return candidate == self.name or candidate in self.aliases


# Command group display order
COMMAND_GROUPS: Tuple[Tuple[str, str], ...] = (
    ("core", "🔧 Core Configuration"),
    ("demos", "🎯 Demonstrations"),
    ("workflows", "📋 Workflow Execution"),
    ("interaction", "💬 Interactive Session"),
    ("models", "🤖 Model Management"),
    ("ops", "⚙️  Operations & Utilities"),
)

# ============================================================================
# Environment & Configuration Commands
# ============================================================================

def cmd_status():
    """Display environment and dependency status."""
    from text2mem.core.config import ModelConfig
    
    env_exists = ENV_PATH.exists()
    cfg = ModelConfig.from_env()
    db_path = os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
    
    echo("=" * 60)
    echo("📊 Text2Mem Environment Status / Text2Mem 环境状态")
    echo("=" * 60)
    
    echo("\n[Environment File / 环境文件]")
    if env_exists:
        echo(f"  ✅ .env configured -> {ENV_PATH} / 已配置")
    else:
        echo(f"  ⚠️  .env not found -> {ENV_PATH} / 未找到")
        echo(f"  💡 Run: python manage.py config --provider ollama / 运行此命令生成配置")
    
    echo("\n[Model Configuration / 模型配置]")
    echo(f"  Provider: {cfg.provider}")
    echo(f"  Embedding Model: {cfg.embedding_provider}:{cfg.embedding_model}")
    echo(f"  Generation Model: {cfg.generation_provider}:{cfg.generation_model}")
    
    if cfg.embedding_provider == 'ollama' or cfg.generation_provider == 'ollama':
        ollama_url = os.environ.get('TEXT2MEM_OLLAMA_BASE_URL') or \
                     os.environ.get('OLLAMA_BASE_URL') or \
                     cfg.ollama_base_url
        echo(f"  Ollama URL: {ollama_url}")
    
    if 'openai' in (cfg.provider, cfg.embedding_provider, cfg.generation_provider):
        api_key_set = bool(os.environ.get('OPENAI_API_KEY'))
        echo(f"  OpenAI API Key: {'✅ Set / 已设置' if api_key_set else '❌ Not Set / 未设置'}")
    
    echo("\n[Database / 数据库]")
    db_exists = Path(db_path).exists()
    echo(f"  Path: {db_path}")
    echo(f"  Status: {'✅ Exists / 已存在' if db_exists else '⚠️  Not Created (auto-created on first use) / 未创建（首次使用时自动创建）'}")
    
    echo("\n[Dependencies / 依赖工具]")
    echo(f"  ollama: {'✅ Available / 可用' if which('ollama') else '❌ Not Installed / 未安装'}")
    echo(f"  pytest: {'✅ Available / 可用' if which('pytest') else '⚠️  Not Installed / 未安装'}")
    
    echo("")
    return 0


def cmd_config():
    """Generate or update .env file."""
    parser = argparse.ArgumentParser(prog='manage.py config', add_help=False)
    parser.add_argument('--provider', choices=['mock','ollama','openai'], required=True)
    parser.add_argument('--openai-key', default=None)
    parser.add_argument('--ollama-base-url', default='http://localhost:11434')
    parser.add_argument('--embed-model', default=None)
    parser.add_argument('--gen-model', default=None)
    parser.add_argument('--db-path', default='./text2mem.db', help='Database path / 数据库路径')
    try:
        args = parser.parse_args(sys.argv[2:])
    except SystemExit:
        echo('Usage / 用法: manage.py config --provider [mock|ollama|openai] [--openai-key ...] [--db-path ...]')
        return 2

    existing = dict(ENV_VARS)
    provider = args.provider
    existing['MODEL_SERVICE'] = provider
    existing['TEXT2MEM_PROVIDER'] = provider
    existing['TEXT2MEM_EMBEDDING_PROVIDER'] = 'openai' if provider=='openai' else ('ollama' if provider=='ollama' else provider)
    existing['TEXT2MEM_GENERATION_PROVIDER'] = existing['TEXT2MEM_EMBEDDING_PROVIDER']
    existing['TEXT2MEM_DB_PATH'] = args.db_path

    if provider == 'mock':
        existing.setdefault('TEXT2MEM_EMBEDDING_MODEL', 'dummy-embedding')
        existing.setdefault('TEXT2MEM_GENERATION_MODEL', 'dummy-llm')
    elif provider == 'ollama':
        existing['TEXT2MEM_OLLAMA_BASE_URL'] = args.ollama_base_url
        existing['OLLAMA_BASE_URL'] = args.ollama_base_url
        existing['TEXT2MEM_EMBEDDING_MODEL'] = args.embed_model or 'nomic-embed-text'
        existing['TEXT2MEM_GENERATION_MODEL'] = args.gen_model or 'qwen2.5:0.5b'
    else:  # openai
        if args.openai_key:
            existing['OPENAI_API_KEY'] = args.openai_key
        existing['TEXT2MEM_EMBEDDING_MODEL'] = args.embed_model or 'text-embedding-3-small'
        existing['TEXT2MEM_GENERATION_MODEL'] = args.gen_model or 'gpt-4o-mini'

    content = generate_grouped_env(existing, provider)
    ENV_PATH.write_text(content, encoding='utf-8')
    echo(f"✅ .env written successfully -> {ENV_PATH} / 已写入 .env 文件")
    echo(f"💡 Tip: Run 'python manage.py status' to verify configuration / 提示：可运行命令验证配置")
    return 0


def cmd_setup_ollama():
    """Download commonly used Ollama models."""
    exe = which('ollama')
    if not exe:
        echo('❌ Ollama executable not found, please install first / 未找到 Ollama 可执行文件，请先安装 https://ollama.ai')
        echo('💡 Installation guide: https://github.com/ollama/ollama#readme')
        return 1
    
    from text2mem.core.config import ModelConfig
    cfg = ModelConfig.for_ollama()
    emb = os.environ.get('TEXT2MEM_EMBEDDING_MODEL') or cfg.embedding_model
    gen = os.environ.get('TEXT2MEM_GENERATION_MODEL') or cfg.generation_model
    
    echo("🚀 Starting Ollama model downloads... / 开始拉取 Ollama 模型...")
    echo(f"⬇️  Embedding Model: {emb} / 嵌入模型")
    try:
        subprocess.run([exe, 'pull', emb], check=True)
        echo(f"✅ {emb} download complete / 下载完成")
    except Exception as e:
        echo(f"❌ Failed to download {emb}: {e} / 拉取失败")
        return 1
    
    echo(f"⬇️  Generation Model: {gen} / 生成模型")
    try:
        subprocess.run([exe, 'pull', gen], check=True)
        echo(f"✅ {gen} download complete / 下载完成")
    except Exception as e:
        echo(f"❌ Failed to download {gen}: {e} / 拉取失败")
        return 1
    
    echo('🎉 All models downloaded successfully! / 所有模型下载完成！')
    echo('💡 Run python manage.py models-smoke to test / 运行命令测试模型')
    return 0


def cmd_setup_openai():
    """Initialize OpenAI configuration into .env."""
    parser = argparse.ArgumentParser(prog='manage.py setup-openai', add_help=False)
    parser.add_argument('--api-key', dest='api_key', default=None)
    try:
        args = parser.parse_args(sys.argv[2:])
    except SystemExit:
        echo('Usage / 用法: manage.py setup-openai [--api-key sk-...]'); return 2
    existing = dict(ENV_VARS)
    existing['MODEL_SERVICE'] = 'openai'
    existing['TEXT2MEM_PROVIDER'] = 'openai'
    existing['TEXT2MEM_EMBEDDING_PROVIDER'] = 'openai'
    existing['TEXT2MEM_GENERATION_PROVIDER'] = 'openai'
    if args.api_key:
        existing['OPENAI_API_KEY'] = args.api_key
    existing.setdefault('TEXT2MEM_EMBEDDING_MODEL', 'text-embedding-3-small')
    existing.setdefault('TEXT2MEM_GENERATION_MODEL', 'gpt-3.5-turbo')
    content = generate_grouped_env(existing, 'openai')
    ENV_PATH.write_text(content, encoding='utf-8')
    echo(f"✅ .env updated successfully -> {ENV_PATH} / 已更新 .env 文件")
    return 0


def cmd_test():
    """Run tests (pytest preferred, otherwise minimal smoke test)."""
    parser = argparse.ArgumentParser(prog='manage.py test', add_help=False)
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-k', '--keyword', default=None, help='Run tests matching keyword')
    parser.add_argument('--smoke', action='store_true', help='Run only smoke test')
    try:
        args = parser.parse_args(sys.argv[2:])
    except SystemExit:
        args = argparse.Namespace(verbose=False, keyword=None, smoke=False)
    
    if args.smoke:
        echo('🧪 Running minimal smoke test... / 运行最小冒烟测试...')
        try:
            service = _build_models_service_from_env(None)
            emb = service.encode_memory('hello embeddings')
            echo(f"✅ Embedding ok, dim={emb.dimension}, model={emb.model}")
            gen = service.generation_model.generate('Summarize in one sentence: What is Text2Mem? / 一句话总结：Text2Mem 是什么？')
            echo(f"✅ Generation ok, model={gen.model}")
            echo(f"📝 Output: {gen.text[:100]}...")
            return 0
        except Exception as e:
            echo(f"❌ Smoke test failed: {e} / 冒烟测试失败")
            return 1
    
    try:
        cmd = [sys.executable, '-m', 'pytest']
        if args.verbose:
            cmd.append('-v')
        else:
            cmd.append('-q')
        if args.keyword:
            cmd.extend(['-k', args.keyword])
        
        echo(f"🧪 Running tests: {' '.join(cmd)} / 运行测试")
        r = subprocess.run(cmd, cwd=str(ROOT))
        return r.returncode
    except Exception as e:
        echo(f'⚠️ Unable to run pytest: {e} / 无法运行 pytest')
        echo('💡 Install pytest: pip install pytest / 可通过此命令安装 pytest')
        return 1


def cmd_models_info():
    """Display current model configuration."""
    from text2mem.core.config import ModelConfig
    cfg = ModelConfig.from_env()
    
    echo("=" * 60)
    echo("🤖 Model Configuration Details / 模型配置详情")
    echo("=" * 60)
    echo(f"\n[General / 总体配置]")
    echo(f"  Provider: {cfg.provider}")
    
    echo(f"\n[Embedding Model / 嵌入模型]")
    echo(f"  Provider: {cfg.embedding_provider}")
    echo(f"  Model: {cfg.embedding_model}")
    
    echo(f"\n[Generation Model / 生成模型]")
    echo(f"  Provider: {cfg.generation_provider}")
    echo(f"  Model: {cfg.generation_model}")
    
    if cfg.embedding_provider == 'ollama' or cfg.generation_provider == 'ollama':
        echo(f"\n[Ollama Configuration / Ollama 配置]")
        echo(f"  Base URL: {cfg.ollama_base_url}")
    
    if cfg.embedding_provider == 'openai' or cfg.generation_provider == 'openai':
        echo(f"\n[OpenAI Configuration / OpenAI 配置]")
        api_key = os.environ.get('OPENAI_API_KEY', '')
        echo(f"  API Key: {'✅ Set (' + api_key[:8] + '...) / 已设置' if api_key else '❌ Not Set / 未设置'}")
        if os.environ.get('OPENAI_API_BASE'):
            echo(f"  API Base: {os.environ.get('OPENAI_API_BASE')}")
    
    echo("")
    return 0

def cmd_ir():
    """Execute a single IR JSON command."""
    parser = argparse.ArgumentParser(prog='manage.py ir', add_help=False)
    parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', dest='file_path')
    group.add_argument('--inline', dest='inline_json')
    parser.add_argument('--db', dest='db_path', default=None)
    try:
        args = parser.parse_args(sys.argv[2:])
    except SystemExit:
        echo("Usage / 用法: manage.py ir [--mode mock|ollama|openai|auto] (--file path.json | --inline '{...}') [--db path]"); 
        return 2

    service, engine = _build_engine_and_adapter(args.mode, args.db_path)
    if args.file_path:
        ir = json.loads(Path(args.file_path).read_text(encoding='utf-8'))
    else:
        ir = json.loads(args.inline_json)
    res = engine.execute(ir)
    if not getattr(res, 'success', False):
        echo(f"❌ Execution failed: {res.error} / 执行失败"); 
        return 1
    data = res.data or {}
    try:
        preview = json.dumps(data, ensure_ascii=False)[:400]
    except Exception:
        preview = str(data)[:400]
    echo(f"✅ Execution successful | {preview}{'…' if len(preview)>=400 else ''} / 执行成功")
    return 0


def cmd_run_demo():
    """Run demonstration: batch execution of predefined workflows or single IR samples.
    
    Usage / 用法:
      python manage.py demo [--mode mock|ollama|openai|auto] [--db path] [--set workflows|individual|scenarios]

    - workflows: Run multi-step operation workflows under examples/op_workflows
    - individual: Execute individual IR examples under examples/ir_operations
    - scenarios: Run realistic scenario workflows under examples/real_world_scenarios
    """
    parser = argparse.ArgumentParser(prog='manage.py demo', add_help=False)
    parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
    parser.add_argument('--db', dest='db_path', default=None)
    parser.add_argument('--set', choices=['workflows','individual','scenarios'], default='workflows')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    try:
        args = parser.parse_args(sys.argv[2:])
    except SystemExit:
        echo('Usage / 用法: python manage.py demo [--mode mock|ollama|openai|auto] [--db path] [--set workflows|individual|scenarios] [--verbose]')
        return 2

    service, engine = _build_engine_and_adapter(args.mode, args.db_path)
    db_path_display = args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
    
    echo("=" * 60)
    echo("🎯 Text2Mem Demo Mode / Text2Mem 演示模式")
    echo("=" * 60)
    echo(f"🧠 Model Service: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
    echo(f"🗄️  Database: {db_path_display} / 数据库")
    echo(f"📦 Demo Set: {args.set} / 演示集")
    echo("=" * 60)
    echo("")

    from text2mem.core.engine import Text2MemEngine
    from text2mem.adapters.sqlite_adapter import SQLiteAdapter
    adapter = SQLiteAdapter(args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db', models_service=service)
    engine = Text2MemEngine(adapter=adapter, models_service=service)

    import json as _json

    def _echo_ir_result(ir_obj, out, verbose=False):
        op = ir_obj.get('op') if isinstance(ir_obj, dict) else None
        if verbose:
            try:
                echo(f"   📄 Full Output: {_json.dumps(out, ensure_ascii=False)[:300]}... / 完整输出")
            except Exception:
                pass
        
        if op == 'Encode':
            rid = None
            if isinstance(out, dict):
                rid = out.get('inserted_id') or out.get('id')
            echo(f"   ✅ Encode | id={rid} dim={out.get('embedding_dim') if isinstance(out, dict) else 'n/a'} / 编码成功")
        elif op == 'Retrieve':
            if isinstance(out, list):
                rows = out
            elif isinstance(out, dict):
                rows = out.get('rows') or out.get('matches') or []
            else:
                rows = []
            echo(f"   ✅ Retrieve | {len(rows)} records retrieved / 检索到 {len(rows)} 条记录")
            if verbose and rows:
                for idx, row in enumerate(rows[:2], 1):
                    echo(f"      [{idx}] {str(row)[:80]}...")
        elif op == 'Summarize':
            summary = ''
            if isinstance(out, dict):
                summary = str(out.get('summary',''))
            echo(f"   ✅ Summarize | {summary[:100]}{'…' if len(summary)>100 else ''} / 摘要生成")
        else:
            affected = None
            if isinstance(out, dict):
                affected = out.get('affected_rows') or out.get('updated_rows') or out.get('success_count')
            if affected is not None:
                echo(f"   ✅ {op} | affected rows: {affected} / 受影响行数")
            else:
                echo(f"   ✅ {op} | Completed / 完成")

    ran = 0
    failed = 0
    
    # --- Individual IR examples ---
    if args.set == 'individual':
        ir_dir = ROOT / 'examples' / 'ir_operations'
        if not ir_dir.exists():
            echo(f'ℹ️  Directory not found: {ir_dir} / 目录不存在')
            return 0
        files = sorted(ir_dir.glob('*.json'))
        if not files:
            echo('ℹ️  No examples found in examples/ir_operations / 未找到示例文件')
            return 0
        for path in files:
            ir = _json.loads(path.read_text(encoding='utf-8'))
            echo(f"🚀 Executing {path.name} -> {ir.get('op')} ({ir.get('stage')}) / 执行示例")
            try:
                res = engine.execute(ir)
            except Exception as e:
                echo(f"❌ Execution error: {e} / 执行异常")
                failed += 1
                continue
            if not getattr(res, 'success', False):
                echo(f"❌ Failed: {res.error} / 执行失败")
                failed += 1
                continue
            out = res.data or {}
            _echo_ir_result(ir, out, args.verbose)
            ran += 1
        echo(f"\n{'='*60}")
        echo(f"🎉 Demo Complete | Success: {ran} | Failed: {failed} / 演示完成")
        return 0 if failed == 0 else 1

    # --- Scenario workflows ---
    if args.set == 'scenarios':
        wf_dir = ROOT / 'examples' / 'real_world_scenarios'
        if not wf_dir.exists():
            echo(f'ℹ️  Directory not found: {wf_dir} / 目录不存在')
            return 0
        files = sorted(wf_dir.glob('*.json'))
        if not files:
            echo('ℹ️  No workflows found in examples/real_world_scenarios / 未找到工作流文件')
            return 0
        for path in files:
            data = _json.loads(path.read_text(encoding='utf-8'))
            steps = data.get('steps', [])
            echo(f"🚀 Running Scenario: {path.name} | {len(steps)} steps / 运行场景工作流")
            for i, step in enumerate(steps, start=1):
                ir = step.get('ir') or step
                title = step.get('name') or step.get('description') or f'step {i}'
                echo(f"➡️  [{i}/{len(steps)}] {title} -> {ir.get('op')} / 执行步骤")
                try:
                    res = engine.execute(ir)
                except Exception as e:
                    echo(f"❌ Execution error: {e} / 执行异常")
                    failed += 1
                    continue
                if not getattr(res, 'success', False):
                    echo(f"❌ Failed: {res.error} / 失败")
                    failed += 1
                    continue
                out = res.data or {}
                _echo_ir_result(ir, out, args.verbose)
                ran += 1
        echo(f"\n{'='*60}")
        echo(f"🎉 Demo Complete | Success: {ran} | Failed: {failed} / 演示完成")
        return 0 if failed == 0 else 1

    # --- Operation workflows (default) ---
    wf_dir = ROOT / 'examples' / 'op_workflows'
    if not wf_dir.exists():
        echo(f'ℹ️  Directory not found: {wf_dir} / 目录不存在')
        return 0
    
    files = [
        'op_encode.json', 'op_label.json', 'op_label_search.json', 'op_label_via_search.json',
        'op_promote.json', 'op_promote_search.json', 'op_promote_remind.json',
        'op_demote.json', 'op_update.json', 'op_delete_search.json',
        'op_update_via_search.json', 'op_delete.json', 'op_lock.json',
        'op_expire.json', 'op_split.json', 'op_split_custom.json', 'op_merge.json',
        'op_retrieve.json', 'op_summarize.json',
    ]
    for name in files:
        path = wf_dir / name
        if not path.exists():
            continue
        data = _json.loads(path.read_text(encoding='utf-8'))
        steps = data.get('steps', [])
        echo(f"🚀 Running Workflow: {name} | {len(steps)} steps / 运行工作流")
        for i, step in enumerate(steps, start=1):
            ir = step.get('ir') or step
            title = step.get('name') or f'step {i}'
            echo(f"➡️  [{i}/{len(steps)}] {title} -> {ir.get('op')} / 执行步骤")
            try:
                res = engine.execute(ir)
            except Exception as e:
                echo(f"❌ Execution error: {e} / 执行异常")
                failed += 1
                continue
            if not getattr(res, 'success', False):
                echo(f"❌ Failed: {res.error} / 失败")
                failed += 1
                continue
            out = res.data or {}
            _echo_ir_result(ir, out, args.verbose)
            ran += 1
    echo(f"\n{'='*60}")
    echo(f"🎉 Demo Complete | Success: {ran} | Failed: {failed} / 演示完成")
    return 0 if failed == 0 else 1


def cmd_list_workflows():
    """List built-in workflow JSON files."""
    candidates = [
        ROOT / "examples" / "real_world_scenarios", 
        ROOT / "examples" / "op_workflows", 
        ROOT / "text2mem" / "examples"
    ]
    files = []
    for d in candidates:
        if d.exists():
            files += [p for p in d.glob("*.json")]
    if not files:
        echo("ℹ️ No workflow files found / 未找到任何工作流文件"); 
        return 0
    echo("📚 Available Workflow Files / 可用工作流文件：")
    for p in sorted(files):
        echo(f"  - {p.relative_to(ROOT)}")
    return 0

def cmd_session():
	"""Persistent interactive session mode — allows specifying database, mode, 
	and loading script files to execute commands or enter interactively.

	Usage / 用法:
	  python manage.py session [--mode mock|ollama|openai|auto] [--db path] [--script file]

	Available commands:
	  help                Show help / 显示帮助
	  list                List script lines / 列出脚本行
	  next / n            Execute next script line / 执行下一行脚本
	  run <idx>           Execute script line <idx> (1-based) / 执行第 idx 行脚本
	  
	  # 12 IR operation shortcuts:
	  encode <text>       Encode/create memory (Encode) / 编码或创建记忆
	  retrieve <query>    Retrieve memory (Retrieve) / 检索记忆
	  label <id> <tags>   Add tags to record (Label) / 给记录添加标签
	  update <id> <text>  Update record content (Update) / 更新记录内容
	  delete <id>         Delete record (Delete) / 删除记录
	  promote <id>        Promote record (Promote) / 提升记录优先级
	  demote <id>         Demote record (Demote) / 降低记录优先级
	  lock <id>           Lock record (Lock) / 锁定记录
	  merge <ids>         Merge multiple records, e.g. merge 2,3 into 1 / 合并多个记录
	  split <id>          Split record (Split) / 拆分记录
	  expire <id> <ttl>   Set record expiration (Expire) / 设置过期时间
	  summarize <ids>     Generate summary for multiple records (Summarize) / 生成摘要
	  
	  ir <json>           Execute raw IR JSON / 执行单条 IR JSON
	  switch-db <path>    Switch database (rebuild engine) / 切换数据库并重建引擎
	  db                  Show current database / 显示当前数据库
	  history             Show executed command history / 显示历史
	  save <path>         Save history to file / 保存历史
	  output brief|full   Switch output mode / 切换输出模式
	  quit / exit         Exit / 退出

	Also supports:
	  • Directly pasting IR JSON, IR lists, or workflows with steps
	  • Script files with JSON lines will be auto-recognized and executed
	"""
	parser = argparse.ArgumentParser(prog='manage.py session', add_help=False)
	parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
	parser.add_argument('--db', dest='db_path', default=None)
	parser.add_argument('--script', dest='script_path', default=None)
	parser.add_argument('--output', choices=['brief','full'], default='brief', help='Output mode (brief|full) / 输出模式')
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('Usage / 用法: python manage.py session [--mode mock|ollama|openai|auto] [--db path] [--script file]')
		sys.exit(2)

	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	db_path = args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
	echo(f"🧠 Model Service: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__} / 模型服务")
	echo(f"🗄️  Database: {db_path} / 数据库路径")
	output_mode = args.output  # 'brief' or 'full'

	# Load script file if provided
	script_lines: list[str] = []
	if args.script_path:
		sp = Path(args.script_path)
		if not sp.exists():
			echo(f"⚠️  Script file not found: {sp} / 脚本文件不存在")
		else:
			script_lines = [ln.rstrip('\n') for ln in sp.read_text(encoding='utf-8').splitlines()]
			echo(f"📄 Script loaded: {sp}, total {len(script_lines)} lines / 已加载脚本")
	script_ptr = 0  # next line index pointer
	history: list[str] = []

	def rebuild_engine(new_db: str):
		"""Rebuild engine when switching database."""
		nonlocal service, engine, db_path
		db_path = new_db
		service, engine = _build_engine_and_adapter(args.mode, db_path)
		echo(f"🔁 Database switched and engine rebuilt -> {db_path} / 已切换数据库并重建引擎")

	def exec_ir(ir: dict):
		"""Execute one IR object and show formatted output."""
		try:
			res = engine.execute(ir)
		except Exception as e:
			echo(f"❌ IR execution error: {e} / 执行异常")
			return
		if not getattr(res, 'success', False):
			echo(f"❌ Failed: {res.error} / 执行失败")
			if output_mode == 'full':
				try:
					echo(json.dumps({'error': getattr(res,'error',None)}, ensure_ascii=False))
				except Exception:
					pass
			return
		data = res.data or {}
		op = ir.get('op')

		if output_mode == 'full':
			# Print full JSON output
			try:
				echo(json.dumps({'op': op, 'success': True, 'data': data}, ensure_ascii=False))
			except Exception:
				echo(str(data))
			return
		
		# --- brief mode summary output ---
		if op == 'Encode':
			rid = data.get('inserted_id') or data.get('id')
			echo(f"✅ Encode | id={rid}, dim={data.get('embedding_dim')} / 编码成功")
			return
		if op == 'Retrieve':
			rows = data.get('rows') if isinstance(data, dict) else (data if isinstance(data, list) else [])
			echo(f"✅ Retrieve | {len(rows)} rows retrieved / 检索到 {len(rows)} 条记录")
			for idx, row in enumerate(rows[:3], 1):
				text_preview = (row.get('text') or '')[:60]
				echo(f"   [{idx}] id={row.get('id')} {text_preview}{'...' if len(text_preview)>=60 else ''}")
			return
		if op == 'Summarize':
			summary = str(data.get('summary',''))
			echo(f"✅ Summarize | {summary[:160]}{'…' if len(summary)>160 else ''} / 摘要生成")
			return
		affected = data.get('affected_rows') or data.get('updated_rows') or data.get('success_count')
		if affected is not None:
			echo(f"✅ {op} | affected={affected} / 受影响记录")
		else:
			echo(f"✅ {op} completed / 操作完成")

	def run_inline_workflow(payload: dict) -> bool:
		"""Execute inline workflow object containing multiple IR steps."""
		steps = payload.get('steps')
		if not isinstance(steps, list):
			return False
		name = payload.get('name') or payload.get('title') or 'workflow'
		echo(f"🧾 Executing inline workflow: {name} | {len(steps)} steps / 执行内联工作流")
		executed = False
		for idx, step in enumerate(steps, start=1):
			if not isinstance(step, dict):
				echo(f"⚠️  Skipping invalid step {idx}: type={type(step).__name__} / 无效步骤，已跳过")
				continue
			ir = step.get('ir') or step
			if not isinstance(ir, dict) or not ir.get('op'):
				echo(f"⚠️  Step {idx} missing valid IR, skipped / 缺少合法 IR，跳过")
				continue
			title = step.get('name') or ir.get('name') or f'step {idx}'
			echo(f"➡️  [{idx}/{len(steps)}] {title} -> {ir.get('op')} / 执行步骤")
			exec_ir(ir)
			executed = True
		return executed

	def execute_json_payload(obj: Any) -> bool:
		"""Handle execution of JSON payloads (IR object, list, or workflow)."""
		if isinstance(obj, dict):
			if obj.get('op'):
				exec_ir(obj)
				return True
			if run_inline_workflow(obj):
				return True
			echo('⚠️  JSON object missing executable content (op or steps) / 缺少可执行字段')
			return False
		if isinstance(obj, list):
			executed_any = False
			for idx, item in enumerate(obj, start=1):
				echo(f"📦 Processing list item {idx}/{len(obj)} / 处理列表元素")
				executed_any |= execute_json_payload(item)
			return executed_any
		echo('⚠️  Unsupported JSON type — expected object or list / 不支持的 JSON 类型')
		return False
	def run_script_line(idx: int):
		"""Run a specific line from the loaded script by index."""
		nonlocal script_ptr
		if idx < 1 or idx > len(script_lines):
			echo("⚠️  Line number out of range / 行号超出范围")
			return
		line = script_lines[idx-1].strip()
		script_ptr = idx  # set current pointer
		if not line or line.startswith('#'):
			echo(f"(Skipping blank/comment line {idx}) / 跳过空行或注释行 {idx}")
			return
		echo(f"▶️  [Script line {idx}] {line} / 执行脚本行")
		process_command(line)

	def process_command(line: str):
		"""Parse and execute a single session command line."""
		nonlocal script_ptr, output_mode
		line = line.strip()
		if not line:
			return
		# Try executing directly if line is JSON
		if line[0] in '{[':
			try:
				obj = json.loads(line)
			except Exception as e:
				echo(f"JSON parse error: {e} / JSON 解析失败")
				return
			history.append(line)
			if execute_json_payload(obj):
				return
			else:
				return
		history.append(line)
		parts = line.split(' ', 1)
		cmd = parts[0]
		arg = parts[1] if len(parts) > 1 else ''
		
		# === Built-in commands ===
		if cmd in ('quit', 'exit'):
			raise SystemExit(0)
		if cmd == 'help':
			echo("""Commands / 命令:
  Basics / 基础: help | list | next | n | run <i> | db | history | save <p> | output (brief|full) | quit
  12 IR operation shortcuts / 12种操作快捷方式:
    encode <text>           - Encode/create memory / 编码或创建记忆
    retrieve <query>        - Retrieve memory / 检索记忆
    label <id> <tags>       - Add tags (comma-separated) / 打标签（逗号分隔）
    update <id> <text>      - Update record text / 更新内容
    delete <id>             - Delete record / 删除记录
    promote <id>            - Promote priority / 提升优先级
    demote <id>             - Demote priority / 降低优先级
    lock <id>               - Lock record / 锁定记录
    merge <ids>             - Merge records (e.g. merge 2,3 into 1) / 合并记录
    split <id>              - Split record / 拆分记录
    expire <id> <ttl>       - Set expiration (e.g. P7D = 7 days) / 设置过期时间
    summarize <ids>         - Summarize multiple records / 生成摘要
  Advanced / 高级: ir <json> | switch-db <p> | (paste IR/workflow JSON)""")
		
		elif cmd == 'list':
			if not script_lines:
				echo('ℹ️  No script loaded / 未加载脚本'); 
				return
			for i, l in enumerate(script_lines, start=1):
				marker = '>>' if (i == script_ptr+1) else '  '
				echo(f"{marker} {i:03d}: {l}")
		elif cmd in ('next','n'):
			if not script_lines:
				echo('ℹ️  No script / 没有脚本'); 
				return
			if script_ptr >= len(script_lines):
				echo('⚠️  End of script reached / 已到脚本末尾'); 
				return
			run_script_line(script_ptr+1)
		elif cmd == 'run':
			if not arg.isdigit():
				echo('Usage / 用法: run <line_number>'); 
				return
			run_script_line(int(arg))
		
		# === IR operation shortcuts ===
		elif cmd == 'encode':
			if not arg:
				echo('Usage / 用法: encode <text>'); 
				return
			ir = {"stage":"ENC","op":"Encode","args":{"payload":{"text":arg}}}
			exec_ir(ir)
		elif cmd == 'retrieve':
			if not arg:
				echo('Usage / 用法: retrieve <query>'); 
				return
			ir = {"stage":"RET","op":"Retrieve","target":{"search":{"intent":{"query":arg},"overrides":{"k":5}}},"args":{}}
			exec_ir(ir)
		elif cmd == 'label':
			parts = arg.split(' ', 1)
			if len(parts) < 2:
				echo('Usage / 用法: label <id> <tags> (comma-separated)'); 
				return
			record_id, tags_str = parts
			tags = [t.strip() for t in tags_str.split(',')]
			ir = {"stage":"STO","op":"Label","target":{"ids":[record_id]},"args":{"tags":tags,"mode":"add"}}
			exec_ir(ir)
		elif cmd == 'update':
			parts = arg.split(' ', 1)
			if len(parts) < 2:
				echo('Usage / 用法: update <id> <new_text>'); 
				return
			record_id, new_text = parts
			ir = {"stage":"STO","op":"Update","target":{"ids":[record_id]},"args":{"set":{"text":new_text}}}
			exec_ir(ir)
		elif cmd == 'delete':
			if not arg:
				echo('Usage / 用法: delete <id>'); 
				return
			ir = {"stage":"STO","op":"Delete","target":{"ids":[arg]},"args":{"soft":True}}
			exec_ir(ir)
		elif cmd == 'promote':
			if not arg:
				echo('Usage / 用法: promote <id>'); 
				return
			ir = {"stage":"STO","op":"Promote","target":{"ids":[arg]},"args":{"weight_delta":0.2}}
			exec_ir(ir)
		elif cmd == 'demote':
			if not arg:
				echo('Usage / 用法: demote <id>'); 
				return
			ir = {"stage":"STO","op":"Demote","target":{"ids":[arg]},"args":{"archive":True}}
			exec_ir(ir)
		elif cmd == 'lock':
			if not arg:
				echo('Usage / 用法: lock <id>'); 
				return
			ir = {"stage":"STO","op":"Lock","target":{"ids":[arg]},"args":{"mode":"read_only"}}
			exec_ir(ir)
		elif cmd == 'merge':
			# Format: merge 2,3 into 1 (merge 2,3 into 1) or merge 2,3,4 (2 is primary)
			if not arg:
				echo('Usage / 用法: merge <child_ids> into <primary_id> or merge <primary_id>,<child_ids>'); 
				return
			if ' into ' in arg:
				parts = arg.split(' into ')
				child_ids_str = parts[0].strip()
				primary_id = parts[1].strip()
				child_ids = [i.strip() for i in child_ids_str.split(',')]
			else:
				ids_str = arg.split(',')
				if len(ids_str) < 2:
					echo('⚠️  At least two IDs required to merge / 需要至少两个ID进行合并'); 
					return
				primary_id = ids_str[0].strip()
				child_ids = [i.strip() for i in ids_str[1:]]
			ir = {"stage":"STO","op":"Merge","target":{"ids":child_ids},"args":{"strategy":"merge_into_primary","primary_id":primary_id}}
			exec_ir(ir)
		elif cmd == 'split':
			if not arg:
				echo('Usage / 用法: split <id>'); 
				return
			ir = {"stage":"STO","op":"Split","target":{"ids":[arg]},"args":{"strategy":"by_sentences","params":{"by_sentences":{"lang":"zh","max_sentences":3}}}}
			exec_ir(ir)
		elif cmd == 'expire':
			parts = arg.split(' ', 1)
			if len(parts) < 2:
				echo('Usage / 用法: expire <id> <ttl> (e.g. P7D means 7 days)'); 
				return
			record_id, ttl = parts
			ir = {"stage":"STO","op":"Expire","target":{"ids":[record_id]},"args":{"ttl":ttl,"on_expire":"soft_delete"}}
			exec_ir(ir)
		elif cmd == 'summarize':
			if not arg:
				echo('Usage / 用法: summarize <ids> [focus]'); 
				return
			parts = arg.split(' ', 1)
			ids_or_all = parts[0]
			focus = parts[1] if len(parts) > 1 else "Overall summary / 总体概述"
			if ids_or_all.lower() == 'all':
				ir = {"stage":"RET","op":"Summarize","target":{"all":True},"args":{"focus":focus,"max_tokens":256},"meta":{"confirmation":True}}
			else:
				ids = [i.strip() for i in ids_or_all.split(',')]
				ir = {"stage":"RET","op":"Summarize","target":{"ids":ids},"args":{"focus":focus,"max_tokens":256}}
			exec_ir(ir)
		
		# === Utility commands ===
		elif cmd == 'ir':
			try:
				ir = json.loads(arg)
			except Exception as e:
				echo(f"JSON parse error: {e} / JSON 解析失败"); 
				return
			exec_ir(ir)
		elif cmd == 'switch-db':
			if not arg:
				echo('Usage / 用法: switch-db <path>'); 
				return
			rebuild_engine(arg)
		elif cmd == 'db':
			echo(f"Current database: {db_path} / 当前数据库")
		elif cmd == 'history':
			for i, h in enumerate(history, start=1):
				echo(f"{i:03d}: {h}")
		elif cmd == 'save':
			if not arg:
				echo('Usage / 用法: save <path>'); 
				return
			try:
				Path(arg).write_text('\n'.join(history), encoding='utf-8')
				echo(f"✅ History saved -> {arg} / 已保存历史")
			except Exception as e:
				echo(f"❌ Save failed: {e} / 保存失败")
		elif cmd == 'output':
			if arg not in ('brief','full'):
				echo('Usage / 用法: output brief|full'); 
				return
			output_mode = arg
			echo(f"🔧 Output mode switched to: {output_mode} / 输出模式已切换")
		else:
			echo('Unknown command, type help for list / 未知命令，请输入 help')

	echo("Entering session mode, type help for commands, Ctrl+C to exit / 进入会话模式，Ctrl+C 退出。")
	while True:
		try:
			line = input('session> ')
		except (EOFError, KeyboardInterrupt):
			echo('')
			break
		try:
			process_command(line)
		except SystemExit:
			break
		except Exception as e:
			echo(f"❌ Error while processing command: {e} / 处理命令时出错")
	echo('👋 Exiting session / 退出会话')
	return 0
def cmd_models_smoke():
	"""Minimal model smoke test — perform one embedding and one generation call.
	最小化模型冒烟测试：做一次 embedding + 一次 generation。

	Usage / 用法:
	  python manage.py models-smoke            # use .env / MODEL_SERVICE
	  python manage.py models-smoke openai     # force OpenAI
	  python manage.py models-smoke ollama     # force Ollama
	  python manage.py models-smoke mock       # mock mode
	"""
	mode = None
	if len(sys.argv) >= 3:
		mode = sys.argv[2].lower()

	echo("=" * 60)
	echo("🧪 Model Smoke Test / 模型冒烟测试")
	echo("=" * 60)
	
	try:
		service = _build_models_service_from_env(mode)
		from text2mem.services.models_service import GenerationResult
		echo(f"🔧 Using models / 使用模型:")
		echo(f"   Embedding: {service.embedding_model.__class__.__name__}")
		echo(f"   Generation: {service.generation_model.__class__.__name__}")
		echo("")

		# 1️⃣ Test embedding
		echo("📍 Test 1/2: Embedding model / 测试嵌入模型...")
		text = "用于嵌入的测试文本。Hello embeddings!"
		emb = service.encode_memory(text)
		echo(f"✅ Embedding succeeded / 嵌入成功")
		echo(f"   Dimension: {emb.dimension} | Model: {emb.model}")
		echo("")

		# 2️⃣ Test generation
		echo("📍 Test 2/2: Generation model / 测试生成模型...")
		prompt = "请用一句话总结：Text2Mem 是一个文本记忆处理系统。"
		gen = service.generation_model.generate(prompt, temperature=0.2, max_tokens=60)
		echo(f"✅ Generation succeeded / 生成成功")
		echo(f"   Model: {gen.model}")
		echo(f"   Output / 输出: {gen.text[:150]}{'...' if len(gen.text) > 150 else ''}")
		echo("")
		
		echo("=" * 60)
		echo("🎉 All tests passed! / 所有测试通过！")
		echo("=" * 60)
	except Exception as e:
		echo("")
		echo("=" * 60)
		echo("❌ Model smoke test failed / 模型冒烟测试失败")
		echo("=" * 60)
		echo(f"Error / 错误: {e}")
		echo("")
		echo("💡 Troubleshooting / 故障排查:")
		echo("   1. Check .env config: python manage.py status / 检查 .env 配置")
		echo("   2. Verify model config: python manage.py models-info / 验证模型配置")
		echo("   3. For Ollama: ensure 'ollama serve' is running / Ollama 请确保服务已启动")
		echo("   4. For OpenAI: verify API key / OpenAI 请检查 API Key")
		sys.exit(1)
	sys.exit(0)


def cmd_run_workflow():
	"""Run a workflow JSON file — executes IR steps in order.
	运行一个工作流 JSON 文件，按顺序执行每个 IR 步骤。

	Usage / 用法:
	  python manage.py workflow <workflow.json> [--mode mock|ollama|openai|auto] [--db <db_path>] [--verbose]
	"""
	import argparse, json
	from text2mem.core.engine import Text2MemEngine
	from text2mem.adapters.sqlite_adapter import SQLiteAdapter

	parser = argparse.ArgumentParser(prog="manage.py workflow", add_help=False)
	parser.add_argument("workflow", help="Path to workflow JSON / 工作流 JSON 文件路径")
	parser.add_argument("--mode", choices=["mock","ollama","openai","auto"], default=None)
	parser.add_argument("--db", dest="db_path", default=None, help="Database path (default: TEXT2MEM_DB_PATH or ./text2mem.db)")
	parser.add_argument("--verbose", action="store_true", help="Verbose output / 详细输出")
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo("Usage / 用法: python manage.py workflow <workflow.json> [--mode mock|ollama|openai|auto] [--db path] [--verbose]")
		sys.exit(2)

	wf_path = Path(args.workflow)
	if not wf_path.exists():
		echo(f"❌ Workflow file not found: {wf_path} / 工作流文件不存在")
		sys.exit(2)

	db_path = args.db_path or os.environ.get("TEXT2MEM_DB_PATH") or "./text2mem.db"
	service = _build_models_service_from_env(args.mode)
	adapter = SQLiteAdapter(db_path, models_service=service)
	engine = Text2MemEngine(adapter=adapter, models_service=service)

	data = json.loads(wf_path.read_text(encoding="utf-8"))
	workflow_name = data.get("name") or data.get("title") or wf_path.name
	steps = data.get("steps", [])
	
	echo("=" * 60)
	echo(f"🚀 Running Workflow: {workflow_name} / 运行工作流")
	echo("=" * 60)
	echo(f"📄 File: {wf_path}")
	echo(f"📦 Steps: {len(steps)}")
	echo(f"🧠 Models: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	echo(f"🗄️  Database: {db_path}")
	echo("=" * 60)
	echo("")

	success_count = 0
	failed_count = 0
	
	for idx, step in enumerate(steps, start=1):
		title = step.get("name") or step.get("description") or f"Step {step.get('step', idx)}"
		ir = step.get("ir") or step
		if not isinstance(ir, dict) or not ir.get("op"):
			echo(f"⚠️  [{idx}/{len(steps)}] Skipping invalid step: {title} / 无效步骤，已跳过")
			continue
		
		echo(f"➡️  [{idx}/{len(steps)}] {title}")
		echo(f"    Operation: {ir.get('op')} | Stage: {ir.get('stage', 'N/A')} / 操作信息")

		try:
			result = engine.execute(ir)
		except Exception as e:
			echo(f"❌ Exception: {e} / 执行异常")
			if args.verbose:
				import traceback
				traceback.print_exc()
			failed_count += 1
			continue

		if not getattr(result, "success", False):
			echo(f"❌ Step failed: {result.error} / 步骤失败")
			failed_count += 1
			continue

		data_out = result.data or {}
		op = ir.get("op")
		
		if op == "Encode":
			rid = data_out.get("inserted_id") or data_out.get("id")
			emb_dim = data_out.get("embedding_dim")
			echo(f"    ✅ Encoded | ID={rid}, dim={emb_dim} / 编码成功")
		elif op == "Retrieve":
			rows = []
			if isinstance(data_out, list):
				rows = data_out
			elif isinstance(data_out, dict):
				rows = data_out.get("rows", []) or []
			echo(f"    ✅ Retrieved {len(rows)} records / 检索到 {len(rows)} 条记录")
			if args.verbose and rows:
				echo(f"       Example / 示例: {str(rows[0])[:120]}...")
		elif op == "Summarize":
			summary = str(data_out.get("summary", ""))
			echo(f"    ✅ Summary: {summary[:120]}{'...' if len(summary) > 120 else ''} / 摘要生成")
		else:
			affected = data_out.get("affected_rows") or data_out.get("updated_rows")
			if affected is not None:
				echo(f"    ✅ Done | affected={affected} / 完成，受影响记录: {affected}")
			else:
				echo(f"    ✅ Done / 完成")
		
		success_count += 1
		echo("")

	echo("=" * 60)
	echo(f"🎉 Workflow Completed / 工作流完成")
	echo("=" * 60)
	echo(f"✅ Success: {success_count}/{len(steps)}")
	if failed_count > 0:
		echo(f"❌ Failed: {failed_count}/{len(steps)}")
	echo("=" * 60)
	
	sys.exit(0 if failed_count == 0 else 1)


def cmd_set_env():
	"""Set or update environment variables in .env file.
	设置或更新 .env 文件中的环境变量。
	"""
	if len(sys.argv) < 4:
		echo("Usage / 用法: manage.py set-env KEY VALUE")
		echo("Example / 示例: manage.py set-env TEXT2MEM_LOG_LEVEL DEBUG")
		return 1
	
	key = sys.argv[2]
	value = sys.argv[3]
	env_path = ROOT / ".env"
	
	# Read existing .env variables
	existing_vars = {}
	if env_path.exists():
		existing_vars = load_env_file(env_path)
	
	existing_vars[key] = value  # update or add

	env_content = "# Text2Mem Environment Configuration / 环境配置\n"
	provider = existing_vars.get("MODEL_SERVICE", "未指定 / unspecified")
	env_content += f"# Provider: {provider}\n\n"

	sections = {
		"Database Settings / 数据库设置": ["DATABASE_PATH", "TEXT2MEM_DB_PATH", "TEXT2MEM_DB_WAL", "TEXT2MEM_DB_TIMEOUT"],
		"Embedding Model / 嵌入模型设置": ["TEXT2MEM_EMBEDDING_PROVIDER", "TEXT2MEM_EMBEDDING_MODEL", "TEXT2MEM_EMBEDDING_BASE_URL"],
		"Generation Model / 生成模型设置": ["TEXT2MEM_GENERATION_PROVIDER", "TEXT2MEM_GENERATION_MODEL", "TEXT2MEM_GENERATION_BASE_URL",
					"TEXT2MEM_TEMPERATURE", "TEXT2MEM_MAX_TOKENS", "TEXT2MEM_TOP_P"],
		"OpenAI Settings / OpenAI 设置": ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_API_BASE", "OPENAI_ORGANIZATION"],
		"Ollama Settings / Ollama 设置": ["OLLAMA_BASE_URL", "OLLAMA_MODEL"],
		"Other / 其他设置": ["MODEL_SERVICE", "TEXT2MEM_LOG_LEVEL"]
	}
	
	key_section = "Other / 其他设置"
	for section, keys in sections.items():
		if key in keys:
			key_section = section
			break
	
	processed_keys = set()
	for section, keys in sections.items():
		section_keys = [k for k in keys if k in existing_vars]
		if section_keys:
			env_content += f"\n# {section}\n"
			for k in section_keys:
				env_content += f"{k}={existing_vars[k]}\n"
				processed_keys.add(k)
	
	unprocessed_keys = [k for k in existing_vars if k not in processed_keys]
	if unprocessed_keys:
		env_content += "\n# Custom / 自定义设置\n"
		for k in unprocessed_keys:
			env_content += f"{k}={existing_vars[k]}\n"
	
	env_path.write_text(env_content, encoding="utf-8")
	echo(f"✅ Environment variable set: {key}={value} / 已写入 .env 文件")
	return 0


def _normalize_docstring(text: Optional[str]) -> str:
    if not text:
        return ""
    return textwrap.dedent(text.expandtabs()).strip()


COMMAND_DEFINITIONS: Tuple[CommandInfo, ...] = (
    CommandInfo("status", cmd_status, "Environment status (dependencies / .env / service detection) | 环境状态（依赖 / .env / 服务探测）", "core"),
    CommandInfo("config", cmd_config, "Generate or update .env (--provider ...) | 生成或更新 .env (--provider ...)", "core"),
    CommandInfo("set-env", cmd_set_env, "Quickly write a single environment variable | 快速写入单个环境变量", "core", aliases=("set_env",)),
    CommandInfo("models-info", cmd_models_info, "Show parsed model configuration | 显示解析后的模型配置", "core"),
    CommandInfo("demo", cmd_run_demo, "Execute preset IR or workflow demos in batch | 批量执行预置 IR / 工作流示例", "demos"),
    CommandInfo("ir", cmd_ir, "Execute a single IR JSON (--file | --inline) | 执行单条 IR JSON (--file | --inline)", "demos"),
    CommandInfo("workflow", cmd_run_workflow, "Run a workflow file step-by-step | 按步骤顺序运行工作流文件", "workflows"),
    CommandInfo("list-workflows", cmd_list_workflows, "List example workflow JSON files | 列出示例工作流 JSON 文件", "workflows", aliases=("list_workflows",)),
    CommandInfo("session", cmd_session, "Enhanced persistent session (supports 12 shortcut operations) | 增强型持久会话（支持12种操作快捷方式）", "interaction"),
    CommandInfo("models-smoke", cmd_models_smoke, "Minimal model smoke test (embed + generate) | 最小模型冒烟测试（嵌入 + 生成）", "models", aliases=("models_smoke",)),
    CommandInfo("setup-ollama", cmd_setup_ollama, "Pull default Ollama models | 拉取默认的 Ollama 模型", "ops"),
    CommandInfo("setup-openai", cmd_setup_openai, "Generate .env for OpenAI usage | 生成 OpenAI 使用的 .env 文件", "ops"),
    CommandInfo("test", cmd_test, "Run pytest or minimal smoke test | 运行 pytest 或最小冒烟测试", "ops"),
)

COMMAND_LOOKUP: Dict[str, CommandInfo] = {}
for info in COMMAND_DEFINITIONS:
    COMMAND_LOOKUP[info.name] = info
    for alias in info.aliases:
        COMMAND_LOOKUP[alias] = info


def _command_names(info: CommandInfo) -> str:
    names = [info.name, *info.aliases]
    return ", ".join(names)


def print_usage() -> None:
    echo("Usage 用法: python manage.py <command> [options]")
    echo("")
    for key, label in COMMAND_GROUPS:
        group_items = [info for info in COMMAND_DEFINITIONS if info.group == key]
        if not group_items:
            continue
        echo(f"[{label}]")
        for info in group_items:
            names = _command_names(info)
            echo(f"  {names:<28} {info.summary}")
        echo("")
    echo("Use 'python manage.py help <command>' for detailed instructions.")
    echo("使用 'python manage.py help <command>' 查看详细说明。")
    echo("")
    echo("Examples 示例:")
    echo("  python manage.py demo --mode mock")
    echo("  python manage.py ir --mode mock --inline '{\"stage\":\"RET\",\"op\":...}'")
    echo("  python manage.py session --mode mock --output full")


def print_command_help(name: str) -> int:
    info = COMMAND_LOOKUP.get(name)
    if not info:
        echo(f"Unknown command: {name} | 未知命令: {name}")
        echo("Use 'python manage.py help' to see available commands.")
        echo("使用 'python manage.py help' 查看可用命令。")
        return 1
    label = next((lbl for key, lbl in COMMAND_GROUPS if key == info.group), info.group)
    echo(f"Command 命令: {_command_names(info)}")
    echo(f"Group 分组: {label}")
    echo(f"Summary 概要: {info.summary}")
    details = _normalize_docstring(info.description or info.handler.__doc__)
    if details:
        echo("")
        for line in details.splitlines():
            echo(line)
    return 0


def main():
    if len(sys.argv) < 2:
        print_usage()
        return 1

    cmd = sys.argv[1]
    if cmd in ("help", "-h", "--help"):
        target = sys.argv[2] if len(sys.argv) > 2 else None
        if not target:
            print_usage()
            return 0
        return print_command_help(target)

    info = COMMAND_LOOKUP.get(cmd)
    if not info:
        echo(f"Unknown command: {cmd} | 未知命令: {cmd}")
        echo("Use 'python manage.py help' to view available commands.")
        echo("使用 'python manage.py help' 查看命令列表。")
        return 2

    result = info.handler()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())

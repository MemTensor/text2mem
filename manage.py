#!/usr/bin/env python3
"""
Text2Mem 项目管理工具

提供统一的环境配置、演示、测试和交互功能入口。

快速开始:
  python manage.py status              # 查看环境状态
  python manage.py config --provider ollama  # 配置环境
  python manage.py demo                # 运行演示
  python manage.py session             # 进入交互模式

详细帮助:
  python manage.py help [command]      # 查看命令帮助
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

# 导入核心工具
from scripts.cli_core import (
    echo, load_env_file, ENV_PATH as CORE_ENV_PATH,
    build_models_service_from_env as _build_models_service_from_env,
    build_engine_and_adapter as _build_engine_and_adapter,
)
from scripts.config_helpers import generate_grouped_env
from scripts.env_utils import which

ROOT = Path(__file__).parent
ENV_PATH = CORE_ENV_PATH

# 在启动时加载环境变量
ENV_VARS = load_env_file(ENV_PATH) if ENV_PATH.exists() else {}


@dataclass(frozen=True)
class CommandInfo:
    name: str
    handler: Callable[[], Optional[int]]
    summary: str
    group: str
    aliases: Tuple[str, ...] = ()
    description: Optional[str] = None

    def matches(self, candidate: str) -> bool:
        return candidate == self.name or candidate in self.aliases


COMMAND_GROUPS: Tuple[Tuple[str, str], ...] = (
    ("core", "🔧 核心配置"),
    ("demos", "🎯 功能演示"),
    ("workflows", "📋 工作流执行"),
    ("interaction", "💬 交互模式"),
    ("models", "🤖 模型管理"),
    ("ops", "⚙️  运维工具"),
)


# ============================================================================
# 环境配置命令
# ============================================================================


# ============================================================================
# 环境配置命令
# ============================================================================

def cmd_status():
    """显示环境与依赖状态"""
    from text2mem.core.config import ModelConfig
    
    env_exists = ENV_PATH.exists()
    cfg = ModelConfig.from_env()
    db_path = os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
    
    echo("=" * 60)
    echo("📊 Text2Mem 环境状态")
    echo("=" * 60)
    
    echo("\n[环境文件]")
    if env_exists:
        echo(f"  ✅ .env 已配置 -> {ENV_PATH}")
    else:
        echo(f"  ⚠️  .env 未找到 -> {ENV_PATH}")
        echo(f"  💡 运行: python manage.py config --provider ollama")
    
    echo("\n[模型配置]")
    echo(f"  Provider: {cfg.provider}")
    echo(f"  嵌入模型: {cfg.embedding_provider}:{cfg.embedding_model}")
    echo(f"  生成模型: {cfg.generation_provider}:{cfg.generation_model}")
    
    if cfg.embedding_provider == 'ollama' or cfg.generation_provider == 'ollama':
        ollama_url = os.environ.get('TEXT2MEM_OLLAMA_BASE_URL') or \
                     os.environ.get('OLLAMA_BASE_URL') or \
                     cfg.ollama_base_url
        echo(f"  Ollama URL: {ollama_url}")
    
    if 'openai' in (cfg.provider, cfg.embedding_provider, cfg.generation_provider):
        api_key_set = bool(os.environ.get('OPENAI_API_KEY'))
        echo(f"  OpenAI API Key: {'✅ 已设置' if api_key_set else '❌ 未设置'}")
    
    echo("\n[数据库]")
    db_exists = Path(db_path).exists()
    echo(f"  路径: {db_path}")
    echo(f"  状态: {'✅ 存在' if db_exists else '⚠️  未创建（首次使用时自动创建）'}")
    
    echo("\n[依赖工具]")
    echo(f"  ollama: {'✅ 可用' if which('ollama') else '❌ 未安装'}")
    echo(f"  pytest: {'✅ 可用' if which('pytest') else '⚠️  未安装'}")
    
    echo("")
    return 0

def cmd_config():
	"""生成/更新 .env 文件。"""
	parser = argparse.ArgumentParser(prog='manage.py config', add_help=False)
	parser.add_argument('--provider', choices=['mock','ollama','openai'], required=True)
	parser.add_argument('--openai-key', default=None)
	parser.add_argument('--ollama-base-url', default='http://localhost:11434')
	parser.add_argument('--embed-model', default=None)
	parser.add_argument('--gen-model', default=None)
	parser.add_argument('--db-path', default='./text2mem.db', help='数据库路径')
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: manage.py config --provider [mock|ollama|openai] [--openai-key ...] [--db-path ...]')
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
	echo(f"✅ 已写入 .env -> {ENV_PATH}")
	echo(f"💡 提示: 运行 'python manage.py status' 验证配置")
	return 0

def cmd_setup_ollama():
	"""拉取常用 Ollama 模型。"""
	exe = which('ollama')
	if not exe:
		echo('❌ 未找到 ollama 可执行文件，请先安装 https://ollama.ai')
		echo('💡 安装指南: https://github.com/ollama/ollama#readme')
		return 1
	
	from text2mem.core.config import ModelConfig
	cfg = ModelConfig.for_ollama()
	emb = os.environ.get('TEXT2MEM_EMBEDDING_MODEL') or cfg.embedding_model
	gen = os.environ.get('TEXT2MEM_GENERATION_MODEL') or cfg.generation_model
	
	echo("🚀 开始拉取 Ollama 模型...")
	echo(f"⬇️  嵌入模型: {emb}")
	try:
		subprocess.run([exe, 'pull', emb], check=True)
		echo(f"✅ {emb} 下载完成")
	except Exception as e:
		echo(f"❌ 拉取 {emb} 失败: {e}")
		return 1
	
	echo(f"⬇️  生成模型: {gen}")
	try:
		subprocess.run([exe, 'pull', gen], check=True)
		echo(f"✅ {gen} 下载完成")
	except Exception as e:
		echo(f"❌ 拉取 {gen} 失败: {e}")
		return 1
	
	echo('🎉 所有模型下载完成！')
	echo('💡 运行 python manage.py models-smoke 测试模型')
	return 0

def cmd_setup_openai():
	"""初始化 OpenAI 配置到 .env。"""
	parser = argparse.ArgumentParser(prog='manage.py setup-openai', add_help=False)
	parser.add_argument('--api-key', dest='api_key', default=None)
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: manage.py setup-openai [--api-key sk-...]'); return 2
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
	echo(f"✅ 已更新 .env -> {ENV_PATH}")
	return 0

def cmd_test():
	"""运行测试（优先 pytest，否则做最小冒烟）。"""
	parser = argparse.ArgumentParser(prog='manage.py test', add_help=False)
	parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
	parser.add_argument('-k', '--keyword', default=None, help='仅运行匹配的测试')
	parser.add_argument('--smoke', action='store_true', help='仅运行冒烟测试')
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		args = argparse.Namespace(verbose=False, keyword=None, smoke=False)
	
	if args.smoke:
		echo('🧪 运行最小冒烟测试...')
		try:
			service = _build_models_service_from_env(None)
			emb = service.encode_memory('hello embeddings')
			echo(f"✅ Embedding ok, dim={emb.dimension}, model={emb.model}")
			gen = service.generation_model.generate('一句话总结：Text2Mem 是什么？')
			echo(f"✅ Generation ok, model={gen.model}")
			echo(f"📝 输出: {gen.text[:100]}...")
			return 0
		except Exception as e:
			echo(f"❌ 冒烟失败: {e}")
			return 1
	
	try:
		cmd = [sys.executable, '-m', 'pytest']
		if args.verbose:
			cmd.append('-v')
		else:
			cmd.append('-q')
		if args.keyword:
			cmd.extend(['-k', args.keyword])
		
		echo(f"🧪 运行测试: {' '.join(cmd)}")
		r = subprocess.run(cmd, cwd=str(ROOT))
		return r.returncode
	except Exception as e:
		echo(f'⚠️ 无法运行 pytest: {e}')
		echo('💡 安装 pytest: pip install pytest')
		return 1

def cmd_models_info():
	"""显示当前模型解析配置。"""
	from text2mem.core.config import ModelConfig
	cfg = ModelConfig.from_env()
	
	echo("=" * 60)
	echo("🤖 模型配置详情")
	echo("=" * 60)
	echo(f"\n[总体配置]")
	echo(f"  Provider: {cfg.provider}")
	
	echo(f"\n[嵌入模型]")
	echo(f"  Provider: {cfg.embedding_provider}")
	echo(f"  Model: {cfg.embedding_model}")
	
	echo(f"\n[生成模型]")
	echo(f"  Provider: {cfg.generation_provider}")
	echo(f"  Model: {cfg.generation_model}")
	
	if cfg.embedding_provider == 'ollama' or cfg.generation_provider == 'ollama':
		echo(f"\n[Ollama 配置]")
		echo(f"  Base URL: {cfg.ollama_base_url}")
	
	if cfg.embedding_provider == 'openai' or cfg.generation_provider == 'openai':
		echo(f"\n[OpenAI 配置]")
		api_key = os.environ.get('OPENAI_API_KEY', '')
		echo(f"  API Key: {'✅ 已设置 (' + api_key[:8] + '...)' if api_key else '❌ 未设置'}")
		if os.environ.get('OPENAI_API_BASE'):
			echo(f"  API Base: {os.environ.get('OPENAI_API_BASE')}")
	
	echo("")
	return 0



def cmd_ir():
	"""执行单条 IR JSON。"""
	parser = argparse.ArgumentParser(prog='manage.py ir', add_help=False)
	parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('--file', dest='file_path')
	group.add_argument('--inline', dest='inline_json')
	parser.add_argument('--db', dest='db_path', default=None)
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo("用法: manage.py ir [--mode mock|ollama|openai|auto] (--file path.json | --inline '{...}') [--db path]"); return 2

	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	if args.file_path:
		ir = json.loads(Path(args.file_path).read_text(encoding='utf-8'))
	else:
		ir = json.loads(args.inline_json)
	res = engine.execute(ir)
	if not getattr(res, 'success', False):
		echo(f"❌ 执行失败: {res.error}"); return 1
	data = res.data or {}
	try:
		preview = json.dumps(data, ensure_ascii=False)[:400]
	except Exception:
		preview = str(data)[:400]
	echo(f"✅ 执行成功 | {preview}{'…' if len(preview)>=400 else ''}")
	return 0


def cmd_run_demo():
	"""运行演示：批量执行预置流程或单条 IR 示例。
	用法: python manage.py demo [--mode mock|ollama|openai|auto] [--db path] [--set workflows|individual|scenarios]
	- workflows: 依次运行 examples/op_workflows 下的多步骤操作工作流
	- individual: 逐个执行 examples/ir_operations 下的单条 IR 示例
	- scenarios: 依次运行 examples/real_world_scenarios 下的现实情境工作流
	"""
	parser = argparse.ArgumentParser(prog='manage.py demo', add_help=False)
	parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
	parser.add_argument('--db', dest='db_path', default=None)
	parser.add_argument('--set', choices=['workflows','individual','scenarios'], default='workflows')
	parser.add_argument('--verbose', action='store_true', help='详细输出')
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: python manage.py demo [--mode mock|ollama|openai|auto] [--db path] [--set workflows|individual|scenarios] [--verbose]')
		return 2

	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	db_path_display = args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
	
	echo("=" * 60)
	echo("🎯 Text2Mem 演示模式")
	echo("=" * 60)
	echo(f"🧠 模型服务: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	echo(f"🗄️  数据库: {db_path_display}")
	echo(f"📦 演示集: {args.set}")
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
				echo(f"   📄 完整输出: {_json.dumps(out, ensure_ascii=False)[:300]}...")
			except Exception:
				pass
		
		if op == 'Encode':
			rid = None
			if isinstance(out, dict):
				rid = out.get('inserted_id') or out.get('id')
			echo(f"   ✅ Encode | id={rid} dim={out.get('embedding_dim') if isinstance(out, dict) else 'n/a'}")
		elif op == 'Retrieve':
			if isinstance(out, list):
				rows = out
			elif isinstance(out, dict):
				rows = out.get('rows') or out.get('matches') or []
			else:
				rows = []
			echo(f"   ✅ Retrieve | 检索到 {len(rows)} 条记录")
			if verbose and rows:
				for idx, row in enumerate(rows[:2], 1):
					echo(f"      [{idx}] {str(row)[:80]}...")
		elif op == 'Summarize':
			summary = ''
			if isinstance(out, dict):
				summary = str(out.get('summary',''))
			echo(f"   ✅ Summarize | {summary[:100]}{'…' if len(summary)>100 else ''}")
		else:
			affected = None
			if isinstance(out, dict):
				affected = out.get('affected_rows') or out.get('updated_rows') or out.get('success_count')
			if affected is not None:
				echo(f"   ✅ {op} | 受影响行数: {affected}")
			else:
				echo(f"   ✅ {op} | 完成")

	ran = 0
	failed = 0
	
	if args.set == 'individual':
		ir_dir = ROOT / 'examples' / 'ir_operations'
		if not ir_dir.exists():
			echo(f'ℹ️  目录不存在: {ir_dir}')
			return 0
		files = sorted(ir_dir.glob('*.json'))
		if not files:
			echo('ℹ️  未找到 examples/ir_operations 下的示例。')
			return 0
		for path in files:
			ir = _json.loads(path.read_text(encoding='utf-8'))
			echo(f"🚀 执行 {path.name} -> {ir.get('op')} ({ir.get('stage')})")
			try:
				res = engine.execute(ir)
			except Exception as e:
				echo(f"❌ 执行异常: {e}")
				failed += 1
				continue
			if not getattr(res, 'success', False):
				echo(f"❌ 失败: {res.error}")
				failed += 1
				continue
			out = res.data or {}
			_echo_ir_result(ir, out, args.verbose)
			ran += 1
		echo(f"\n{'='*60}")
		echo(f"🎉 Demo 完成 | 成功: {ran} | 失败: {failed}")
		return 0 if failed == 0 else 1

	if args.set == 'scenarios':
		wf_dir = ROOT / 'examples' / 'real_world_scenarios'
		if not wf_dir.exists():
			echo(f'ℹ️  目录不存在: {wf_dir}')
			return 0
		files = sorted(wf_dir.glob('*.json'))
		if not files:
			echo('ℹ️  未找到 examples/real_world_scenarios 下的工作流。')
			return 0
		for path in files:
			data = _json.loads(path.read_text(encoding='utf-8'))
			steps = data.get('steps', [])
			echo(f"🚀 运行场景: {path.name} | {len(steps)} 步骤")
			for i, step in enumerate(steps, start=1):
				ir = step.get('ir') or step
				title = step.get('name') or step.get('description') or f'step {i}'
				echo(f"➡️  [{i}/{len(steps)}] {title} -> {ir.get('op')}")
				try:
					res = engine.execute(ir)
				except Exception as e:
					echo(f"❌ 执行异常: {e}")
					failed += 1
					continue
				if not getattr(res, 'success', False):
					echo(f"❌ 失败: {res.error}")
					failed += 1
					continue
				out = res.data or {}
				_echo_ir_result(ir, out, args.verbose)
				ran += 1
		echo(f"\n{'='*60}")
		echo(f"🎉 Demo 完成 | 成功: {ran} | 失败: {failed}")
		return 0 if failed == 0 else 1

	# workflows: run curated op workflows
	wf_dir = ROOT / 'examples' / 'op_workflows'
	if not wf_dir.exists():
		echo(f'ℹ️  目录不存在: {wf_dir}')
		return 0
	
	files = [
		'op_encode.json',
		'op_label.json',
		'op_label_search.json',
		'op_label_via_search.json',
		'op_promote.json',
		'op_promote_search.json',
		'op_promote_remind.json',
		'op_demote.json',
		'op_update.json',
		'op_delete_search.json',
		'op_update_via_search.json',
		'op_delete.json',
		'op_lock.json',
		'op_expire.json',
		'op_split.json',
		'op_split_custom.json',
		'op_merge.json',
		'op_retrieve.json',
		'op_summarize.json',
	]
	for name in files:
		path = wf_dir / name
		if not path.exists():
			continue
		data = _json.loads(path.read_text(encoding='utf-8'))
		steps = data.get('steps', [])
		echo(f"🚀 运行工作流: {name} | {len(steps)} 步骤")
		for i, step in enumerate(steps, start=1):
			ir = step.get('ir') or step
			title = step.get('name') or f'step {i}'
			echo(f"➡️  [{i}/{len(steps)}] {title} -> {ir.get('op')}")
			try:
				res = engine.execute(ir)
			except Exception as e:
				echo(f"❌ 执行异常: {e}")
				failed += 1
				continue
			if not getattr(res, 'success', False):
				echo(f"❌ 失败: {res.error}")
				failed += 1
				continue
			out = res.data or {}
			_echo_ir_result(ir, out, args.verbose)
			ran += 1
	echo(f"\n{'='*60}")
	echo(f"🎉 Demo 完成 | 成功: {ran} | 失败: {failed}")
	return 0 if failed == 0 else 1


def cmd_list_workflows():
	"""列出内置工作流文件。"""
	candidates = [ROOT/"examples"/"real_world_scenarios", ROOT/"examples"/"op_workflows", ROOT/"text2mem"/"examples"]
	files = []
	for d in candidates:
		if d.exists():
			files += [p for p in d.glob("*.json")]
	if not files:
		echo("ℹ️ 未找到任何工作流文件"); return 0
	echo("📚 工作流文件：")
	for p in sorted(files):
		echo(f"  - {p.relative_to(ROOT)}")
	return 0





def cmd_session():
	"""持久化会话模式：可指定数据库/模式，加载脚本并逐条执行或交互输入。
	用法: python manage.py session [--mode mock|ollama|openai|auto] [--db path] [--script file]

	可用指令:
	  help                显示帮助
	  list                列出脚本行
	  next / n            执行下一行脚本
	  run <idx>           执行脚本第 idx 行 (从 1 开始)
	  
	  # 12种IR操作的快捷方式:
	  encode <text>       编码/创建记忆 (Encode)
	  retrieve <query>    检索记忆 (Retrieve)
	  label <id> <tags>   给记录打标签 (Label)
	  update <id> <text>  更新记录内容 (Update)
	  delete <id>         删除记录 (Delete)
	  promote <id>        提升记录优先级 (Promote)
	  demote <id>         降低记录优先级 (Demote)
	  lock <id>           锁定记录 (Lock)
	  merge <ids>         合并多个记录，格式: merge 2,3 into 1 (Merge)
	  split <id>          拆分记录 (Split)
	  expire <id> <ttl>   设置记录过期时间 (Expire)
	  summarize <ids>     生成多条记录的摘要 (Summarize)
	  
	  ir <json>           执行单条 IR JSON
	  switch-db <path>    切换数据库 (重建引擎)
	  db                  显示当前数据库
	  history             显示已执行指令历史
	  save <path>         保存历史到文件
	  output brief|full   切换输出模式
	  quit/exit           退出
	  
	额外支持：
	  • 直接粘贴单条 IR JSON、IR 列表或包含 steps 的工作流 JSON
	  • 脚本文件中的 JSON 行会被自动识别并执行
	"""
	parser = argparse.ArgumentParser(prog='manage.py session', add_help=False)
	parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
	parser.add_argument('--db', dest='db_path', default=None)
	parser.add_argument('--script', dest='script_path', default=None)
	parser.add_argument('--output', choices=['brief','full'], default='brief', help='输出模式 (brief|full)')
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: python manage.py session [--mode mock|ollama|openai|auto] [--db path] [--script file]'); sys.exit(2)

	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	db_path = args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
	echo(f"🧠 模型服务: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	echo(f"🗄️  数据库: {db_path}")
	output_mode = args.output  # 'brief' or 'full'

	script_lines: list[str] = []
	if args.script_path:
		sp = Path(args.script_path)
		if not sp.exists():
			echo(f"⚠️ 脚本文件不存在: {sp}")
		else:
			script_lines = [ln.rstrip('\n') for ln in sp.read_text(encoding='utf-8').splitlines()]
			echo(f"📄 已加载脚本 {sp} 共 {len(script_lines)} 行")
	script_ptr = 0  # next line index
	history: list[str] = []

	def rebuild_engine(new_db: str):
		nonlocal service, engine, db_path
		db_path = new_db
		service, engine = _build_engine_and_adapter(args.mode, db_path)
		echo(f"🔁 已切换数据库并重建引擎 -> {db_path}")

	def exec_ir(ir: dict):
		try:
			res = engine.execute(ir)
		except Exception as e:
			echo(f"❌ IR 执行异常: {e}")
			return
		if not getattr(res, 'success', False):
			echo(f"❌ 失败: {res.error}")
			if output_mode == 'full':
				try:
					echo(json.dumps({'error': getattr(res,'error',None)}, ensure_ascii=False))
				except Exception:
					pass
			return
		data = res.data or {}
		op = ir.get('op')
		if output_mode == 'full':
			# 完整 JSON 输出
			try:
				echo(json.dumps({'op': op, 'success': True, 'data': data}, ensure_ascii=False))
			except Exception:
				echo(str(data))
			return
		# brief 模式
		if op == 'Encode':
			rid = data.get('inserted_id') or data.get('id')
			echo(f"✅ Encode id={rid} dim={data.get('embedding_dim')}")
			return
		if op == 'Retrieve':
			rows = data.get('rows') if isinstance(data, dict) else (data if isinstance(data, list) else [])
			echo(f"✅ Retrieve rows={len(rows)}")
			for idx, row in enumerate(rows[:3], 1):  # 显示前3条
				text_preview = (row.get('text') or '')[:60]
				echo(f"   [{idx}] id={row.get('id')} {text_preview}{'...' if len(text_preview)>=60 else ''}")
			return
		if op == 'Summarize':
			summary = str(data.get('summary',''))
			echo(f"✅ Summarize -> {summary[:160]}{'…' if len(summary)>160 else ''}")
			return
		affected = data.get('affected_rows') or data.get('updated_rows') or data.get('success_count')
		if affected is not None:
			echo(f"✅ {op} affected={affected}")
		else:
			echo(f"✅ {op} 完成")

	def run_inline_workflow(payload: dict) -> bool:
		steps = payload.get('steps')
		if not isinstance(steps, list):
			return False
		name = payload.get('name') or payload.get('title') or 'workflow'
		echo(f"🧾 执行内联工作流: {name} | 步骤数 {len(steps)}")
		executed = False
		for idx, step in enumerate(steps, start=1):
			if not isinstance(step, dict):
				echo(f"⚠️ 跳过无效步骤 {idx}: 类型 {type(step).__name__}")
				continue
			ir = step.get('ir') or step
			if not isinstance(ir, dict) or not ir.get('op'):
				echo(f"⚠️ 跳过步骤 {idx}: 未找到合法的 IR")
				continue
			title = step.get('name') or ir.get('name') or f'step {idx}'
			echo(f"➡️  [{idx}/{len(steps)}] {title} -> {ir.get('op')}")
			exec_ir(ir)
			executed = True
		return executed

	def execute_json_payload(obj: Any) -> bool:
		if isinstance(obj, dict):
			if obj.get('op'):
				exec_ir(obj)
				return True
			if run_inline_workflow(obj):
				return True
			echo('⚠️ JSON 对象缺少可执行内容 (需要 op 或 steps)')
			return False
		if isinstance(obj, list):
			executed_any = False
			for idx, item in enumerate(obj, start=1):
				echo(f"📦 处理列表元素 {idx}/{len(obj)}")
				executed_any |= execute_json_payload(item)
			return executed_any
		echo('⚠️ 不支持的 JSON 类型，预期对象或数组')
		return False

	def run_script_line(idx: int):
		nonlocal script_ptr
		if idx < 1 or idx > len(script_lines):
			echo("⚠️ 行号超出范围")
			return
		line = script_lines[idx-1].strip()
		script_ptr = idx  # set pointer to this
		if not line or line.startswith('#'):
			echo(f"(跳过空/注释行 {idx})")
			return
		echo(f"▶️ [脚本行{idx}] {line}")
		process_command(line)

	def process_command(line: str):
		nonlocal script_ptr, output_mode
		line = line.strip()
		if not line:
			return
		# 若整行是 JSON（IR）直接尝试执行
		if line[0] in '{[':
			try:
				obj = json.loads(line)
			except Exception as e:
				echo(f"JSON 解析失败: {e}")
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
		
		if cmd in ('quit','exit'):
			raise SystemExit(0)
		if cmd == 'help':
			echo("""命令:
  基础: help|list|next|n|run <i>|db|history|save <p>|output (brief|full)|quit
  12种操作快捷方式:
    encode <text>           - 编码/创建记忆 (Encode)
    retrieve <query>        - 检索记忆 (Retrieve)
    label <id> <tags>       - 打标签，多个标签用逗号分隔 (Label)
    update <id> <text>      - 更新记录内容 (Update)
    delete <id>             - 删除记录 (Delete)
    promote <id>            - 提升优先级 (Promote)
    demote <id>             - 降低优先级 (Demote)
    lock <id>               - 锁定记录 (Lock)
    merge <ids>             - 合并记录，格式: merge 2,3 into 1 (Merge)
    split <id>              - 拆分记录 (Split)
    expire <id> <ttl>       - 设置过期，如: P7D=7天 (Expire)
    summarize <ids>         - 生成多条记录的摘要，格式: summarize 1,2,3 (Summarize)
  高级: ir <json>|switch-db <p>|<粘贴IR/工作流JSON>""")
		elif cmd == 'list':
			if not script_lines:
				echo('ℹ️ 未加载脚本'); return
			for i,l in enumerate(script_lines, start=1):
				marker = '>>' if (i == script_ptr+1) else '  '
				echo(f"{marker} {i:03d}: {l}")
		elif cmd in ('next','n'):
			if not script_lines:
				echo('ℹ️ 没有脚本'); return
			if script_ptr >= len(script_lines):
				echo('⚠️ 已到脚本末尾'); return
			run_script_line(script_ptr+1)
		elif cmd == 'run':
			if not arg.isdigit():
				echo('用法: run <行号>'); return
			run_script_line(int(arg))
		
		# 12种操作的快捷方式
		elif cmd == 'encode':
			if not arg:
				echo('用法: encode <text>'); return
			ir = {"stage":"ENC","op":"Encode","args":{"payload":{"text":arg}}}
			exec_ir(ir)
		elif cmd == 'retrieve':
			if not arg:
				echo('用法: retrieve <query>'); return
			ir = {"stage":"RET","op":"Retrieve","target":{"search":{"intent":{"query":arg},"overrides":{"k":5}}},"args":{}}
			exec_ir(ir)
		elif cmd == 'label':
			parts = arg.split(' ', 1)
			if len(parts) < 2:
				echo('用法: label <id> <tags> (多个标签用逗号分隔)'); return
			record_id, tags_str = parts
			tags = [t.strip() for t in tags_str.split(',')]
			ir = {"stage":"STO","op":"Label","target":{"ids":[record_id]},"args":{"tags":tags,"mode":"add"}}
			exec_ir(ir)
		elif cmd == 'update':
			parts = arg.split(' ', 1)
			if len(parts) < 2:
				echo('用法: update <id> <new_text>'); return
			record_id, new_text = parts
			ir = {"stage":"STO","op":"Update","target":{"ids":[record_id]},"args":{"set":{"text":new_text}}}
			exec_ir(ir)
		elif cmd == 'delete':
			if not arg:
				echo('用法: delete <id>'); return
			ir = {"stage":"STO","op":"Delete","target":{"ids":[arg]},"args":{"soft":True}}
			exec_ir(ir)
		elif cmd == 'promote':
			if not arg:
				echo('用法: promote <id>'); return
			ir = {"stage":"STO","op":"Promote","target":{"ids":[arg]},"args":{"weight_delta":0.2}}
			exec_ir(ir)
		elif cmd == 'demote':
			if not arg:
				echo('用法: demote <id>'); return
			ir = {"stage":"STO","op":"Demote","target":{"ids":[arg]},"args":{"archive":True}}
			exec_ir(ir)
		elif cmd == 'lock':
			if not arg:
				echo('用法: lock <id>'); return
			ir = {"stage":"STO","op":"Lock","target":{"ids":[arg]},"args":{"mode":"read_only"}}
			exec_ir(ir)
		elif cmd == 'merge':
			# 格式: merge 2,3 into 1 (将2,3合并到1)
			# 或: merge 2,3,4 (将2,3合并到第一个，即2是主记录)
			if not arg:
				echo('用法: merge <child_ids> into <primary_id> 或 merge <primary_id>,<child_ids>'); return
			# 解析格式
			if ' into ' in arg:
				parts = arg.split(' into ')
				child_ids_str = parts[0].strip()
				primary_id = parts[1].strip()
				child_ids = [i.strip() for i in child_ids_str.split(',')]
			else:
				ids_str = arg.split(',')
				if len(ids_str) < 2:
					echo('⚠️ 至少需要2个ID进行合并'); return
				primary_id = ids_str[0].strip()
				child_ids = [i.strip() for i in ids_str[1:]]
			ir = {"stage":"STO","op":"Merge","target":{"ids":child_ids},"args":{"strategy":"merge_into_primary","primary_id":primary_id}}
			exec_ir(ir)
		elif cmd == 'split':
			if not arg:
				echo('用法: split <id>'); return
			ir = {"stage":"STO","op":"Split","target":{"ids":[arg]},"args":{"strategy":"by_sentences","params":{"by_sentences":{"lang":"zh","max_sentences":3}}}}
			exec_ir(ir)
		elif cmd == 'expire':
			parts = arg.split(' ', 1)
			if len(parts) < 2:
				echo('用法: expire <id> <ttl> (如: expire 123 P7D 表示7天后过期)'); return
			record_id, ttl = parts
			ir = {"stage":"STO","op":"Expire","target":{"ids":[record_id]},"args":{"ttl":ttl,"on_expire":"soft_delete"}}
			exec_ir(ir)
		elif cmd == 'summarize':
			# 格式: summarize 1,2,3 [focus]
			if not arg:
				echo('用法: summarize <ids> [focus] (多个id用逗号分隔) 或 summarize all [focus]'); return
			parts = arg.split(' ', 1)
			ids_or_all = parts[0]
			focus = parts[1] if len(parts) > 1 else "总体概述"
			
			if ids_or_all.lower() == 'all':
				# 总结所有记录
				ir = {"stage":"RET","op":"Summarize","target":{"all":True},"args":{"focus":focus,"max_tokens":256},"meta":{"confirmation":True}}
			else:
				# 总结指定记录
				ids = [i.strip() for i in ids_or_all.split(',')]
				ir = {"stage":"RET","op":"Summarize","target":{"ids":ids},"args":{"focus":focus,"max_tokens":256}}
			exec_ir(ir)
		
		# 其他命令
		elif cmd == 'ir':
			try:
				ir = json.loads(arg)
			except Exception as e:
				echo(f"JSON 解析失败: {e}"); return
			exec_ir(ir)
		elif cmd == 'switch-db':
			if not arg:
				echo('用法: switch-db <路径>'); return
			rebuild_engine(arg)
		elif cmd == 'db':
			echo(f"当前数据库: {db_path}")
		elif cmd == 'history':
			for i,h in enumerate(history, start=1):
				echo(f"{i:03d}: {h}")
		elif cmd == 'save':
			if not arg:
				echo('用法: save <路径>'); return
			try:
				Path(arg).write_text('\n'.join(history), encoding='utf-8')
				echo(f"✅ 已保存历史 -> {arg}")
			except Exception as e:
				echo(f"❌ 保存失败: {e}")
		elif cmd == 'output':
			if arg not in ('brief','full'):
				echo('用法: output brief|full'); return
			output_mode = arg
			echo(f"🔧 输出模式已切换为: {output_mode}")
		else:
			echo('未知命令，输入 help 获取帮助')

	echo("进入会话模式，输入 help 查看命令，Ctrl+C 退出。")
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
			echo(f"❌ 处理命令时错误: {e}")
	echo('👋 退出 session')
	return 0


## removed duplicate full demo implementation (deprecated)


def cmd_models_smoke():
	"""最小化模型调用测试：做一次 embed + 一次 generate。
	用法:
	  python manage.py models-smoke            # 依据 .env / MODEL_SERVICE
	  python manage.py models-smoke openai     # 强制OpenAI
	  python manage.py models-smoke ollama     # 强制Ollama
	  python manage.py models-smoke mock       # 模拟
	"""
	mode = None
	if len(sys.argv) >= 3:
		mode = sys.argv[2].lower()

	echo("=" * 60)
	echo("🧪 模型冒烟测试")
	echo("=" * 60)
	
	try:
		service = _build_models_service_from_env(mode)
		from text2mem.services.models_service import GenerationResult
		echo(f"🔧 使用模型:")
		echo(f"   Embedding: {service.embedding_model.__class__.__name__}")
		echo(f"   Generation: {service.generation_model.__class__.__name__}")
		echo("")

		# 1) 测试嵌入
		echo("📍 测试 1/2: 嵌入模型...")
		text = "用于嵌入的测试文本。Hello embeddings!"
		emb = service.encode_memory(text)
		echo(f"✅ Embedding 成功")
		echo(f"   维度: {emb.dimension}")
		echo(f"   模型: {emb.model}")
		echo("")

		# 2) 测试生成
		echo("📍 测试 2/2: 生成模型...")
		prompt = "请用一句话总结：Text2Mem 是一个文本记忆处理系统。"
		gen = service.generation_model.generate(prompt, temperature=0.2, max_tokens=60)
		echo(f"✅ Generation 成功")
		echo(f"   模型: {gen.model}")
		echo(f"   输出: {gen.text[:150]}{'...' if len(gen.text) > 150 else ''}")
		echo("")
		
		echo("=" * 60)
		echo("🎉 所有测试通过！")
		echo("=" * 60)
	except Exception as e:
		echo("")
		echo("=" * 60)
		echo(f"❌ 模型冒烟测试失败")
		echo("=" * 60)
		echo(f"错误: {e}")
		echo("")
		echo("💡 故障排查:")
		echo("   1. 检查 .env 配置: python manage.py status")
		echo("   2. 验证模型配置: python manage.py models-info")
		echo("   3. Ollama 用户: 确保服务运行 (ollama serve)")
		echo("   4. OpenAI 用户: 检查 API Key 是否正确")
		sys.exit(1)
	sys.exit(0)

def cmd_run_workflow():
	"""运行一个工作流JSON文件，按顺序执行每个IR步骤。
	用法:
	  python manage.py workflow <path-to-workflow.json> [--mode mock|ollama|openai|auto] [--db <db_path>] [--verbose]
	"""
	import argparse, json
	from text2mem.core.engine import Text2MemEngine
	from text2mem.adapters.sqlite_adapter import SQLiteAdapter

	parser = argparse.ArgumentParser(prog="manage.py workflow", add_help=False)
	parser.add_argument("workflow", help="工作流JSON文件路径")
	parser.add_argument("--mode", choices=["mock","ollama","openai","auto"], default=None)
	parser.add_argument("--db", dest="db_path", default=None, help="数据库路径（默认读取 TEXT2MEM_DB_PATH 或 ./text2mem.db）")
	parser.add_argument("--verbose", action="store_true", help="详细输出")
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo("用法: python manage.py workflow <workflow.json> [--mode mock|ollama|openai|auto] [--db path] [--verbose]")
		sys.exit(2)

	wf_path = Path(args.workflow)
	if not wf_path.exists():
		echo(f"❌ 工作流文件不存在: {wf_path}")
		sys.exit(2)

	db_path = args.db_path or os.environ.get("TEXT2MEM_DB_PATH") or "./text2mem.db"
	service = _build_models_service_from_env(args.mode)
	adapter = SQLiteAdapter(db_path, models_service=service)
	engine = Text2MemEngine(adapter=adapter, models_service=service)

	data = json.loads(wf_path.read_text(encoding="utf-8"))
	workflow_name = data.get("name") or data.get("title") or wf_path.name
	steps = data.get("steps", [])
	
	echo("=" * 60)
	echo(f"🚀 运行工作流: {workflow_name}")
	echo("=" * 60)
	echo(f"📄 文件: {wf_path}")
	echo(f"📦 步骤数: {len(steps)}")
	echo(f"🧠 模型: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	echo(f"🗄️  数据库: {db_path}")
	echo("=" * 60)
	echo("")

	success_count = 0
	failed_count = 0
	
	for idx, step in enumerate(steps, start=1):
		title = step.get("name") or step.get("description") or f"Step {step.get('step', idx)}"
		ir = step.get("ir") or step
		if not isinstance(ir, dict) or not ir.get("op"):
			echo(f"⚠️  [{idx}/{len(steps)}] 跳过无效步骤: {title}")
			continue
		
		echo(f"➡️  [{idx}/{len(steps)}] {title}")
		echo(f"    操作: {ir.get('op')} | 阶段: {ir.get('stage', 'N/A')}")
		
		try:
			result = engine.execute(ir)
		except Exception as e:
			echo(f"❌ 执行异常: {e}")
			if args.verbose:
				import traceback
				traceback.print_exc()
			failed_count += 1
			continue

		if not getattr(result, "success", False):
			echo(f"❌ 步骤失败: {result.error}")
			failed_count += 1
			continue

		data_out = result.data or {}
		op = ir.get("op")
		
		if op == "Encode":
			rid = data_out.get("inserted_id") or data_out.get("id")
			emb_dim = data_out.get("embedding_dim")
			echo(f"    ✅ 已编码 | ID={rid}, dim={emb_dim}")
		elif op == "Retrieve":
			rows = []
			if isinstance(data_out, list):
				rows = data_out
			elif isinstance(data_out, dict):
				rows = data_out.get("rows", []) or []
			echo(f"    ✅ 检索成功 | 返回 {len(rows)} 条记录")
			if args.verbose and rows:
				echo(f"       示例: {str(rows[0])[:120]}...")
		elif op == "Summarize":
			summary = str(data_out.get("summary", ""))
			echo(f"    ✅ 摘要生成 | {summary[:120]}{'...' if len(summary) > 120 else ''}")
		else:
			affected = data_out.get("affected_rows") or data_out.get("updated_rows")
			if affected is not None:
				echo(f"    ✅ 完成 | 受影响行: {affected}")
			else:
				echo(f"    ✅ 完成")
		
		success_count += 1
		echo("")

	echo("=" * 60)
	echo(f"🎉 工作流完成")
	echo("=" * 60)
	echo(f"✅ 成功: {success_count}/{len(steps)}")
	if failed_count > 0:
		echo(f"❌ 失败: {failed_count}/{len(steps)}")
	echo("=" * 60)
	
	sys.exit(0 if failed_count == 0 else 1)

def cmd_set_env():
	"""设置环境变量"""
	if len(sys.argv) < 4:
		echo("用法: manage.py set-env KEY VALUE")
		echo("例如: manage.py set-env TEXT2MEM_LOG_LEVEL DEBUG")
		return 1
	
	key = sys.argv[2]
	value = sys.argv[3]
	
	env_path = ROOT / ".env"
	
	# 读取现有的环境变量
	existing_vars = {}
	if env_path.exists():
		existing_vars = load_env_file(env_path)
	
	# 更新或添加环境变量
	existing_vars[key] = value
	
	# 重新构建.env文件
	env_content = "# Text2Mem 环境配置\n"
	provider = existing_vars.get("MODEL_SERVICE", "未指定")
	env_content += f"# 提供商: {provider}\n\n"
	
	# 添加配置分组
	sections = {
		"数据库设置": ["DATABASE_PATH", "TEXT2MEM_DB_PATH", "TEXT2MEM_DB_WAL", "TEXT2MEM_DB_TIMEOUT"],
		"嵌入模型设置": ["TEXT2MEM_EMBEDDING_PROVIDER", "TEXT2MEM_EMBEDDING_MODEL", "TEXT2MEM_EMBEDDING_BASE_URL"],
		"生成模型设置": ["TEXT2MEM_GENERATION_PROVIDER", "TEXT2MEM_GENERATION_MODEL", "TEXT2MEM_GENERATION_BASE_URL",
					"TEXT2MEM_TEMPERATURE", "TEXT2MEM_MAX_TOKENS", "TEXT2MEM_TOP_P"],
		"OpenAI设置": ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_API_BASE", "OPENAI_ORGANIZATION"],
		"Ollama设置": ["OLLAMA_BASE_URL", "OLLAMA_MODEL"],
		"其他设置": ["MODEL_SERVICE", "TEXT2MEM_LOG_LEVEL"]
	}
	
	# 找到键所属的部分
	key_section = "其他设置"
	for section, keys in sections.items():
		if key in keys:
			key_section = section
			break
	
	# 按分组写入配置
	processed_keys = set()
	for section, keys in sections.items():
		# 检查是否有任何属于此部分的配置
		section_keys = [k for k in keys if k in existing_vars]
		if section_keys:
			env_content += f"\n# {section}\n"
			for k in section_keys:
				env_content += f"{k}={existing_vars[k]}\n"
				processed_keys.add(k)
	
	# 添加任何未分类的键
	unprocessed_keys = [k for k in existing_vars if k not in processed_keys]
	if unprocessed_keys:
		env_content += "\n# 其他自定义设置\n"
		for k in unprocessed_keys:
			env_content += f"{k}={existing_vars[k]}\n"
	
	# 写入文件
	env_path.write_text(env_content, encoding="utf-8")
	
	echo(f"✅ 已设置环境变量: {key}={value}")
	return 0


def _normalize_docstring(text: Optional[str]) -> str:
	if not text:
		return ""
	return textwrap.dedent(text.expandtabs()).strip()


COMMAND_DEFINITIONS: Tuple[CommandInfo, ...] = (
	CommandInfo("status", cmd_status, "环境状态 (依赖 / .env / 服务探测)", "core"),
	CommandInfo("config", cmd_config, ".env 生成/更新 (--provider ...)", "core"),
	CommandInfo("set-env", cmd_set_env, "快速写入单个环境变量", "core", aliases=("set_env",)),
	CommandInfo("models-info", cmd_models_info, "显示解析后的模型配置", "core"),
	CommandInfo("demo", cmd_run_demo, "批量执行预置 IR / 工作流示例", "demos"),
	CommandInfo("ir", cmd_ir, "执行单条 IR JSON (--file|--inline)", "demos"),
	CommandInfo("workflow", cmd_run_workflow, "按 steps 顺序运行工作流文件", "workflows"),
	CommandInfo("list-workflows", cmd_list_workflows, "列出示例工作流 JSON", "workflows", aliases=("list_workflows",)),
	CommandInfo("session", cmd_session, "增强型持久会话 (支持12种操作快捷方式)", "interaction"),
	CommandInfo("models-smoke", cmd_models_smoke, "最小模型冒烟 (embed + generate)", "models", aliases=("models_smoke",)),
	CommandInfo("setup-ollama", cmd_setup_ollama, "拉取默认 Ollama 模型", "ops"),
	CommandInfo("setup-openai", cmd_setup_openai, "生成 OpenAI 使用的 .env", "ops"),
	CommandInfo("test", cmd_test, "运行 pytest 或最小冒烟", "ops"),
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
	echo("Usage: python manage.py <command> [options]")
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
	echo("使用 python manage.py help <command> 查看详细说明。")
	echo("")
	echo("示例:")
	echo("  python manage.py demo --mode mock")
	echo("  python manage.py ir --mode mock --inline '{\"stage\":\"RET\",\"op\":...")
	echo("  python manage.py session --mode mock --output full")


def print_command_help(name: str) -> int:
	info = COMMAND_LOOKUP.get(name)
	if not info:
		echo(f"未知命令: {name}")
		echo("使用 python manage.py help 查看可用命令。")
		return 1
	label = next((lbl for key, lbl in COMMAND_GROUPS if key == info.group), info.group)
	echo(f"命令: {_command_names(info)}")
	echo(f"分组: {label}")
	echo(f"概要: {info.summary}")
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
	if cmd in ('help', '-h', '--help'):
		target = sys.argv[2] if len(sys.argv) > 2 else None
		if not target:
			print_usage()
			return 0
		return print_command_help(target)
	info = COMMAND_LOOKUP.get(cmd)
	if not info:
		echo(f"Unknown command: {cmd}")
		echo("使用 python manage.py help 查看命令列表。")
		return 2
	result = info.handler()
	return result if isinstance(result, int) else 0


if __name__ == "__main__":
	sys.exit(main())


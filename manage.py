#!/usr/bin/env python3
"""
Project manager for Text2Mem

Commands:
  - status: quick environment status
  - config: write a .env file (--provider [ollama|openai])
  - setup-ollama: pull default models via ollama (if installed)
	- setup-openai: create/update .env for OpenAI usage
	- workflow: run a workflow JSON (examples/workflows/*.json)
  - test: run tests (pytest), or smoke integration if pytest absent
	- models-info: show resolved provider/models from current env
	- models-smoke [mode]: minimal embed+generate smoke (mock|ollama|openai|auto)
	- features [--mode ...] [--db ...]: run encode/retrieve/summarize flow
	- ir [--mode ...] (--file path.json | --inline '{...}') [--db ...]: execute a single IR
	- list-workflows: list bundled workflow files
	- repl [--mode ...] [--db ...]: interactive shell to run commands (embed/gen/ir/...)
		- bench-planning --input file.jsonl [--out report.json]: validate schemas against IR v1
"""
import os, sys, subprocess, re, json, argparse, time
from pathlib import Path
from scripts.cli_core import (
	echo, load_env_file, ENV_PATH as CORE_ENV_PATH,
	build_models_service_from_env as _build_models_service_from_env,
	build_engine_and_adapter as _build_engine_and_adapter,
)
from scripts.cli_helpers import run_basic_demo
from scripts.config_helpers import generate_grouped_env
from scripts.env_utils import which

ROOT = Path(__file__).parent
ENV_PATH = CORE_ENV_PATH

# Load env values (and inject into process) once at startup
ENV_VARS = load_env_file(ENV_PATH) if ENV_PATH.exists() else {}

def cmd_status():
	"""显示环境与依赖状态。"""
	from text2mem.core.config import ModelConfig
	env_exists = ENV_PATH.exists()
	cfg = ModelConfig.from_env()
	db_path = os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
	echo("[环境]")
	echo(f"  .env: {'存在' if env_exists else '缺失'} -> {ENV_PATH}")
	echo(f"  Provider: {cfg.provider} | embed={cfg.embedding_provider}:{cfg.embedding_model} | gen={cfg.generation_provider}:{cfg.generation_model}")
	if cfg.embedding_provider == 'ollama' or cfg.generation_provider == 'ollama':
		echo(f"  Ollama: {os.environ.get('TEXT2MEM_OLLAMA_BASE_URL') or os.environ.get('OLLAMA_BASE_URL') or cfg.ollama_base_url}")
	if cfg.provider == 'openai' or cfg.embedding_provider == 'openai' or cfg.generation_provider == 'openai':
		api_key_set = bool(os.environ.get('OPENAI_API_KEY'))
		echo(f"  OpenAI API Key: {'已设置' if api_key_set else '未设置'}")
	echo("[数据库]")
	echo(f"  路径: {db_path}")
	echo("[依赖探测]")
	echo(f"  ollama: {'可用' if which('ollama') else '不可用'}")
	return 0

def cmd_config():
	"""生成/更新 .env 文件。"""
	parser = argparse.ArgumentParser(prog='manage.py config', add_help=False)
	parser.add_argument('--provider', choices=['mock','ollama','openai'], required=True)
	parser.add_argument('--openai-key', default=None)
	parser.add_argument('--ollama-base-url', default='http://localhost:11434')
	parser.add_argument('--embed-model', default=None)
	parser.add_argument('--gen-model', default=None)
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: manage.py config --provider [mock|ollama|openai] [--openai-key ...]'); return 2

	existing = dict(ENV_VARS)
	provider = args.provider
	existing['MODEL_SERVICE'] = provider
	existing['TEXT2MEM_PROVIDER'] = provider
	existing['TEXT2MEM_EMBEDDING_PROVIDER'] = 'openai' if provider=='openai' else ('ollama' if provider=='ollama' else provider)
	existing['TEXT2MEM_GENERATION_PROVIDER'] = existing['TEXT2MEM_EMBEDDING_PROVIDER']

	if provider == 'mock':
		# Minimal
		existing.setdefault('TEXT2MEM_EMBEDDING_MODEL', 'dummy-embedding')
		existing.setdefault('TEXT2MEM_GENERATION_MODEL', 'dummy-llm')
	elif provider == 'ollama':
		existing['TEXT2MEM_OLLAMA_BASE_URL'] = args.ollama_base_url
		existing['OLLAMA_BASE_URL'] = args.ollama_base_url
		existing['TEXT2MEM_EMBEDDING_MODEL'] = args.embed_model or 'nomic-embed-text'
		existing['TEXT2MEM_GENERATION_MODEL'] = args.gen_model or 'qwen2:0.5b'
	else:  # openai
		if args.openai_key:
			existing['OPENAI_API_KEY'] = args.openai_key
		existing['TEXT2MEM_EMBEDDING_MODEL'] = args.embed_model or 'text-embedding-3-small'
		existing['TEXT2MEM_GENERATION_MODEL'] = args.gen_model or 'gpt-3.5-turbo'

	content = generate_grouped_env(existing, provider)
	ENV_PATH.write_text(content, encoding='utf-8')
	echo(f"✅ 已写入 .env -> {ENV_PATH}")
	return 0

def cmd_setup_ollama():
	"""拉取常用 Ollama 模型。"""
	exe = which('ollama')
	if not exe:
		echo('❌ 未找到 ollama 可执行文件，请先安装 https://ollama.ai'); return 1
	from text2mem.core.config import ModelConfig
	cfg = ModelConfig.for_ollama()
	emb = os.environ.get('TEXT2MEM_EMBEDDING_MODEL') or cfg.embedding_model
	gen = os.environ.get('TEXT2MEM_GENERATION_MODEL') or cfg.generation_model
	echo(f"⬇️ 拉取嵌入模型: {emb}")
	try:
		subprocess.run([exe, 'pull', emb], check=True)
	except Exception as e:
		echo(f"⚠️ 拉取 {emb} 失败: {e}")
	echo(f"⬇️ 拉取生成模型: {gen}")
	try:
		subprocess.run([exe, 'pull', gen], check=True)
	except Exception as e:
		echo(f"⚠️ 拉取 {gen} 失败: {e}")
	echo('✅ 完成')
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
	try:
		r = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=str(ROOT))
		return r.returncode
	except Exception:
		echo('⚠️ 无法运行 pytest，改为最小冒烟测试')
		try:
			service = _build_models_service_from_env(None)
			emb = service.encode_memory('hello embeddings')
			echo(f"✅ Embedding ok, dim={emb.dimension}")
			gen = service.generation_model.generate('一句话总结：Text2Mem 是什么？')
			echo(f"✅ Generation ok, model={gen.model}")
			return 0
		except Exception as e:
			echo(f"❌ 冒烟失败: {e}")
			return 1

def cmd_models_info():
	"""显示当前模型解析配置。"""
	from text2mem.core.config import ModelConfig
	cfg = ModelConfig.from_env()
	echo("[模型解析]")
	echo(f"  provider={cfg.provider}")
	echo(f"  embedding: provider={cfg.embedding_provider} model={cfg.embedding_model}")
	echo(f"  generation: provider={cfg.generation_provider} model={cfg.generation_model}")
	echo(f"  ollama_base_url={cfg.ollama_base_url}")
	if os.environ.get('OPENAI_API_BASE'):
		echo(f"  openai_api_base={os.environ.get('OPENAI_API_BASE')}")
	return 0

def cmd_features():
	"""快速链路 Encode->Retrieve->Summarize。"""
	parser = argparse.ArgumentParser(prog='manage.py features', add_help=False)
	parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
	parser.add_argument('--db', dest='db_path', default=None)
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: manage.py features [--mode mock|ollama|openai|auto] [--db path]'); return 2
	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	echo(f"🧠 模型服务: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	run_basic_demo(echo, engine)
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
	"""运行演示：基于 examples/op_workflows 中的最小可执行工作流。
	用法: python manage.py demo [--mode mock|ollama|openai|auto] [--db path] [--set basic|ops]
	- basic: 运行一个小型 Encode->Retrieve->Summarize
	- ops: 依次运行每个单操作工作流（带前置种子）
	"""
	parser = argparse.ArgumentParser(prog='manage.py demo', add_help=False)
	parser.add_argument('--mode', choices=['mock','ollama','openai','auto'], default=None)
	parser.add_argument('--db', dest='db_path', default=None)
	parser.add_argument('--set', choices=['basic','ops'], default='ops')
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo('用法: python manage.py demo [--mode mock|ollama|openai|auto] [--db path] [--set basic|ops]'); return 2

	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	echo(f"🧠 模型服务: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	echo(f"🗄️  数据库: {args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'}")

	if args.set == 'basic':
		run_basic_demo(echo, engine)
		return 0

	# ops: run curated op workflows
	wf_dir = ROOT / 'examples' / 'op_workflows'
	files = [
		'op_encode.json',
		'op_label.json',
		'op_label_search.json',
	'op_label_via_search.json',
		'op_promote.json',
		'op_promote_search.json',
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
	from text2mem.core.engine import Text2MemEngine
	from text2mem.adapters.sqlite_adapter import SQLiteAdapter
	# Rebuild engine to ensure same service but fresh adapter DB path
	adapter = SQLiteAdapter(args.db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db', models_service=service)
	engine = Text2MemEngine(adapter=adapter, models_service=service)

	import json as _json
	ran = 0
	for name in files:
		path = wf_dir / name
		if not path.exists():
			continue
		data = _json.loads(path.read_text(encoding='utf-8'))
		steps = data.get('steps', [])
		echo(f"🚀 运行 {name} | 步骤 {len(steps)}")
		for i, step in enumerate(steps, start=1):
			ir = step.get('ir') or step
			title = step.get('name') or f'step {i}'
			echo(f"➡️  [{name}] {title} -> {ir.get('op')}")
			try:
				res = engine.execute(ir)
			except Exception as e:
				echo(f"❌ 执行失败: {e}"); return 1
			if not getattr(res, 'success', False):
				echo(f"❌ 失败: {res.error}"); return 1
			out = res.data or {}
			op = ir.get('op')
			if op == 'Encode':
				rid = out.get('inserted_id') or out.get('id')
				echo(f"   ✅ id={rid} dim={out.get('embedding_dim')}")
			elif op == 'Retrieve':
				rows = out.get('rows') if isinstance(out, dict) else []
				echo(f"   ✅ rows={len(rows)}")
			elif op == 'Summarize':
				s = str(out.get('summary',''))
				echo(f"   📝 {s[:160]}{'…' if len(s)>160 else ''}")
			else:
				affected = out.get('affected_rows') or out.get('updated_rows')
				if affected is not None:
					echo(f"   ✅ affected={affected}")
				else:
					echo("   ✅ 完成")
			ran += 1
	echo(f"🎉 demo 完成，共执行 {ran} 步")
	return 0


def cmd_list_workflows():
	"""列出内置工作流文件。"""
	candidates = [ROOT/"examples"/"workflows", ROOT/"examples"/"op_workflows", ROOT/"text2mem"/"examples"]
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


def cmd_repl():
	"""交互模式：接受命令行输入执行常见操作。
	命令：
	  embed <text>
	  gen <prompt>
	  ir <json>
	  encode <text>
	  retrieve <query>
	  summarize <focus>
	  help | quit | exit
	可选：python manage.py repl [--mode mock|ollama|openai|auto] [--db path]
	"""
	import argparse
	parser = argparse.ArgumentParser(prog="manage.py repl", add_help=False)
	parser.add_argument("--mode", choices=["mock","ollama","openai","auto"], default=None)
	parser.add_argument("--db", dest="db_path", default=None)
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo("用法: python manage.py repl [--mode mock|ollama|openai|auto] [--db path]"); sys.exit(2)

	service, engine = _build_engine_and_adapter(args.mode, args.db_path)
	echo(f"🧠 模型服务: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
	echo("输入 'help' 查看命令，'quit' 退出。")
	while True:
		try:
			line = input("t2m> ").strip()
		except (EOFError, KeyboardInterrupt):
			echo("")
			break
		if not line:
			continue
		cmd, *rest = line.split(" ", 1)
		arg = rest[0] if rest else ""
		try:
			if cmd in ("quit","exit"):
				break
			elif cmd == "help":
				echo("命令: embed|gen|ir|encode|retrieve|summarize|quit")
			elif cmd == "embed":
				res = service.encode_memory(arg)
				echo(f"dim={res.dimension} model={res.model}")
			elif cmd == "gen":
				res = service.generation_model.generate(arg)
				echo(res.text)
			elif cmd == "ir":
				ir = json.loads(arg)
				res = engine.execute(ir)
				echo(str(res.data)[:400])
			elif cmd == "encode":
				ir = {"stage": "ENC", "op": "Encode", "args": {"payload": {"text": arg}}}
				res = engine.execute(ir)
				row_id = (res.data or {}).get("inserted_id") or (res.data or {}).get("id")
				echo(f"ok id={row_id}")
			elif cmd == "retrieve":
				ir = {
					"stage": "RET",
					"op": "Retrieve",
					"target": {"search": {"intent": {"query": arg}, "overrides": {"k": 5}}},
					"args": {}
				}
				res = engine.execute(ir)
				rows = []
				if isinstance(res.data, list): rows = res.data
				elif isinstance(res.data, dict): rows = res.data.get("rows", []) or []
				echo(f"{len(rows)} rows")
			elif cmd == "summarize":
				ir = {"stage": "RET", "op": "Summarize", "args": {"focus": arg, "max_tokens": 120}}
				res = engine.execute(ir)
				echo(str((res.data or {}).get("summary","")))
			else:
				echo("未知命令，输入 'help' 查看帮助")
		except Exception as e:
			echo(f"❌ 错误: {e}")
	return 0


def cmd_bench_planning():
	"""Planning-only bench: validate schemas in a JSONL file.
	用法: python manage.py bench-planning --input path.jsonl [--out report.json] [--schema path]
	"""
	import argparse
	parser = argparse.ArgumentParser(prog="manage.py bench-planning", add_help=False)
	parser.add_argument("--input", required=True)
	parser.add_argument("--out", default=None)
	parser.add_argument("--schema", default=str(ROOT/"text2mem"/"schema"/"text2mem-ir-v1.json"))
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo("用法: python manage.py bench-planning --input file.jsonl [--out report.json] [--schema path]"); sys.exit(2)

	# Delegate to module to keep logic isolated
	import runpy
	mod_path = str(ROOT / "scripts" / "bench_planning.py")
	# Construct argv for the module's main
	sys_argv_backup = list(sys.argv)
	try:
		sys.argv = [mod_path, "--input", args.input, "--schema", args.schema] + (["--out", args.out] if args.out else [])
		runpy.run_path(mod_path, run_name="__main__")
	finally:
		sys.argv = sys_argv_backup
	return 0


def cmd_session():
	"""持久化会话模式：可指定数据库/模式，加载脚本并逐条执行或交互输入。
	用法: python manage.py session [--mode mock|ollama|openai|auto] [--db path] [--script file]

	可用指令:
	  help               显示帮助
	  list               列出脚本行
	  next / n           执行下一行脚本
	  run <idx>          执行脚本第 idx 行 (从 1 开始)
	  encode <text>      编码一条记忆
	  retrieve <query>   检索
	  summarize <focus>  摘要
	  ir <json>          执行单条 IR JSON
	  switch-db <path>   切换数据库 (重建引擎)
	  db                 显示当前数据库
	  history            显示已执行指令历史
	  save <path>        保存历史到文件
	  quit/exit          退出
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
			rows = data.get('rows') if isinstance(data, dict) else []
			echo(f"✅ Retrieve rows={len(rows)}")
			return
		if op == 'Summarize':
			summary = str(data.get('summary',''))
			echo(f"✅ Summarize -> {summary[:160]}{'…' if len(summary)>160 else ''}")
			return
		affected = data.get('affected_rows') or data.get('updated_rows')
		if affected is not None:
			echo(f"✅ {op} affected={affected}")
		else:
			echo(f"✅ {op} 完成")

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
		nonlocal script_ptr
		line = line.strip()
		if not line:
			return
		# 若整行是 JSON（IR）直接尝试执行
		if line[0] in '{[':
			try:
				obj = json.loads(line)
				if isinstance(obj, dict) and obj.get('op'):
					history.append(line)
					exec_ir(obj)
					return
			except Exception:
				pass  # 继续按普通命令解析
		history.append(line)
		parts = line.split(' ', 1)
		cmd = parts[0]
		arg = parts[1] if len(parts) > 1 else ''
		if cmd in ('quit','exit'):
			raise SystemExit(0)
		if cmd == 'help':
			echo("命令: help|list|next|n|run <i>|encode <t>|retrieve <q>|summarize <f>|ir <json>|switch-db <p>|db|history|save <p>|output (brief|full)|quit|<直接粘贴IR JSON>")
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
		elif cmd == 'encode':
			ir = {"stage":"ENC","op":"Encode","args":{"payload":{"text":arg},"use_embedding":True}}
			exec_ir(ir)
		elif cmd == 'retrieve':
			ir = {"stage":"RET","op":"Retrieve","args":{"query":arg,"k":5}}
			exec_ir(ir)
		elif cmd == 'summarize':
			ir = {"stage":"RET","op":"Summarize","args":{"focus":arg,"max_tokens":160}}
			exec_ir(ir)
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

	try:
		service = _build_models_service_from_env(mode)
		from text2mem.services.models_service import GenerationResult
		echo(f"🧪 正在使用: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")

		# 1) 测试嵌入
		text = "用于嵌入的测试文本。Hello embeddings!"
		emb = service.encode_memory(text)
		echo(f"✅ Embedding 维度: {emb.dimension}, 模型: {emb.model}")

		# 2) 测试生成
		prompt = "请用一句话总结：Text2Mem 是一个文本记忆处理系统。"
		gen = service.generation_model.generate(prompt, temperature=0.2, max_tokens=60)
		echo(f"✅ Generation 模型: {gen.model}")
		echo(f"📝 输出: {gen.text[:200]}...")
	except Exception as e:
		echo(f"❌ 模型冒烟测试失败: {e}")
		sys.exit(1)
	sys.exit(0)

def cmd_run_workflow():
	"""运行一个工作流JSON文件，按顺序执行每个IR步骤。
	用法:
	  python manage.py workflow <path-to-workflow.json> [--mode mock|ollama|openai|auto] [--db <db_path>]
	"""
	import argparse, json
	from text2mem.core.engine import Text2MemEngine
	from text2mem.adapters.sqlite_adapter import SQLiteAdapter

	parser = argparse.ArgumentParser(prog="manage.py workflow", add_help=False)
	parser.add_argument("workflow", help="工作流JSON文件路径")
	parser.add_argument("--mode", choices=["mock","ollama","openai","auto"], default=None)
	parser.add_argument("--db", dest="db_path", default=None, help="数据库路径（默认读取 TEXT2MEM_DB_PATH 或 ./text2mem.db）")
	try:
		args = parser.parse_args(sys.argv[2:])
	except SystemExit:
		echo("用法: python manage.py workflow <workflow.json> [--mode mock|ollama|openai|auto] [--db path]")
		sys.exit(2)

	wf_path = Path(args.workflow)
	if not wf_path.exists():
		echo(f"❌ 工作流文件不存在: {wf_path}")
		sys.exit(2)

	# 选择数据库
	db_path = args.db_path or os.environ.get("TEXT2MEM_DB_PATH") or "./text2mem.db"
	# 构建模型服务
	service = _build_models_service_from_env(args.mode)

	# 引擎与适配器
	adapter = SQLiteAdapter(db_path, models_service=service)
	engine = Text2MemEngine(adapter=adapter, models_service=service)

	# 读取工作流
	data = json.loads(wf_path.read_text(encoding="utf-8"))
	steps = data.get("steps", [])
	echo(f"🚀 运行工作流: {wf_path.name} | 步骤数: {len(steps)} | DB: {db_path}")
	echo(f"🧠 模型: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")

	success_count = 0
	for idx, step in enumerate(steps, start=1):
		title = step.get("name") or step.get("description") or f"Step {step.get('step', idx)}"
		ir = step.get("ir") or step  # 容错：若直接是IR
		if not isinstance(ir, dict) or not ir.get("op"):
			echo(f"⚠️ 跳过无效步骤[{idx}]: 缺少IR")
			continue
		echo(f"➡️ [{idx}/{len(steps)}] {title} -> {ir.get('op')}")
		try:
			result = engine.execute(ir)
		except Exception as e:
			echo(f"❌ 执行失败: {e}")
			sys.exit(1)

		if not getattr(result, "success", False):
			echo(f"❌ 步骤失败: {result.error}")
			sys.exit(1)

		# 结果摘要输出
		data_out = result.data or {}
		op = ir.get("op")
		if op == "Encode":
			rid = data_out.get("inserted_id") or data_out.get("id")
			emb_dim = data_out.get("embedding_dim")
			emb_model = data_out.get("embedding_model")
			emb_provider = data_out.get("embedding_provider")
			echo(f"   ✅ 已编码，ID={rid}")
			if emb_model or emb_dim or emb_provider:
				echo(f"      🧩 向量: dim={emb_dim} model={emb_model} provider={emb_provider}")
		elif op == "Retrieve":
			rows = []
			if isinstance(data_out, list):
				rows = data_out
			elif isinstance(data_out, dict):
				rows = data_out.get("rows", []) or []
			note = data_out.get("note")
			echo(f"   ✅ 检索到 {len(rows)} 条" + (f" | {note}" if note else ""))
			if rows:
				# 打印一条简短预览
				import json as _json
				try:
					pv = _json.dumps(rows[0], ensure_ascii=False)[:200]
				except Exception:
					pv = str(rows[0])[:200]
				echo(f"      📋 示例: {pv}…")
		elif op == "Summarize":
			summary = str(data_out.get("summary", ""))
			model = data_out.get("model")
			usage = data_out.get("tokens") or {}
			echo(f"   📝 摘要: {summary[:200]}{'…' if len(summary)>200 else ''}")
			if model:
				echo(f"      🔎 模型: {model} | tokens: {usage}")
		else:
			# 通用反馈
			affected = data_out.get("affected_rows") or data_out.get("updated_rows")
			if affected is not None:
				echo(f"   ✅ 完成 | 受影响行: {affected}")
			else:
				echo("   ✅ 完成")
		success_count += 1

	echo(f"🎉 工作流完成: {success_count}/{len(steps)} 步成功")
	sys.exit(0)

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

def main():
	if len(sys.argv) < 2:
		echo("Usage: manage.py <command> [options]")
		echo("")
		echo("[核心 / 环境]")
		echo("  status                      环境状态 (依赖 / .env / 服务探测)")
		echo("  models-info                 当前模型解析配置")
		echo("  config --provider <p>       生成/更新 .env (mock|ollama|openai)")
		echo("  set-env KEY VALUE           快速写入单个环境变量并重写分组")
		echo("")
		echo("[功能演示 / 典型流程]")
		echo("  demo [--mode --db --full --json --perf]  功能演示 (--full 含12操作)")
		echo("  features [--mode --db]      Encode -> Retrieve -> Summarize 快速链路")
		echo("  ir [--mode (--file|--inline) --db]  执行单条 IR JSON")
		echo("")
		echo("[Bench / 评测]")
		echo("  bench-planning --input file.jsonl [--out report.json]  规划层 Schema 合法性校验")
		echo("")
		echo("[工作流]")
		echo("  workflow <json> [--mode --db]  运行工作流文件 steps")
		echo("  list-workflows               列出内置工作流示例")
		echo("")
		echo("[交互 / 会话]")
		echo("  repl [--mode --db]           简单交互 (embed/gen/ir/...)")
		echo("  session [--mode --db --script file --output full|brief]  持久会话")
		echo("")
		echo("[模型快速验证]")
		echo("  models-smoke [mode]          最小 embed+generate 冒烟")
		echo("")
		echo("[运维 / 测试 / 依赖]")
		echo("  test                         运行测试套件 (优先 pytest)")
		echo("  setup-ollama                 准备/拉取 Ollama 模型 (占位)")
		echo("  setup-openai                 生成 OpenAI 用 .env (占位)")
		echo("")
		echo("示例:")
		echo("  python manage.py demo --mode mock")
		echo('  python manage.py ir --mode mock --inline "{\"stage\":\"RET\",\"op\":\"Retrieve\",\"args\":{\"query\":\"测试\",\"k\":2}}"')
		echo("  python manage.py session --mode mock --output full")
		return 1
	cmd = sys.argv[1]
	if cmd == "status":
		cmd_status()
		return 0
	if cmd == "config":
		cmd_config()
		return 0
	if cmd == "set-env":
		return cmd_set_env()
	if cmd == "setup-ollama":
		cmd_setup_ollama()
		return 0
	if cmd == "setup-openai":
		cmd_setup_openai()
		return 0
	if cmd == "test":
		cmd_test()
		return 0
	if cmd == "demo":
		cmd_run_demo()
		return 0
	if cmd == "models-smoke":
		cmd_models_smoke()
		return 0
	if cmd == "models-info":
		cmd_models_info()
		return 0
	if cmd == "features":
		cmd_features()
		return 0
	if cmd == "ir":
		cmd_ir()
		return 0
	if cmd == "list-workflows":
		cmd_list_workflows()
		return 0
	if cmd == "repl":
		cmd_repl()
		return 0
	if cmd == "session":
		cmd_session()
		return 0
	if cmd == "workflow":
		cmd_run_workflow()
		return 0
	if cmd == "bench-planning":
		cmd_bench_planning()
		return 0
	echo(f"Unknown command: {cmd}")
	return 2


if __name__ == "__main__":
	sys.exit(main())


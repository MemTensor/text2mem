"""CLI helper utilities for Text2Mem management commands.

Centralizes repeated logic (demo sequences, IR execution formatting) so
`manage.py` stays lean. Both `manage.py demo` and `scripts/full_demo.py`
should import and reuse these helpers.
"""
from __future__ import annotations
import time, os
from typing import Any, Dict, Optional

# manage.py defines these; we import lazily inside functions to avoid cycles.

class IRRunResult:
    def __init__(self, ok: bool, data: Any = None, error: str | None = None, duration_ms: float = 0.0, op: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error
        self.duration_ms = duration_ms
        self.op = op


def execute_ir(engine, ir: Dict[str, Any]):
    """Execute an IR dict via engine and wrap timing + success flag."""
    start = time.time()
    res = engine.execute(ir)
    ok = getattr(res, 'success', False)
    data = res.data if ok else {}
    dur = (time.time() - start) * 1000
    return IRRunResult(ok=ok, data=data, error=getattr(res, 'error', None), duration_ms=dur, op=ir.get('op'))


def format_and_echo(echo, title: str, ir: Dict[str, Any], r: IRRunResult):
    """Print concise formatted output for a finished IR run."""
    if not r.ok:
        echo(f"❌ {title} 失败: {r.error}")
        return
    op = ir.get("op")
    d = r.data
    dur = f"({r.duration_ms:.1f}ms)"
    if op == "Encode":
        rid = d.get("inserted_id") or d.get("id")
        echo(f"✅ {title} -> id={rid} dim={d.get('embedding_dim')} {dur}")
    elif op == "Retrieve":
        rows = d.get("rows") if isinstance(d, dict) else []
        echo(f"✅ {title} -> {len(rows)} rows {dur}")
    elif op == "Summarize":
        summary = str(d.get("summary", ""))
        echo(f"✅ {title} -> summary {summary[:60]}{'…' if len(summary)>60 else ''} {dur}")
    elif op in {"Update","Label","Promote","Demote","Delete","Lock","Expire"}:
        affected = d.get("affected_rows") or d.get("updated_rows")
        if affected is not None:
            echo(f"✅ {title} -> affected={affected} {dur}")
        else:
            echo(f"✅ {title} {dur}")
    elif op == "Split":
        echo(f"✅ {title} -> total_splits={d.get('total_splits')} {dur}")
    elif op == "Merge":
        echo(f"✅ {title} -> merged={d.get('merged_count')} primary={d.get('primary_id')} {dur}")
    else:
        echo(f"✅ {title} {dur}")


def run_basic_demo(echo, engine):
    """Encode -> Retrieve -> Summarize minimal path. Returns summary dict."""
    ops_log = []
    encode_ir = {"stage":"ENC","op":"Encode","args":{"payload":{"text":"这是一条测试记忆，用于验证Text2Mem系统是否正常工作。"},"tags":["测试","演示"],"use_embedding":True}}
    r = execute_ir(engine, encode_ir); format_and_echo(echo, "Encode", encode_ir, r); ops_log.append(r)
    ret_ir = {"stage":"RET","op":"Retrieve","args":{"query":"测试","k":5}}
    r = execute_ir(engine, ret_ir); format_and_echo(echo, "Retrieve", ret_ir, r); ops_log.append(r)
    sum_ir = {"stage":"RET","op":"Summarize","args":{"focus":"测试","max_tokens":120}}
    r = execute_ir(engine, sum_ir); format_and_echo(echo, "Summarize", sum_ir, r); ops_log.append(r)
    return {
        "mode": "basic",
        "operations": [o.op for o in ops_log],
        "total_ms": sum(o.duration_ms for o in ops_log),
        "encode_id": ops_log[0].data.get('inserted_id') if ops_log and ops_log[0].ok else None
    }


def run_full_demo(echo, engine):
    """Execute 12 operations (exclude Clarify). Returns summary dict."""
    echo("🚀 运行 FULL DEMO (12 类操作)")
    ids: Dict[str, Any] = {}
    ops: list[IRRunResult] = []

    def log(ir_dict, title):
        r = execute_ir(engine, ir_dict); format_and_echo(echo, title, ir_dict, r); ops.append(r); return r

    main_r = log({"stage":"ENC","op":"Encode","args":{"payload":{"text":"项目A 第一次会议：讨论范围、目标与下一步计划。"},"tags":["project","meeting"],"type":"note","use_embedding":True}}, "Encode main")
    main_id = main_r.data.get("inserted_id") if main_r.ok else None
    sec_r = log({"stage":"ENC","op":"Encode","args":{"payload":{"text":"项目A 第二次会议：确定任务分工与风险。"},"tags":["project","meeting","notes"],"type":"note","use_embedding":True}}, "Encode secondary")
    secondary_id = sec_r.data.get("inserted_id") if sec_r.ok else None
    long_text = "# 概览\n项目A 说明文档。\n# 目标\n提升协作效率。\n# 计划\n1. 建立知识库\n2. 周会记录\n# 风险\n资源不足与延期风险。"
    long_r = log({"stage":"ENC","op":"Encode","args":{"payload":{"text":long_text},"tags":["doc","long"],"type":"note","use_embedding":True}}, "Encode long")
    long_id = long_r.data.get("inserted_id") if long_r.ok else None
    log({"stage":"ENC","op":"Encode","args":{"payload":{"text":"临时笔记：本周临时任务记录"},"tags":["temp","note"],"type":"note","use_embedding":True}}, "Encode temp")
    log({"stage":"ENC","op":"Encode","args":{"payload":{"text":"obsolete record: 过期的参考资料"},"tags":["cleanup"],"type":"note","use_embedding":True}}, "Encode obsolete")
    log({"stage":"STO","op":"Label","target":{"by_id":str(main_id) if main_id else None},"args":{"tags":["project","meeting","sensitive"]}}, "Label main add sensitive")
    log({"stage":"RET","op":"Retrieve","args":{"query":"项目A","k":10,"order_by":"time_desc"}}, "Retrieve project")
    log({"stage":"RET","op":"Summarize","target":{"by_tags":["project","meeting"],"match":"all"},"args":{"focus":"项目A 会议进展","max_tokens":200}}, "Summarize project meetings")
    log({"stage":"STO","op":"Promote","target":{"by_id":str(main_id) if main_id else None},"args":{"weight": 1.0}}, "Promote main")
    log({"stage":"STO","op":"Demote","target":{"by_id":str(secondary_id) if secondary_id else None},"args":{"archive":True}}, "Demote secondary")
    log({"stage":"STO","op":"Update","target":{"by_tags":["project"]},"args":{"set":{"weight":0.8,"text":"项目A 会议内容已整理"}}}, "Update project")
    log({"stage":"STO","op":"Split","target":{"by_id":str(long_id) if long_id else None},"args":{"strategy":"headings","inherit":{"tags":True}}}, "Split long doc")
    log({"stage":"STO","op":"Merge","target":{"by_tags":["meeting"],"match":"any"},"args":{"strategy":"fold_into_primary","primary_id":str(main_id),"soft_delete_children":True}}, "Merge meetings")
    log({"stage":"STO","op":"Lock","target":{"by_tags":["sensitive"]},"args":{"mode":"read_only","reason":"保护敏感会议记录"}}, "Lock sensitive")
    log({"stage":"STO","op":"Expire","target":{"by_tags":["temp"]},"args":{"ttl":"P7D","on_expire":"soft_delete"}}, "Expire temp")
    log({"stage":"STO","op":"Delete","target":{"by_query":"obsolete"},"args":{"soft":True,"reason":"清理过时"}}, "Delete obsolete")
    echo("🎉 FULL DEMO 完成 (Encode/Label/Retrieve/Summarize/Promote/Demote/Update/Split/Merge/Lock/Expire/Delete)")
    return {
        "mode": "full",
        "total_ms": sum(o.duration_ms for o in ops),
        "operations": [o.op for o in ops],
        "ids": {
            "main": main_id,
            "secondary": secondary_id,
            "long": long_id
        }
    }

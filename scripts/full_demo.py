#!/usr/bin/env python3
"""Standalone full demo runner using manage.py internal logic.
Usage:
  python scripts/full_demo.py [--mode mock|ollama|openai|auto] [--db path]

This mirrors `python manage.py demo --full` but keeps logic isolated
so it can be imported or extended (e.g., for benchmarking).
"""
from __future__ import annotations
import argparse, os, sys, time, json
from pathlib import Path

# Allow relative imports of project modules when run directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from manage import _build_engine_and_adapter, echo  # type: ignore

def run_full(mode: str | None, db_path: str | None):
    service, engine = _build_engine_and_adapter(mode, db_path)
    echo(f"🧠 模型服务: embed={service.embedding_model.__class__.__name__}, gen={service.generation_model.__class__.__name__}")
    echo(f"🗄️  数据库: {db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'}")

    def _run(ir: dict, title: str):
        start = time.time()
        res = engine.execute(ir)
        ok = getattr(res, 'success', False)
        data = res.data if ok else {}
        dur = (time.time() - start) * 1000
        if not ok:
            echo(f"❌ {title} 失败: {res.error}")
            return None
        op = ir.get("op")
        if op == "Encode":
            rid = data.get("inserted_id") or data.get("id")
            echo(f"✅ {title} -> id={rid} dim={data.get('embedding_dim')} ({dur:.1f}ms)")
            return rid
        if op == "Retrieve":
            rows = data.get("rows") if isinstance(data, dict) else []
            echo(f"✅ {title} -> {len(rows)} rows ({dur:.1f}ms)")
        elif op == "Summarize":
            summary = str(data.get("summary",""))
            echo(f"✅ {title} -> summary {summary[:60]}{'…' if len(summary)>60 else ''} ({dur:.1f}ms)")
        elif op in ("Update","Label","Promote","Demote","Delete","Lock","Expire"):
            affected = data.get("affected_rows") or data.get("updated_rows")
            if affected is not None:
                echo(f"✅ {title} -> affected={affected} ({dur:.1f}ms)")
            else:
                echo(f"✅ {title} ({dur:.1f}ms)")
        elif op == "Split":
            echo(f"✅ {title} -> total_splits={data.get('total_splits')} ({dur:.1f}ms)")
        elif op == "Merge":
            echo(f"✅ {title} -> merged={data.get('merged_count')} primary={data.get('primary_id')} ({dur:.1f}ms)")
        else:
            echo(f"✅ {title} ({dur:.1f}ms)")
        return data

    echo("🚀 运行 FULL DEMO (12 类操作)")
    ids = {}

    ids['main'] = _run({
        "stage":"ENC","op":"Encode","args":{"payload":{"text":"项目A 第一次会议：讨论范围、目标与下一步计划。"},"tags":["project","meeting"],"type":"note","use_embedding":True}
    }, "Encode main")

    ids['secondary'] = _run({
        "stage":"ENC","op":"Encode","args":{"payload":{"text":"项目A 第二次会议：确定任务分工与风险。"},"tags":["project","meeting","notes"],"type":"note","use_embedding":True}
    }, "Encode secondary")

    long_text = "# 概览\n项目A 说明文档。\n# 目标\n提升协作效率。\n# 计划\n1. 建立知识库\n2. 周会记录\n# 风险\n资源不足与延期风险。"
    ids['long'] = _run({
        "stage":"ENC","op":"Encode","args":{"payload":{"text":long_text},"tags":["doc","long"],"type":"note","use_embedding":True}
    }, "Encode long")

    ids['temp'] = _run({
        "stage":"ENC","op":"Encode","args":{"payload":{"text":"临时笔记：本周临时任务记录"},"tags":["temp","note"],"type":"note","use_embedding":True}
    }, "Encode temp")

    ids['obsolete'] = _run({
        "stage":"ENC","op":"Encode","args":{"payload":{"text":"obsolete record: 过期的参考资料"},"tags":["cleanup"],"type":"note","use_embedding":True}
    }, "Encode obsolete")

    _run({"stage":"STO","op":"Label","target":{"by_id":str(ids['main']) if ids.get('main') else None},"args":{"tags":["project","meeting","sensitive"]}}, "Label main add sensitive")

    _run({"stage":"RET","op":"Retrieve","args":{"query":"项目A","k":10,"order_by":"time_desc"}}, "Retrieve project")

    _run({"stage":"RET","op":"Summarize","target":{"by_tags":["project","meeting"],"match":"all"},"args":{"focus":"项目A 会议进展","max_tokens":200}}, "Summarize project meetings")

    _run({"stage":"STO","op":"Promote","target":{"by_id":str(ids['main']) if ids.get('main') else None},"args":{"priority":"urgent"}}, "Promote main")

    _run({"stage":"STO","op":"Demote","target":{"by_id":str(ids['secondary']) if ids.get('secondary') else None},"args":{"archive":True}}, "Demote secondary")

    _run({"stage":"STO","op":"Update","target":{"by_tags":["project"]},"args":{"set":{"priority":"high","text":"项目A 会议内容已整理"}}}, "Update project")

    _run({"stage":"STO","op":"Split","target":{"by_id":str(ids['long']) if ids.get('long') else None},"args":{"strategy":"headings","inherit":{"tags":True}}}, "Split long doc")

    _run({"stage":"STO","op":"Merge","target":{"by_tags":["meeting"],"match":"any"},"args":{"strategy":"fold_into_primary","primary_id":str(ids['main']),"soft_delete_children":True}}, "Merge meetings")

    _run({"stage":"STO","op":"Lock","target":{"by_tags":["sensitive"]},"args":{"mode":"read_only","reason":"保护敏感会议记录"}}, "Lock sensitive")

    _run({"stage":"STO","op":"Expire","target":{"by_tags":["temp"]},"args":{"ttl":"P7D","on_expire":"soft_delete"}}, "Expire temp")

    _run({"stage":"STO","op":"Delete","target":{"by_query":"obsolete"},"args":{"soft":True,"reason":"清理过时"}}, "Delete obsolete")

    echo("🎉 FULL DEMO 完成")


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--mode", choices=["mock","ollama","openai","auto"], default=None)
    p.add_argument("--db", dest="db_path", default=None)
    args = p.parse_args()
    run_full(args.mode, args.db_path)

if __name__ == "__main__":
    main()

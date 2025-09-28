"""Minimal CLI helper utilities used by :mod:`manage.py`.

The original helpers carried many legacy demos that no longer matched the
latest IR schema. This trimmed version keeps only the essentials that are
actively reused by the management commands.
"""

from __future__ import annotations

import time
from typing import Any, Dict


class IRRunResult:
    """Lightweight wrapper capturing execution outcome + timing."""

    def __init__(
        self,
        ok: bool,
        data: Any | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
        op: str | None = None,
    ) -> None:
        self.ok = ok
        self.data = data or {}
        self.error = error
        self.duration_ms = duration_ms
        self.op = op


def execute_ir(engine, ir: Dict[str, Any]) -> IRRunResult:
    """Execute an IR dict via *engine* and capture timing information."""

    start = time.time()
    res = engine.execute(ir)
    ok = getattr(res, "success", False)
    data = res.data if ok else {}
    dur = (time.time() - start) * 1000
    return IRRunResult(
        ok=ok,
        data=data,
        error=getattr(res, "error", None),
        duration_ms=dur,
        op=ir.get("op"),
    )


def format_and_echo(echo, title: str, ir: Dict[str, Any], result: IRRunResult) -> None:
    """Print a concise summary for a finished IR run."""

    if not result.ok:
        echo(f"❌ {title} 失败: {result.error}")
        return

    op = ir.get("op")
    data = result.data if isinstance(result.data, dict) else {}
    dur = f"({result.duration_ms:.1f}ms)"

    if op == "Encode":
        rid = data.get("inserted_id") or data.get("id")
        dim = data.get("embedding_dim")
        echo(f"✅ {title} -> id={rid} dim={dim} {dur}")
        return

    if op == "Retrieve":
        rows = []
        if isinstance(result.data, list):
            rows = result.data
        elif isinstance(result.data, dict):
            rows = result.data.get("rows", []) or []
        echo(f"✅ {title} -> {len(rows)} rows {dur}")
        return

    if op == "Summarize":
        summary = str(data.get("summary", ""))
        echo(f"✅ {title} -> summary {summary[:80]}{'…' if len(summary) > 80 else ''} {dur}")
        return

    affected = data.get("affected_rows") or data.get("updated_rows")
    if affected is not None:
        echo(f"✅ {title} -> affected={affected} {dur}")
    else:
        echo(f"✅ {title} {dur}")


def run_basic_demo(echo, engine) -> Dict[str, Any]:
    """Encode → Retrieve → Summarize quick check used by ``manage.py features``."""

    ops_log: list[IRRunResult] = []

    encode_ir = {
        "stage": "ENC",
        "op": "Encode",
        "args": {
            "payload": {
                "text": "这是一条用于功能自检的记忆，确认 Encode 是否正常。"
            },
            "tags": ["demo", "自检"],
            "type": "note",
            "source": "cli_helpers.basic_demo",
            "facets": {
                "subject": "CLI 快速体验",
                "topic": "系统自检",
            },
        },
    }
    result = execute_ir(engine, encode_ir)
    format_and_echo(echo, "Encode", encode_ir, result)
    ops_log.append(result)

    retrieve_ir = {
        "stage": "RET",
        "op": "Retrieve",
        "target": {
            "search": {
                "intent": {"query": "功能自检"},
                "overrides": {"k": 5},
                "limit": 5,
            }
        },
        "args": {"include": ["id", "text", "tags", "weight"]},
    }
    result = execute_ir(engine, retrieve_ir)
    format_and_echo(echo, "Retrieve", retrieve_ir, result)
    ops_log.append(result)

    summarize_ir = {
        "stage": "RET",
        "op": "Summarize",
        "target": {
            "filter": {
                "has_tags": ["demo"],
                "limit": 10,
            }
        },
        "args": {"focus": "功能演示回顾", "max_tokens": 120},
    }
    result = execute_ir(engine, summarize_ir)
    format_and_echo(echo, "Summarize", summarize_ir, result)
    ops_log.append(result)

    return {
        "mode": "basic",
        "operations": [entry.op for entry in ops_log],
        "total_ms": sum(entry.duration_ms for entry in ops_log),
        "encode_id": ops_log[0].data.get("inserted_id") if ops_log and ops_log[0].ok else None,
    }

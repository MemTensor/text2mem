import json
import sqlite3
import os

import pytest

from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.core.models import IR, SplitArgs, Target, Filters
from text2mem.services.models_service_mock import create_models_service


def _run_ir(adapter: SQLiteAdapter, ir: IR):
    # minimal runner for STO stage Split after a seeded encode
    return adapter.execute(ir)


@pytest.fixture()
def adapter(tmp_path):
    db_path = tmp_path / "t2m.db"
    # Use mock models service for deterministic tests
    service = create_models_service(mode="mock")
    ad = SQLiteAdapter(path=str(db_path), models_service=service)
    return ad


def test_workflow_op_split_by_sentences(adapter):
    # Seed a note
    seed_ir = IR(stage="ENC", op="Encode", args={
        "payload": {"text": "这是第一句。这里是第二句！还有第三句？这是第四句。"},
        "tags": ["doc", "long"],
        "type": "note",
    })
    adapter.execute(seed_ir)

    # Split by sentences
    split_ir = IR(
        stage="STO",
        op="Split",
        target={"filter": {"has_tags": ["long"], "limit": 100}},
        args={
            "strategy": "by_sentences",
        "params": {"by_sentences": {"lang": "zh", "max_sentences": 1}},
            "inherit_all": True,
        },
    )
    res = adapter.execute(split_ir)
    assert res.success
    data = res.data or {}
    # Expect we created multiple child entries
    results = data.get("results") or []
    assert results and results[0].get("split_count", 0) >= 2


def test_workflow_op_split_custom(adapter):
    # Seed a note
    seed_ir = IR(stage="ENC", op="Encode", args={
        "payload": {"text": "# 标题\n第一段内容……\n\n# 第二节\n第二段内容更长……\n\n# 第三节\n第三段内容。"},
        "tags": ["doc", "long"],
        "type": "note",
    })
    adapter.execute(seed_ir)

    # Split by custom (LLM structured)
    split_ir = IR(
        stage="STO",
        op="Split",
        target={"filter": {"has_tags": ["long"], "limit": 100}},
        args={
            "strategy": "custom",
            "params": {"custom": {"instruction": "请按标题切分，并为每段提供一个可选标题。保留原文内容。", "max_splits": 5}},
            "inherit_all": True,
        },
    )
    res = adapter.execute(split_ir)
    assert res.success
    data = res.data or {}
    results = data.get("results") or []
    assert results and results[0].get("split_count", 0) >= 1

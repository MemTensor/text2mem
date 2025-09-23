import json
import pytest
from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.services.models_service_mock import create_models_service
from text2mem.core.models import IR


@pytest.fixture()
def adapter():
    service = create_models_service(mode="mock")
    adp = SQLiteAdapter(":memory:", models_service=service)
    yield adp
    adp.close()


def test_encode_generates_embedding_meta(adapter):
    ir = IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {
            "payload": {"text": "hello embedding"},
            "type": "note",
            "tags": ["emb"],
            
        },
    })
    out = adapter.execute(ir)
    assert out.success
    d = out.data
    assert d.get("inserted_id")
    assert d.get("generated_embedding") is True
    assert d.get("embedding_dim")
    assert d.get("embedding_model")
    assert d.get("embedding_provider") in {"dummy", "openai", "ollama", "unknown", "mock"}


def test_retrieve_semantic_mode_filters_incompatible_vectors(adapter):
    # insert two notes
    for t in ["alpha", "beta"]:
        adapter.execute(IR.model_validate({
            "stage": "ENC",
            "op": "Encode",
            "args": {"payload": {"text": t}, "type": "note", "tags": ["sem"]},
        }))
    # semantic retrieve
    out = adapter.execute(IR.model_validate({
        "stage": "RET",
        "op": "Retrieve",
        "target": {"search": {"intent": {"query": "alpha"}, "overrides": {"k": 2}}},
        "args": {}
    }))
    assert out.success
    data = out.data
    assert data.get("mode") in {"semantic", "traditional"}
    assert isinstance(data.get("rows", []), list)


def test_get_table_stats_and_dump(adapter):
    # seed a row
    adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
    "args": {"payload": {"text": "stats"}, "type": "note"}
    }))
    stats = adapter.get_table_stats()
    assert isinstance(stats, dict)
    assert stats.get("total_rows") >= 1
    recent = adapter.dump_recent_rows(limit=2)
    assert isinstance(recent, list)


def test_optimize_and_db_info(adapter):
    res = adapter.optimize_database()
    assert isinstance(res, dict)
    info = adapter.get_database_info()
    assert isinstance(info, dict)
    assert "tables" in info

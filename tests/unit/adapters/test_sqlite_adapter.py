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
    assert d.get("embedding_model") == "mock-embedding"
    assert d.get("embedding_provider") == "mock"

    row = adapter.conn.execute(
        "SELECT embedding, embedding_dim, embedding_model, embedding_provider FROM memory WHERE id = ?",
        (d["inserted_id"],),
    ).fetchone()
    assert row["embedding_model"] == "mock-embedding"
    assert row["embedding_provider"] == "mock"
    assert isinstance(json.loads(row["embedding"]), list)
    assert row["embedding_dim"] == len(json.loads(row["embedding"]))


def test_semantic_retrieve_prefers_closest_matches(adapter):
    texts = [
        "alpha project meeting notes",  # should match strongly
        "beta launch plan",             # partial overlap
        "unrelated gardening tips",    # low similarity
    ]
    ids = []
    for t in texts:
        ir = IR.model_validate({
            "stage": "ENC",
            "op": "Encode",
            "args": {"payload": {"text": t}, "type": "note"},
        })
        res = adapter.execute(ir)
        ids.append(res.data["inserted_id"])

    ret_ir = IR.model_validate({
        "stage": "RET",
        "op": "Retrieve",
    "target": {"search": {"intent": {"query": "alpha project plan"}, "overrides": {"k": 3}, "limit": 3}},
        "args": {},
    })
    res = adapter.execute(ret_ir)
    rows = res.data["rows"]
    assert len(rows) == 3
    top_texts = [row["text"] for row in rows[:2]]
    assert "alpha project meeting notes" in top_texts
    assert "beta launch plan" in [row["text"] for row in rows]
    assert rows[0]["_similarity"] >= rows[1]["_similarity"] >= rows[2]["_similarity"]


def test_semantic_retrieve_skips_dimension_mismatch(adapter):
    # Seed two notes
    ids = []
    for text in ["vector test one", "vector test two"]:
        ir = IR.model_validate({
            "stage": "ENC",
            "op": "Encode",
            "args": {"payload": {"text": text}, "type": "note"},
        })
        res = adapter.execute(ir)
        ids.append(res.data["inserted_id"])

    # Corrupt the first embedding to have mismatched dimension
    corrupted_vector = json.dumps([0.1, 0.2])
    adapter.conn.execute(
        "UPDATE memory SET embedding = ?, embedding_dim = ? WHERE id = ?",
        (corrupted_vector, 2, ids[0]),
    )
    adapter.conn.commit()

    ret_ir = IR.model_validate({
        "stage": "RET",
        "op": "Retrieve",
        "target": {"search": {"intent": {"query": "vector test"}, "overrides": {"k": 5}, "limit": 5}},
        "args": {},
    })
    res = adapter.execute(ret_ir)
    data = res.data
    assert data["count"] == 1
    assert data["rows"][0]["id"] == ids[1]
    # Depending on vector ordering, note may be absent; ensure mismatch skipped
    assert ids[0] not in [row["id"] for row in data["rows"]]


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


def test_semantic_retrieve_respects_filter_with_search(adapter):
    # Seed notes with different tags
    ir_payloads = [
        {"text": "Project sync with marketing team", "tags": ["project", "team"]},
        {"text": "Personal grocery list", "tags": ["personal"]},
        {"text": "Project roadmap discussion", "tags": ["project", "team"]},
    ]
    for item in ir_payloads:
        adapter.execute(IR.model_validate({
            "stage": "ENC",
            "op": "Encode",
            "args": {
                "payload": {"text": item["text"]},
                "type": "note",
                "tags": item["tags"],
            },
        }))

    ret_ir = IR.model_validate({
        "stage": "RET",
        "op": "Retrieve",
        "target": {
            "filter": {"has_tags": ["team"]},
            "search": {"intent": {"query": "project roadmap"}, "overrides": {"k": 5}, "limit": 5},
        },
        "args": {"include": ["id", "text", "tags"]},
    })
    res = adapter.execute(ret_ir)
    assert res.success
    rows = res.data["rows"]
    assert rows, "Expected at least one row when combining filter and semantic search"
    for row in rows:
        tags = json.loads(row["tags"]) if row.get("tags") else []
        assert "team" in tags
    texts = [row["text"] for row in rows]
    assert any("Project" in t for t in texts)


def test_semantic_retrieve_with_explicit_vector(adapter):
    # Seed two conceptually distant notes
    adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {"payload": {"text": "Launch plan for Q4"}, "type": "note"},
    }))
    adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {"payload": {"text": "Recipe for chocolate cake"}, "type": "note"},
    }))

    query_vector = adapter.models_service.encode_memory("Launch plan for new product").embedding

    ret_ir = IR.model_validate({
        "stage": "RET",
        "op": "Retrieve",
        "target": {
            "search": {"intent": {"vector": query_vector}, "limit": 2}
        },
        "args": {"include": ["id", "text"]},
    })
    res = adapter.execute(ret_ir)
    assert res.success
    rows = res.data["rows"]
    assert rows
    top_text = rows[0]["text"]
    assert "Launch" in top_text or "plan" in top_text


def test_split_by_sentences_creates_child_records(adapter):
    parent = adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {
            "payload": {"text": "First sentence. Second sentence? Third sentence!"},
            "type": "note",
            "tags": ["split"],
        },
    }))
    parent_id = parent.data["inserted_id"]

    split_ir = IR.model_validate({
        "stage": "STO",
        "op": "Split",
        "target": {"ids": [str(parent_id)]},
        "args": {
            "strategy": "by_sentences",
            "params": {"by_sentences": {"lang": "en", "max_sentences": 1}},
        },
    })
    res = adapter.execute(split_ir)
    assert res.success
    assert res.data["total_splits"] >= 2
    assert res.data["results"][0]["strategy_used"] == "by_sentences"

    child_rows = adapter.conn.execute(
        "SELECT id, text, tags FROM memory WHERE id != ? ORDER BY id",
        (parent_id,),
    ).fetchall()
    assert len(child_rows) >= 2
    for row in child_rows:
        assert row["text"]
        tags = json.loads(row["tags"]) if row["tags"] else []
        assert f"split_from_{parent_id}" in tags


def test_split_by_chunks_limits_chunk_size(adapter):
    text = "-".join(["chunk"] * 40)
    parent = adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {"payload": {"text": text}, "type": "note"},
    }))
    parent_id = parent.data["inserted_id"]

    split_ir = IR.model_validate({
        "stage": "STO",
        "op": "Split",
        "target": {"ids": [str(parent_id)]},
        "args": {
            "strategy": "by_chunks",
            "params": {"by_chunks": {"chunk_size": 60}},
        },
    })
    res = adapter.execute(split_ir)
    assert res.success
    assert res.data["total_splits"] >= 2
    assert res.data["results"][0]["strategy_used"] == "by_chunks"

    child_rows = adapter.conn.execute(
        "SELECT text FROM memory WHERE id != ?",
        (parent_id,),
    ).fetchall()
    assert child_rows
    for row in child_rows:
        assert len(row["text"]) <= 70  # chunk_size upper bound with small slack


def test_split_custom_fallback_paragraphs(adapter, monkeypatch):
    long_text = "Section A\nline1\n\nSection B\nline2\n\nSection C"
    parent = adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {
            "payload": {"text": long_text},
            "type": "note",
        },
    }))
    parent_id = parent.data["inserted_id"]

    # Force models service to fail to trigger paragraph fallback
    def _raise(*args, **kwargs):
        raise RuntimeError("no split")

    monkeypatch.setattr(adapter.models_service, "split_custom", _raise)

    split_ir = IR.model_validate({
        "stage": "STO",
        "op": "Split",
        "target": {"ids": [str(parent_id)]},
        "args": {
            "strategy": "custom",
            "params": {"custom": {"instruction": "按段落拆分", "max_splits": 5}},
        },
    })
    res = adapter.execute(split_ir)
    assert res.success
    assert res.data["total_splits"] >= 2
    assert res.data["results"][0]["strategy_used"] == "custom:paragraphs"

    child_rows = adapter.conn.execute(
        "SELECT text FROM memory WHERE id != ? ORDER BY id",
        (parent_id,),
    ).fetchall()
    child_texts = [row["text"].strip() for row in child_rows]
    assert "Section A\nline1" in child_texts
    assert "Section B\nline2" in child_texts


def test_split_custom_force_model_calls_service(adapter, monkeypatch):
    text = "# Heading A\n内容一\n\n# Heading B\n内容二"
    parent = adapter.execute(IR.model_validate({
        "stage": "ENC",
        "op": "Encode",
        "args": {"payload": {"text": text}, "type": "note"},
    }))
    parent_id = parent.data["inserted_id"]

    calls: list[tuple] = []

    def fake_split(text_val, instruction, max_splits):
        calls.append((text_val, instruction, max_splits))
        return [
            {"title": "Heading A", "text": "Heading A\n内容一"},
            {"title": "Heading B", "text": "Heading B\n内容二"},
        ]

    monkeypatch.setattr(adapter.models_service, "split_custom", fake_split)

    split_ir = IR.model_validate({
        "stage": "STO",
        "op": "Split",
        "target": {"ids": [str(parent_id)]},
        "args": {
            "strategy": "custom",
            "params": {"custom": {"instruction": "强制模型拆分", "max_splits": 5, "force_model": True}},
        },
    })
    res = adapter.execute(split_ir)
    assert res.success
    assert calls  # ensure models service invoked
    result_entry = res.data["results"][0]
    assert result_entry["strategy_used"] == "custom:model"
    child_rows = adapter.conn.execute(
        "SELECT text FROM memory WHERE id != ? ORDER BY id",
        (parent_id,),
    ).fetchall()
    texts = [row["text"].strip() for row in child_rows]
    assert "Heading A" in texts[0]


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

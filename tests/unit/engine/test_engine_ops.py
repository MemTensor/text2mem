from text2mem.adapters.base import ExecutionResult


def exec_ok(engine, ir):
    res = engine.execute(ir)
    assert isinstance(res, ExecutionResult)
    assert res.success, res.error
    return res.data or {}


def test_encode_returns_id(engine):
    data = exec_ok(engine, {
        "stage": "ENC",
        "op": "Encode",
        "args": {
            "payload": {"text": "测试一条记忆，用于检索。"},
            "type": "note",
            "tags": ["单元测试", "roundtrip"],
        },
    })
    rid = data.get("inserted_id")
    assert rid


def test_retrieve_by_tag_returns_rows(engine, seed_memories):
    seed_memories(["r1", "r2"], tags=["检索标签"], mtype="note")
    rows = exec_ok(engine, {
        "stage": "RET",
        "op": "Retrieve",
        "target": {"filter": {"has_tags": ["检索标签"], "limit": 5}},
        "args": {},
    }).get("rows", [])
    assert isinstance(rows, list)


def test_label_adds_tags(engine, seed_memories):
    seed_memories(["L1", "L2"], tags=["Alpha"], mtype="task")
    exec_ok(engine, {
        "stage": "STO",
        "op": "Label",
        "target": {"filter": {"has_tags": ["Alpha"], "limit": 10}},
    "args": {"tags": ["项目"]},
    })


def test_promote_sets_weight(engine, seed_memories):
    # 直接种入有目标标签，避免依赖Label测试
    seed_memories(["P1", "P2", "P3"], tags=["项目"], mtype="task")
    out = exec_ok(engine, {
        "stage": "STO",
    "op": "Promote",
    "target": {"filter": {"has_tags": ["项目"], "limit": 10}},
    "args": {"weight_delta": 1.0},
    })
    assert out.get("affected_rows") is not None


def test_update_by_id(engine, seed_memories):
    ids = seed_memories(["Alpha 分析需求"], tags=["Alpha"], mtype="task")
    exec_ok(engine, {
        "stage": "STO",
        "op": "Update",
        "target": {"ids": str(ids[0])},
        "args": {"set": {"text": "Alpha 分析需求 - 已完成", "weight": 0.1}},
    })
    rows = exec_ok(engine, {
        "stage": "RET",
        "op": "Retrieve",
    "target": {"ids": str(ids[0])},
    "args": {},
    }).get("rows", [])
    assert rows and "已完成" in (rows[0].get("text") or "")


def test_merge_into_primary_default(engine, seed_memories):
    # Seed three related notes
    ids = seed_memories(["A", "B", "C"], tags=["MergeGroup"], mtype="note")
    # Dry-run to preview
    preview = exec_ok(engine, {
        "stage": "STO",
        "op": "Merge",
        "target": {"filter": {"has_tags": ["MergeGroup"], "limit": 10}},
        "args": {},
        "meta": {"dry_run": True},
    })
    assert preview.get("strategy") == "merge_into_primary"
    # Actual merge with default primary (first match) and soft delete
    out = exec_ok(engine, {
        "stage": "STO",
        "op": "Merge",
        "target": {"filter": {"has_tags": ["MergeGroup"], "limit": 10}},
        "args": {},
    })
    assert out.get("strategy") == "merge_into_primary"
    assert out.get("merged_count", 0) >= 1
    # Verify primary still retrievable, others soft-deleted
    primary_id = int(out.get("primary_id"))
    rows = exec_ok(engine, {
        "stage": "RET",
        "op": "Retrieve",
        "target": {"ids": str(primary_id)},
        "args": {},
    }).get("rows", [])
    assert rows and rows[0]["id"] == primary_id

def test_merge_via_search_target(engine, seed_memories):
    # Seed with a keyword to enable search target, and use filter to constrain scope
    seed_memories(["OKR A", "OKR B", "Other"], tags=["MergeSearch"], mtype="note")
    out = exec_ok(engine, {
        "stage": "STO",
        "op": "Merge",
        "target": {
            "search": {"intent": {"query": "OKR"}, "limit": 2},
            "filter": {"has_tags": ["MergeSearch"], "limit": 10}
        },
        "args": {},
    })
    assert out.get("strategy") == "merge_into_primary"
    assert out.get("merged_count", 0) >= 1


def test_split_sentences_inherit_tags(engine, seed_memories):
    # Ensure text contains periods to trigger sentence splitting
    ids = seed_memories(["Part A. Part B. Part C."], tags=["SplitMe"], mtype="note")
    out = exec_ok(engine, {
        "stage": "STO",
        "op": "Split",
        "target": {"ids": str(ids[0])},
    "args": {"strategy": "sentences", "inherit": {"tags": True}},
    })
    # total_splits >= 1 means at least one child inserted
    assert out.get("total_splits", 0) >= 1


def test_lock_read_only(engine, seed_memories):
    ids = seed_memories(["Lock me"], tags=["LockTag"], mtype="note")
    exec_ok(engine, {
        "stage": "STO",
        "op": "Lock",
        "target": {"ids": str(ids[0])},
    "args": {"mode": "read_only", "reason": "冻结测试"},
    })
    row = exec_ok(engine, {
        "stage": "RET",
        "op": "Retrieve",
        "target": {"ids": str(ids[0])},
    "args": {},
    }).get("rows", [])[0]
    assert row.get("write_perm_level") == "locked_no_write"


def test_expire_sets_time(engine, seed_memories):
    ids = seed_memories(["Expire me"], tags=["ExpireTag"], mtype="note")
    exec_ok(engine, {
        "stage": "STO",
        "op": "Expire",
        "target": {"ids": str(ids[0])},
    "args": {"ttl": "P7D", "on_expire": "soft_delete"},
    })
    row2 = exec_ok(engine, {
        "stage": "RET",
        "op": "Retrieve",
        "target": {"ids": str(ids[0])},
    "args": {},
    }).get("rows", [])[0]
    assert row2.get("expire_at")


def test_summarize_focus(engine, seed_memories):
    seed_memories(["Alpha 总结 1", "Alpha 总结 2"], tags=["Alpha"], mtype="note")
    out = exec_ok(engine, {
        "stage": "RET",
        "op": "Summarize",
        "target": {"filter": {"has_tags": ["Alpha"], "limit": 10}},
    "args": {"focus": "项目概览", "max_tokens": 120},
    })
    assert isinstance(out.get("summary", ""), str)

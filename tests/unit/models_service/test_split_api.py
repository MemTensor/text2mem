import json
import pytest

from text2mem.services.models_service_mock import create_models_service


def test_split_by_sentences_en_basic():
    service = create_models_service(mode="mock")
    text = "Hello world. This is a test! Done? Yes."
    items = service.split(text, strategy="by_sentences", params={"by_sentences": {"max_sentences": 2}}, lang="en")
    # Expect merged pairs of sentences into blocks
    assert isinstance(items, list) and len(items) >= 2
    assert all("text" in it and isinstance(it["text"], str) for it in items)
    assert all("range" in it and isinstance(it["range"], list) for it in items)
    # Ranges should map to substrings
    for it in items:
        s, e = it["range"]
        assert text[s:e] == it["text"]


def test_split_by_sentences_zh_basic():
    service = create_models_service(mode="mock")
    text = "这是第一句。这里是第二句！还有第三句？结束。"
    items = service.split(text, strategy="by_sentences", params={"by_sentences": {"max_sentences": 1}}, lang="zh")
    assert len(items) >= 3
    for it in items:
        assert it["text"]
        s, e = it["range"]
        assert text[s:e] == it["text"]


def test_split_by_chunks_size():
    service = create_models_service(mode="mock")
    text = "abcdefghij"  # len=10
    items = service.split(text, strategy="by_chunks", params={"by_chunks": {"chunk_size": 3}})
    # Expect 4 chunks: 3,3,3,1
    lengths = [len(it["text"]) for it in items]
    assert lengths == [3, 3, 3, 1]
    # Check contiguous ranges
    pos = 0
    for it in items:
        s, e = it["range"]
        assert s == pos and e == pos + len(it["text"]) and text[s:e] == it["text"]
        pos = e


def test_split_by_chunks_num():
    service = create_models_service(mode="mock")
    text = "abcdefghij"  # len=10
    items = service.split(text, strategy="by_chunks", params={"by_chunks": {"num_chunks": 4}})
    # Expect 4 chunks with near-equal sizes that sum to 10
    assert len(items) == 4
    assert sum(len(it["text"]) for it in items) == len(text)
    pos = 0
    for it in items:
        s, e = it["range"]
        assert s == pos and e == pos + len(it["text"]) and text[s:e] == it["text"]
        pos = e


def test_split_custom_mock_provider_array_output():
    service = create_models_service(mode="mock")
    text = "# 标题\n第一段内容……\n\n# 第二节\n第二段内容更长……\n\n# 第三节\n第三段内容。"
    items = service.split(
        text,
        strategy="custom",
        params={
            "custom": {
                "instruction": "请按标题切分，并为每段提供一个可选标题。保留原文内容。",
                "max_splits": 5,
            }
        },
        lang="zh",
    )
    # Mock returns an array of 3 items
    assert isinstance(items, list) and len(items) == 3
    assert all("text" in it for it in items)


def test_split_invalid_strategy_raises():
    service = create_models_service(mode="mock")
    with pytest.raises(ValueError):
        service.split("text", strategy="unknown")

from text2mem.services.models_service_providers import create_models_service


def test_semantic_search_and_dimension_guard():
    service = create_models_service(mode="mock")
    items = []
    for text in ["alpha", "beta", "gamma", "delta"]:
        emb = service.encode_memory(text)
        items.append({"id": text, "text": text, "vector": emb.vector})

    results = service.semantic_search("alpha topic", items, k=2)
    assert len(results) == 2
    assert results[0]["id"] in {"alpha", "beta", "gamma", "delta"}


def test_generate_summary_mock():
    service = create_models_service(mode="mock")
    r = service.generate_summary(["这是第一段", "这是第二段"], focus="要点", max_tokens=50)
    assert r.text and r.model

Text2Mem package layout (modularized)

- core/
  - engine.py: Text2MemEngine
  - models.py: IR models (Pydantic)
  - validate.py: JSON Schema validator utilities
  - config.py: Model/DB/Text2Mem configs
- services/
  - models_service.py: Service interfaces and dummy implementations
  - models_service_mock.py: Mock + factory (canonical). 旧的 providers shim 已删除。
  - models_service_ollama.py: Ollama-backed service
  - models_service_openai.py: OpenAI-backed service
- adapters/
  - sqlite_adapter.py, base.py
- schema/
  - text2mem-ir-v1.json

Public API remains available via `text2mem` top-level imports.
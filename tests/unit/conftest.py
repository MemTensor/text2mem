"""
Shared pytest configuration for unit tests.
Ensures project root is on sys.path and provides common fixtures.
"""
import sys
from pathlib import Path
import pytest

# Add project root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from text2mem.services.models_service_providers import create_models_service
from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.core.engine import Text2MemEngine


@pytest.fixture()
def mock_service():
    return create_models_service(mode="mock")


@pytest.fixture()
def adapter(mock_service):
    adp = SQLiteAdapter(":memory:", models_service=mock_service)
    yield adp
    adp.close()


@pytest.fixture()
def engine(mock_service, adapter):
    return Text2MemEngine(adapter=adapter, models_service=mock_service)


@pytest.fixture()
def seed_memories(engine):
    def _seed(texts, tags=None, mtype="note"):
        ids = []
        for t in texts:
            ir = {
                "stage": "ENC",
                "op": "Encode",
                "args": {"payload": {"text": t}, "type": mtype, "tags": tags or []},
            }
            res = engine.execute(ir)
            assert res.success
            ids.append(res.data.get("inserted_id"))
        return ids
    return _seed


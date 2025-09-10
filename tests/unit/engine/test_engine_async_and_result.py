import asyncio

from text2mem.adapters.base import ExecutionResult


async def _run_async(engine):
    ir = {
        "stage": "ENC",
        "op": "Encode",
        "args": {"payload": {"text": "async 测试"}, "tags": ["async"]}
    }
    return await engine.process_ir(ir)


def test_execution_result_bool_truthiness():
    ok = ExecutionResult(success=True, data={"x": 1})
    bad = ExecutionResult(success=False, error="xx")
    assert bool(ok) is True
    assert bool(bad) is False


def test_engine_async_process_ir(engine):
    res = asyncio.run(_run_async(engine))
    assert isinstance(res, ExecutionResult)
    assert res.success

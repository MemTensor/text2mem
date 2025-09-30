import json
from pathlib import Path

from text2mem.core.validate import IRValidator, validate_ir


def test_irvalidator_valid_and_invalid():
    # This test lives at tests/unit/validate/, repo root is 3 levels up
    root = Path(__file__).resolve().parents[3]
    schema_path = root / "text2mem" / "schema" / "text2mem-ir-v1.json"
    v = IRValidator(schema_path)

    valid_ir = {
        "stage": "ENC",
        "op": "Encode",
        "args": {"payload": {"text": "hello"}}
    }
    assert v.is_valid(valid_ir)
    v.validate(valid_ir)  # should not raise

    invalid_ir = {"stage": "STO", "op": "Encode", "args": {"payload": {}}}
    # is_valid False and validate raises
    assert not v.is_valid(invalid_ir)
    try:
        v.validate(invalid_ir)
        raised = False
    except Exception:
        raised = True
    assert raised


def test_validate_ir_helper():
    # This test lives at tests/unit/validate/, repo root is 3 levels up
    root = Path(__file__).resolve().parents[3]
    schema = json.loads((root / "text2mem" / "schema" / "text2mem-ir-v1.json").read_text(encoding="utf-8"))

    ok = {
        "stage": "RET",
        "op": "Retrieve",
        "target": {"ids": "abc"},
        "args": {}
    }
    res = validate_ir(ok, schema)
    assert res.valid

    bad = {"stage": "RET", "op": "Retrieve", "target": {"ids": "abc"}, "args": {"include": ["unknown_field"]}}
    res2 = validate_ir(bad, schema)
    assert not res2.valid and res2.error

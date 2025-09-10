import json
from pathlib import Path

from text2mem.core.validate import IRValidator


def test_schema_load_and_validate_examples():
    # This test lives at tests/unit/schema/, repo root is 3 levels up
    root = Path(__file__).resolve().parents[3]
    schema_path = root / "text2mem" / "schema" / "text2mem-ir-v1_3.json"
    validator = IRValidator(schema_path)

    # Examples are in the root examples directory, not in text2mem/examples
    examples_dir = root / "examples" / "ir_operations"
    example_files = sorted(p for p in examples_dir.glob("sample_ir_*.json"))
    assert example_files, "No example IR files found"

    for f in example_files:
        content = f.read_text(encoding="utf-8").strip()
        if not content:
            # skip placeholder/empty example files
            continue
        data = json.loads(content)
        # some files may contain a single IR or a list
        if isinstance(data, list):
            for ir in data:
                assert validator.is_valid(ir), f"Invalid IR in {f.name}: {ir}"
        else:
            assert validator.is_valid(data), f"Invalid IR in {f.name}: {data}"

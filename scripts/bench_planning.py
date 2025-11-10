"""Schema validation helper for planning IR JSONL files.

This lightweight tool validates each JSON line against the Text2Mem IR v1
schema. It mirrors the behaviour expected by ``manage.py bench-planning`` and
keeps the implementation decoupled from the CLI entrypoint.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from jsonschema import Draft202012Validator


@dataclass
class ValidationIssue:
    line_no: int
    message: str
    json_path: str

    def to_dict(self) -> dict[str, Any]:
        return {"line": self.line_no, "json_path": self.json_path, "message": self.message}


def load_schema(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_jsonl(input_path: Path, validator: Draft202012Validator) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for idx, raw in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(idx, f"JSON parsing failed: {exc}", json_path="<root>"))
            continue
        errors = list(validator.iter_errors(payload))
        for err in errors:
            path = getattr(err, "json_path", "") or "/".join(str(p) for p in err.path)
            issues.append(ValidationIssue(idx, err.message, path or "<root>"))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate planning IR JSONL against schema.")
    parser.add_argument("--input", required=True, help="Path to JSONL file containing planning IRs")
    parser.add_argument("--schema", default="text2mem/schema/text2mem-ir-v1.json", help="Schema file path")
    parser.add_argument("--out", default=None, help="Optional path to save validation report (JSON)")
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    schema_path = Path(args.schema).expanduser().resolve()

    if not input_path.exists():
        raise SystemExit(f"❌ Input file does not exist: {input_path}")
    if not schema_path.exists():
        raise SystemExit(f"❌ Schema file does not exist: {schema_path}")

    validator = load_schema(schema_path)
    issues = validate_jsonl(input_path, validator)

    if issues:
        print(f"❌ Validation failed {len(issues)}  entries do not conform to schema")
    else:
        print("✅ Validation passed, all entries meet schema")

    if args.out:
        report = {
            "input": str(input_path),
            "schema": str(schema_path),
            "issues": [issue.to_dict() for issue in issues],
            "total_issues": len(issues),
        }
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📝 Validation report written to {args.out}")

    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())

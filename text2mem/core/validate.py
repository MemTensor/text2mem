# moved from text2mem/validate.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from jsonschema import Draft202012Validator, exceptions
import json
from pathlib import Path
from dataclasses import dataclass


class IRValidator:
    def __init__(self, schema_path: str | Path):
        try:
            self.schema_path = Path(schema_path)
            self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
            self.validator = Draft202012Validator(self.schema)
        except json.JSONDecodeError as e:
            raise ValueError(f"Schema file parsing error: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

    def validate(self, ir: Dict[str, Any]) -> None:
        try:
            self.validator.validate(ir)
        except exceptions.ValidationError as e:
            path = " -> ".join(str(p) for p in e.path) if e.path else "root"
            message = f"Validation failed (location: {path}): {e.message}"
            raise exceptions.ValidationError(
                message,
                validator=e.validator,
                validator_value=e.validator_value,
                instance=e.instance,
                schema_path=e.schema_path,
                schema=e.schema,
                cause=e.cause,
            )

    def is_valid(self, ir: Dict[str, Any]) -> bool:
        return self.validator.is_valid(ir)

    def iter_errors(self, ir: Dict[str, Any]) -> List[str]:
        errors = []
        for error in self.validator.iter_errors(ir):
            path = " -> ".join(str(p) for p in error.path) if error.path else "root"
            errors.append(f"Validation error (location: {path}): {error.message}")
        return errors


@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str] = None


def validate_ir(ir: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
    try:
        if isinstance(schema, dict):
            validator = Draft202012Validator(schema)
            if validator.is_valid(ir):
                return ValidationResult(valid=True)
            else:
                errors = []
                for error in validator.iter_errors(ir):
                    path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                    errors.append(f"Validation error (location: {path}): {error.message}")
                error_msg = "; ".join(errors) if errors else "Unknown validation error"
                return ValidationResult(valid=False, error=error_msg)
        else:
            validator = IRValidator(schema)
            if validator.is_valid(ir):
                return ValidationResult(valid=True)
            else:
                errors = validator.iter_errors(ir)
                error_msg = "; ".join(errors) if errors else "Unknown validation error"
                return ValidationResult(valid=False, error=error_msg)
    except Exception as e:
        return ValidationResult(valid=False, error=f"Validation process error: {str(e)}")

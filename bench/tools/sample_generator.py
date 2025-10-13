"""Test sample generator for Text2Mem Bench.

This tool helps generate test samples following the benchmark schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


@dataclass
class SampleTemplate:
    """Template for generating benchmark samples."""
    
    # Metadata
    id: str
    lang: Literal["zh", "en"] = "zh"
    instruction_type: Literal["direct", "indirect", "implicit"] = "direct"
    structure: Literal["single", "combo", "workflow"] = "single"
    layer: Literal["exec", "both"] = "exec"
    
    # Content
    nl_text: str = ""
    prerequisites: List[Dict[str, Any]] = field(default_factory=list)  # 前置指令（IR格式）
    schema_list: List[Dict[str, Any]] = field(default_factory=list)
    init_db: str = "DB-100"
    
    # Expectations
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    ranking: Optional[Dict[str, Any]] = None
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    
    # Documentation
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to benchmark sample format."""
        result = {
            "id": self.id,
            "class": {
                "instruction": self.instruction_type,
                "structure": self.structure,
                "lang": self.lang,
                "layer": self.layer,
            },
            "nl": {self.lang: self.nl_text},
            "schema_list": self.schema_list,
            "init_db": self.init_db,
            "expected": {
                "assertions": self.assertions,
                "ranking": self.ranking,
                "triggers": self.triggers,
            },
            "notes": self.notes,
        }
        
        # Only include prerequisites if not empty
        if self.prerequisites:
            result["prerequisites"] = self.prerequisites
        
        return result
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SampleBuilder:
    """Fluent builder for creating test samples."""
    
    def __init__(self, sample_id: str):
        self.template = SampleTemplate(id=sample_id)
    
    def set_metadata(
        self,
        lang: Literal["zh", "en"] = "zh",
        instruction_type: Literal["direct", "indirect", "implicit"] = "direct",
        structure: Literal["single", "combo", "workflow"] = "single",
        layer: Literal["exec", "both"] = "exec",
    ) -> "SampleBuilder":
        """Set sample classification metadata."""
        self.template.lang = lang
        self.template.instruction_type = instruction_type
        self.template.structure = structure
        self.template.layer = layer
        return self
    
    def set_nl(self, text: str) -> "SampleBuilder":
        """Set natural language description."""
        self.template.nl_text = text
        return self
    
    def set_db(self, db_name: str) -> "SampleBuilder":
        """Set initial database snapshot."""
        self.template.init_db = db_name
        return self
    
    def add_encode(
        self,
        text: str,
        type: str = "note",
        tags: Optional[List[str]] = None,
        facets: Optional[Dict[str, Any]] = None,
        weight: Optional[float] = None,
        **kwargs: Any,
    ) -> "SampleBuilder":
        """Add an Encode operation."""
        payload = {
            "text": text,
        }
        
        # Build args
        args = {
            "payload": payload,
            "type": type,
        }
        
        if tags:
            args["tags"] = tags
        if facets:
            args["facets"] = facets
        if weight is not None:
            args["weight"] = weight
        
        # Add any additional kwargs to args (not payload)
        for key, value in kwargs.items():
            if key not in args and key not in payload:
                args[key] = value
        
        self.template.schema_list.append({
            "stage": "ENC",
            "op": "Encode",
            "args": args,
        })
        return self
    
    def add_retrieve(
        self,
        query: str,
        limit: int = 5,
        include: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> "SampleBuilder":
        """Add a Retrieve operation."""
        target = {
            "search": {
                "intent": {"query": query},
                "limit": limit,
            }
        }
        if filters:
            target["search"]["filters"] = filters
        
        args = {}
        if include:
            args["include"] = include
        
        self.template.schema_list.append({
            "stage": "RET",
            "op": "Retrieve",
            "target": target,
            "args": args,
        })
        return self
    
    def add_update(
        self,
        ids: List[Any],
        updates: Dict[str, Any],
    ) -> "SampleBuilder":
        """Add an Update operation."""
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Update",
            "target": {"ids": [str(id) for id in ids]},
            "args": {"set": updates},  # Changed from updates to set
        })
        return self
    
    def add_label(
        self,
        ids: List[Any],
        tags: Optional[List[str]] = None,
        facets: Optional[Dict[str, Any]] = None,
    ) -> "SampleBuilder":
        """Add a Label operation."""
        args = {}
        if tags:
            args["tags"] = tags
        if facets:
            args["facets"] = facets
        
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Label",
            "target": {"ids": [str(id) for id in ids]},
            "args": args,
        })
        return self
    
    def add_promote(self, ids: List[Any], weight: float) -> "SampleBuilder":
        """Add a Promote operation."""
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Promote",
            "target": {"ids": [str(id) for id in ids]},
            "args": {"weight": weight},
        })
        return self
    
    def add_demote(self, ids: List[Any], weight: float) -> "SampleBuilder":
        """Add a Demote operation."""
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Demote",
            "target": {"ids": [str(id) for id in ids]},
            "args": {"weight": weight},
        })
        return self
    
    def add_delete(self, ids: List[Any], soft: bool = True) -> "SampleBuilder":
        """Add a Delete operation."""
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Delete",
            "target": {"ids": [str(id) for id in ids]},
            "args": {"soft": soft},
        })
        return self
    
    def add_expire(
        self,
        ids: List[Any],
        ttl: str,
        on_expire: str = "soft_delete",
        reason: Optional[str] = None,
    ) -> "SampleBuilder":
        """Add an Expire operation."""
        args = {
            "ttl": ttl,
            "on_expire": on_expire,
        }
        if reason:
            args["reason"] = reason
        
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Expire",
            "target": {"ids": [str(id) for id in ids]},
            "args": args,
        })
        return self
    
    def add_lock(
        self,
        ids: List[Any],
        mode: str = "read_only",
        reason: Optional[str] = None,
        policy: Optional[Dict[str, Any]] = None,
    ) -> "SampleBuilder":
        """Add a Lock operation."""
        args = {"mode": mode}
        if reason:
            args["reason"] = reason
        if policy:
            args["policy"] = policy
        
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Lock",
            "target": {"ids": [str(id) for id in ids]},
            "args": args,
        })
        return self
    
    def add_merge(
        self,
        source_ids: List[Any],
        strategy: str = "concat",
        keep_sources: bool = False,
    ) -> "SampleBuilder":
        """Add a Merge operation."""
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Merge",
            "target": {"ids": [str(id) for id in source_ids]},
            "args": {
                "strategy": strategy,
                "keep_sources": keep_sources,
            },
        })
        return self
    
    def add_split(
        self,
        memory_id: Any,
        strategy: str = "semantic",
    ) -> "SampleBuilder":
        """Add a Split operation."""
        self.template.schema_list.append({
            "stage": "STO",
            "op": "Split",
            "target": {"ids": [str(memory_id)]},
            "args": {"strategy": strategy},
        })
        return self
    
    def add_summarize(
        self,
        query: Optional[str] = None,
        ids: Optional[List[Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> "SampleBuilder":
        """Add a Summarize operation."""
        target: Dict[str, Any] = {}
        if query:
            target["search"] = {
                "intent": {"query": query},
                "limit": 10,
            }
            if filters:
                target["search"]["filters"] = filters
        elif ids:
            target["ids"] = [str(id) for id in ids]
        
        self.template.schema_list.append({
            "stage": "RET",
            "op": "Summarize",
            "target": target,
            "args": {},
        })
        return self
    
    def add_assertion(
        self,
        name: str,
        from_table: str,
        where: List[str],
        agg: str = "count",
        value_expr: str = "*",
        expect_op: str = "==",
        expect_value: Any = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> "SampleBuilder":
        """Add an assertion to validate results."""
        assertion = {
            "name": name,
            "select": {
                "from": from_table,
                "where": where,
                "agg": agg,
            },
            "expect": {
                "op": expect_op,
                "value": expect_value,
            },
        }
        
        if value_expr != "*":
            assertion["select"]["value"] = value_expr
        
        if params:
            assertion["params"] = params
        
        self.template.assertions.append(assertion)
        return self
    
    def set_ranking(
        self,
        query: str,
        gold_ids: List[str],
        topk: int = 5,
        allow_extra: bool = True,
        min_hits: Optional[int] = None,
        include: Optional[List[str]] = None,
    ) -> "SampleBuilder":
        """Set ranking evaluation criteria."""
        ranking = {
            "query": query,
            "gold_ids": gold_ids,
            "topk": topk,
            "allow_extra": allow_extra,
        }
        
        if min_hits is not None:
            ranking["min_hits"] = min_hits
        
        if include:
            ranking["include"] = include
        
        self.template.ranking = ranking
        return self
    
    def add_trigger(
        self,
        advance: str,
        assertions: List[Dict[str, Any]],
    ) -> "SampleBuilder":
        """Add a time-based trigger with assertions."""
        self.template.triggers.append({
            "advance": advance,
            "assertions": assertions,
        })
        return self
    
    def add_prerequisite(self, ir: Dict[str, Any]) -> "SampleBuilder":
        """Add a prerequisite IR instruction.
        
        Prerequisites are executed before the main schema_list to set up test data.
        They should be standard IR format (stage, op, args, target, etc.)
        
        Args:
            ir: Complete IR instruction in JSON Schema format
            
        Example:
            builder.add_prerequisite({
                "stage": "ENC",
                "op": "Encode",
                "args": {"payload": {"text": "Test data"}, "type": "note"}
            })
        """
        self.template.prerequisites.append(ir)
        return self
    
    def add_prerequisite_encode(
        self,
        text: str,
        type: str = "note",
        tags: Optional[List[str]] = None,
        facets: Optional[Dict[str, Any]] = None,
        weight: Optional[float] = None,
        **kwargs: Any,
    ) -> "SampleBuilder":
        """Add an Encode operation as a prerequisite.
        
        This is a convenience method for adding Encode prerequisites without
        manually constructing the IR.
        """
        payload = {"text": text}
        args = {"payload": payload, "type": type}
        
        if tags:
            args["tags"] = tags
        if facets:
            args["facets"] = facets
        if weight is not None:
            args["weight"] = weight
        
        for key, value in kwargs.items():
            if key not in args and key not in payload:
                args[key] = value
        
        return self.add_prerequisite({
            "stage": "ENC",
            "op": "Encode",
            "args": args,
        })
    
    def set_notes(self, notes: str) -> "SampleBuilder":
        """Add documentation notes."""
        self.template.notes = notes
        return self
    
    def build(self) -> SampleTemplate:
        """Build and return the sample template."""
        return self.template
    
    def save(self, path: Path, append: bool = True) -> None:
        """Save sample to a JSONL file."""
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(self.template.to_json() + "\n")


__all__ = ["SampleTemplate", "SampleBuilder"]

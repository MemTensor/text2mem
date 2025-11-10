"""
Unit tests for the text2mem.core.models module.

Focus areas:
1. Model validation logic
2. Field constraints
3. Model conversion and parsing
4. Error handling
"""
import pytest
from datetime import datetime
from text2mem.core.models import (
    IR, Stage, Op, Meta, Facets, Filters, TimeRange, Target,
    Embedding, EncodePayload, EncodeArgs, LabelArgs,
    UpdateSet, UpdateArgs, MergeArgs, PromoteArgs, DemoteArgs,
    DeleteArgs, RetrieveArgs, SummarizeArgs, SplitArgs, LockArgs, ExpireArgs
)
from pydantic import ValidationError


class TestMeta:
    """Tests for the Meta metadata model."""
    
    def test_meta_defaults(self):
        """Test default values of Meta."""
        meta = Meta()
        assert meta.actor is None
        assert meta.lang is None
        assert meta.trace_id is None
        assert meta.timestamp is None
        assert meta.dry_run is False
    
    def test_meta_timestamp_validation(self):
        """Test ISO8601 timestamp validation."""
        valid_timestamps = [
            "2023-12-01T10:30:00Z",
            "2023-12-01T10:30:00+08:00",
            "2023-12-01T10:30:00.123Z"
        ]
        for ts in valid_timestamps:
            meta = Meta(timestamp=ts)
            assert meta.timestamp == ts
    
    def test_meta_invalid_timestamp(self):
        """Test invalid timestamp format."""
        with pytest.raises(ValidationError) as exc_info:
            Meta(timestamp="invalid-timestamp")
        assert "Invalid timestamp format" in str(exc_info.value)


class TestFacets:
    """Tests for the Facets feature model."""
    
    def test_facets_at_least_one_field_required(self):
        """Test that at least one field is required."""
        with pytest.raises(ValidationError) as exc_info:
            Facets()
        assert "At least one facet field must be provided" in str(exc_info.value)
    
    def test_facets_valid_creation(self):
        """Test valid Facets creation."""
        facets = Facets(subject="Zhang San")
        assert facets.subject == "Zhang San"
        assert facets.time is None
        
        facets = Facets(time="2023-12-01T10:30:00Z", location="Beijing")
        assert facets.time == "2023-12-01T10:30:00Z"
        assert facets.location == "Beijing"
    
    def test_facets_time_validation(self):
        """Test invalid time format in Facets."""
        with pytest.raises(ValidationError) as exc_info:
            Facets(time="invalid-time")
        assert "Invalid time format" in str(exc_info.value)


class TestTimeRange:
    """Tests for the TimeRange model."""
    
    def test_absolute_time_range(self):
        """Test absolute time range fields."""
        tr = TimeRange(
            start="2023-12-01T00:00:00Z",
            end="2023-12-01T23:59:59Z"
        )
        assert tr.start == "2023-12-01T00:00:00Z"
        assert tr.end == "2023-12-01T23:59:59Z"
        assert tr.relative is None
    
    def test_relative_time_range(self):
        """Test relative time range fields."""
        tr = TimeRange(relative="last", amount=7, unit="days")
        assert tr.relative == "last"
        assert tr.amount == 7
        assert tr.unit == "days"
        assert tr.start is None
    
    def test_time_range_mutual_exclusion(self):
        """Test mutual exclusion of absolute and relative time."""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(
                start="2023-12-01T00:00:00Z",
                end="2023-12-01T23:59:59Z",
                relative="last",
                amount=7,
                unit="days"
            )
        assert "Conflicting time range settings" in str(exc_info.value)
    
    def test_incomplete_absolute_time(self):
        """Test incomplete absolute time definition."""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(start="2023-12-01T00:00:00Z")
        assert "Incomplete time range definition" in str(exc_info.value)
    
    def test_incomplete_relative_time(self):
        """Test incomplete relative time definition."""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(relative="last", amount=7)
        assert "Incomplete time range definition" in str(exc_info.value)


class TestTarget:
    """Tests for the Target selection model."""
    
    def test_target_by_id(self):
        """Test selecting by a single ID."""
        target = Target(ids="mem123")
        assert target.ids == "mem123"

    def test_target_by_ids_list(self):
        target = Target(ids=["mem123", "mem456"])
        assert target.ids == ["mem123", "mem456"]
    
    def test_target_filter(self):
        """Test selecting by filter (including limit)."""
        target = Target(filter=Filters(type="note", limit=5))
        assert target.filter and target.filter.type == "note"
        assert target.filter.limit == 5
    
    def test_target_all_exclusive(self):
        """Test that 'all=True' cannot coexist with other selectors."""
        with pytest.raises(ValidationError) as exc_info:
            Target(ids="mem123", all=True)
        assert "target must specify exactly one of ids | filter | search | all" in str(exc_info.value)
    
    def test_target_requires_selector(self):
        """Test that at least one selector must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            Target()
        assert "target must specify exactly one of ids | filter | search | all" in str(exc_info.value)


class TestEmbedding:
    """Tests for the Embedding vector model."""
    
    def test_embedding_creation(self):
        """Test vector creation."""
        vec = [0.1, 0.2, 0.3, 0.4]
        emb = Embedding(vec)
        assert len(emb) == 4
        assert emb[0] == 0.1
        assert emb.root == vec
    
    def test_embedding_indexing(self):
        """Test vector indexing access."""
        emb = Embedding([1.0, 2.0, 3.0])
        assert emb[0] == 1.0
        assert emb[1] == 2.0
        assert emb[2] == 3.0


class TestEncodePayload:
    """Tests for the EncodePayload model."""
    
    def test_text_payload(self):
        """Test text payload."""
        payload = EncodePayload(text="Test text")
        assert payload.text == "Test text"
        assert payload.url is None
        assert payload.structured is None
    
    def test_url_payload(self):
        """Test URL payload."""
        payload = EncodePayload(url="https://example.com")
        assert payload.url == "https://example.com"
        assert payload.text is None
    
    def test_structured_payload(self):
        """Test structured data payload."""
        data = {"title": "Test", "content": "Content"}
        payload = EncodePayload(structured=data)
        assert payload.structured == data
    
    def test_payload_mutual_exclusion(self):
        """Test that payload fields are mutually exclusive."""
        with pytest.raises(ValidationError) as exc_info:
            EncodePayload(text="test", url="https://example.com")
        assert "Exactly one of the following must be provided" in str(exc_info.value)
    
    def test_payload_required(self):
        """Test that at least one payload field must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            EncodePayload()
        assert "Exactly one of the following must be provided" in str(exc_info.value)


class TestLabelArgs:
    """Tests for the LabelArgs model."""
    
    def test_label_with_tags(self):
        """Test label with tags."""
        args = LabelArgs(tags=["work", "important"])
        assert args.tags == ["work", "important"]
    
    def test_label_with_facets(self):
        """Test label with facets."""
        facets = Facets(subject="Zhang San")
        args = LabelArgs(facets=facets)
        assert args.facets == facets
    
    def test_label_auto_generate(self):
        """Test auto-generating tags."""
        args = LabelArgs(auto_generate_tags=True)
        assert args.auto_generate_tags is True
    
    def test_label_requires_something(self):
        """Test that at least one argument is required."""
        with pytest.raises(ValidationError) as exc_info:
            LabelArgs()
        assert "Label operation requires at least one of" in str(exc_info.value)


class TestUpdateArgs:
    """Tests for the UpdateArgs model."""
    
    def test_update_text(self):
        """Test updating text field."""
        update_set = UpdateSet(text="New text")
        args = UpdateArgs(set=update_set)
        assert args.set.text == "New text"
    
    def test_update_multiple_fields(self):
        """Test updating multiple fields."""
        update_set = UpdateSet(
            text="New text",
            weight=0.9,
            tags=["updated"]
        )
        args = UpdateArgs(set=update_set)
        assert args.set.text == "New text"
        assert args.set.weight == 0.9
    
    def test_update_empty_set(self):
        """Test that empty update set raises an error."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateSet()
        assert "At least one field must be provided for update" in str(exc_info.value)


class TestPromoteArgs:
    """Tests for the PromoteArgs model."""
    
    def test_promote_requires_delta_or_remind(self):
        """Test that at least one of weight_delta or remind is required."""
        with pytest.raises(ValidationError):
            PromoteArgs()
    
    def test_promote_weight(self):
        """Test weight adjustment argument."""
        args = PromoteArgs(weight_delta=0.5)
        assert args.weight_delta == 0.5
    
    def test_promote_remind(self):
        """Test remind scheduling argument."""
        remind = {"rrule": "FREQ=DAILY", "until": "2023-12-31T23:59:59Z"}
        args = PromoteArgs(remind=remind)
        assert args.remind == remind
    
    def test_promote_mutual_exclusion(self):
        """Test argument mutual exclusion."""
        with pytest.raises(ValidationError) as exc_info:
            PromoteArgs(weight_delta=0.5, remind={"rrule":"FREQ=DAILY"})
        assert "Promote operation can only include one of" in str(exc_info.value)
    
    def test_promote_requires_something(self):
        """Test that at least one argument must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            PromoteArgs()
        assert "Promote operation requires at least one of" in str(exc_info.value)


class TestIR:
    """Tests for the IR (Intermediate Representation) model."""
    
    def test_ir_basic_creation(self):
        """Test basic IR creation."""
        ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "test"}})
        assert ir.stage == "ENC"
        assert ir.op == "Encode"
        assert "payload" in ir.args and ir.args["payload"]["text"] == "test"
        assert "engine_id" not in ir.args
    
    def test_ir_with_target(self):
        """Test IR with target field."""
        target = Target(ids="mem123")
        ir = IR(stage="STO", op="Update", target=target, args={"set": {"text": "New text"}})
        assert ir.target == target
    
    def test_ir_with_meta(self):
        """Test IR with metadata."""
        meta = Meta(actor="user1", dry_run=True)
        ir = IR(stage="RET", op="Retrieve", target={"ids": ["mem123"]}, meta=meta, args={})
        assert ir.meta == meta
    
    def test_ir_parse_args_typed(self):
        """Test parsing args into typed model."""
        ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "test text"}})
        typed_args = ir.parse_args_typed()
        assert isinstance(typed_args, EncodeArgs)
        assert typed_args.payload.text == "test text"
    
    def test_ir_stage_operation_validation(self):
        """Test stage-operation compatibility validation."""
        # Valid combinations
        ir1 = IR(stage="ENC", op="Encode", args={"payload": {"text": "test"}})
        assert ir1.stage == "ENC"
        
        ir2 = IR(stage="STO", op="Update", target={"ids": ["mem123"]}, args={"set": {"text": "test"}})
        assert ir2.stage == "STO"
        
        ir3 = IR(stage="RET", op="Retrieve", target={"ids": ["mem123"]}, args={})
        assert ir3.stage == "RET"
        
        # Invalid combination
        with pytest.raises(ValidationError) as exc_info:
            IR(stage="STO", op="Encode", args={"payload": {"text": "test"}})
        assert "Operation Encode must be executed in stage ENC" in str(exc_info.value)

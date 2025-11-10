"""Additional safety & validation tests.

Covers edge cases not exercised in the main suite:
1. STO-stage safety guards (all requires confirmation/dry_run)
2. Promote / Demote weight bounds
3. Retrieve include-field validation (invalid field)
4. Summarize max_tokens upper bound
5. Filter/search limit is now optional for STO operations
"""
import pytest
from pydantic import ValidationError

from text2mem.core.models import IR, PromoteArgs, DemoteArgs, RetrieveArgs, SummarizeArgs


def test_sto_filter_without_limit_is_allowed():
    """STO stage with target.filter but missing limit should now be allowed."""
    ir = IR(
        stage="STO",
        op="Update",
        target={"filter": {"has_tags": ["x"]}},  # no limit - allowed
        args={"set": {"text": "new"}},
    )
    assert ir.stage == "STO"
    assert ir.target.filter is not None
    assert ir.target.filter.limit is None  # limit is optional


def test_sto_search_without_limit_is_allowed():
    """STO stage with target.search but missing limit should now be allowed."""
    ir = IR(
        stage="STO",
        op="Label",
        target={"search": {"intent": {"query": "foo"}}},  # no limit - allowed
        args={"tags": ["x"]},
    )
    assert ir.stage == "STO"
    assert ir.target.search is not None
    assert ir.target.search.limit is None  # limit is optional


def test_sto_all_requires_confirmation():
    """STO stage using all=True must include confirmation/dry_run."""
    with pytest.raises(ValidationError) as exc:
        IR(
            stage="STO",
            op="Delete",
            target={"all": True},
            args={"soft": True},
        )
    assert "dry_run" in str(exc.value) or "confirmation" in str(exc.value)


def test_retrieve_requires_target():
    """Retrieve must specify a valid target."""
    with pytest.raises(ValidationError) as exc:
        IR(stage="RET", op="Retrieve", args={})
    assert "target" in str(exc.value)


def test_ret_all_requires_confirmation():
    """RET stage with all=True requires explicit confirmation."""
    with pytest.raises(ValidationError) as exc:
        IR(stage="RET", op="Retrieve", target={"all": True}, args={})
    assert "confirmation" in str(exc.value)

    ok = IR(
        stage="RET",
        op="Retrieve",
        target={"all": True},
        args={},
        meta={"confirmation": True},
    )
    assert ok.meta and ok.meta.confirmation is True


def test_promote_weight_out_of_range():
    """Weight must be within [0,1] range."""
    with pytest.raises(ValidationError) as exc:
        PromoteArgs(weight=1.5)
    assert "[0,1]" in str(exc.value)


def test_demote_weight_out_of_range():
    """Weight must be within [0,1] range."""
    with pytest.raises(ValidationError) as exc:
        DemoteArgs(weight=-0.1)
    assert "[0,1]" in str(exc.value)


def test_retrieve_invalid_include_field():
    """Invalid include field should trigger validation error."""
    with pytest.raises(ValidationError) as exc:
        RetrieveArgs(include=["id", "nonexistent_field"])
    assert "invalid field" in str(exc.value).lower()


def test_promote_weight_delta_range():
    """weight_delta must be within [-1,1] range."""
    with pytest.raises(ValidationError) as exc:
        PromoteArgs(weight_delta=2.0)
    assert "[-1,1]" in str(exc.value)


def test_demote_weight_delta_range():
    """weight_delta must be within [-1,1] range."""
    with pytest.raises(ValidationError) as exc:
        DemoteArgs(weight_delta=-2.0)
    assert "[-1,1]" in str(exc.value)


def test_summarize_max_tokens_upper_bound():
    """max_tokens above limit should raise validation error."""
    with pytest.raises(ValidationError) as exc:
        SummarizeArgs(max_tokens=5000)
    assert "max_tokens should not exceed" in str(exc.value).lower()


def test_sto_search_limit_zero_invalid():
    """Explicit zero (invalid) for search.limit should raise validation error."""
    with pytest.raises(ValidationError) as exc:
        IR(
            stage="STO",
            op="Label",
            target={"search": {"intent": {"query": "foo"}, "limit": 0}},
            args={"tags": ["x"]},
        )
    assert "ge=1" in str(exc.value) or "limit" in str(exc.value).lower()

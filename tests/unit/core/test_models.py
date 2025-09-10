"""
测试 text2mem.core.models 模块中的数据模型
重点测试：
1. 模型验证逻辑
2. 字段约束
3. 模型转换和解析
4. 错误处理
"""
import pytest
from datetime import datetime
from text2mem.core.models import (
    IR, Stage, Op, Meta, Facets, Filters, TimeRange, TargetSpec, 
    Embedding, Priority, EncodePayload, EncodeArgs, LabelArgs,
    UpdateSet, UpdateArgs, MergeArgs, PromoteArgs, DemoteArgs,
    DeleteArgs, RetrieveArgs, SummarizeArgs, SplitArgs, LockArgs, ExpireArgs
)
from pydantic import ValidationError


class TestMeta:
    """测试Meta元数据模型"""
    
    def test_meta_defaults(self):
        """测试Meta模型的默认值"""
        meta = Meta()
        assert meta.actor is None
        assert meta.lang is None
        assert meta.trace_id is None
        assert meta.timestamp is None
        assert meta.dry_run is False
    
    def test_meta_timestamp_validation(self):
        """测试时间戳格式验证"""
        # 有效的ISO8601格式
        valid_timestamps = [
            "2023-12-01T10:30:00Z",
            "2023-12-01T10:30:00+08:00",
            "2023-12-01T10:30:00.123Z"
        ]
        for ts in valid_timestamps:
            meta = Meta(timestamp=ts)
            assert meta.timestamp == ts
    
    def test_meta_invalid_timestamp(self):
        """测试无效时间戳格式"""
        with pytest.raises(ValidationError) as exc_info:
            Meta(timestamp="invalid-timestamp")
        assert "时间戳格式错误" in str(exc_info.value)


class TestFacets:
    """测试Facets特性模型"""
    
    def test_facets_at_least_one_field_required(self):
        """测试至少需要一个字段"""
        with pytest.raises(ValidationError) as exc_info:
            Facets()
        assert "特性集合至少需要提供一个字段" in str(exc_info.value)
    
    def test_facets_valid_creation(self):
        """测试有效的Facets创建"""
        facets = Facets(subject="张三")
        assert facets.subject == "张三"
        assert facets.time is None
        
        facets = Facets(time="2023-12-01T10:30:00Z", location="北京")
        assert facets.time == "2023-12-01T10:30:00Z"
        assert facets.location == "北京"
    
    def test_facets_time_validation(self):
        """测试时间格式验证"""
        with pytest.raises(ValidationError) as exc_info:
            Facets(time="invalid-time")
        assert "时间格式错误" in str(exc_info.value)


class TestTimeRange:
    """测试TimeRange时间范围模型"""
    
    def test_absolute_time_range(self):
        """测试绝对时间范围"""
        tr = TimeRange(
            start="2023-12-01T00:00:00Z",
            end="2023-12-01T23:59:59Z"
        )
        assert tr.start == "2023-12-01T00:00:00Z"
        assert tr.end == "2023-12-01T23:59:59Z"
        assert tr.relative is None
    
    def test_relative_time_range(self):
        """测试相对时间范围"""
        tr = TimeRange(relative="last", amount=7, unit="days")
        assert tr.relative == "last"
        assert tr.amount == 7
        assert tr.unit == "days"
        assert tr.start is None
    
    def test_time_range_mutual_exclusion(self):
        """测试绝对和相对时间不能同时设置"""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(
                start="2023-12-01T00:00:00Z",
                end="2023-12-01T23:59:59Z",
                relative="last",
                amount=7,
                unit="days"
            )
        assert "时间范围设置冲突" in str(exc_info.value)
    
    def test_incomplete_absolute_time(self):
        """测试不完整的绝对时间设置"""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(start="2023-12-01T00:00:00Z")
        assert "时间范围设置不完整" in str(exc_info.value)
    
    def test_incomplete_relative_time(self):
        """测试不完整的相对时间设置"""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(relative="last", amount=7)
        assert "时间范围设置不完整" in str(exc_info.value)


class TestTargetSpec:
    """测试TargetSpec目标规范模型"""
    
    def test_target_by_id(self):
        """测试通过ID定位"""
        target = TargetSpec(by_id="mem123")
        assert target.by_id == "mem123"
        
        target = TargetSpec(by_id=["mem123", "mem456"])
        assert target.by_id == ["mem123", "mem456"]
    
    def test_target_by_tags(self):
        """测试通过标签定位"""
        target = TargetSpec(by_tags=["work", "important"], match="all")
        assert target.by_tags == ["work", "important"]
        assert target.match == "all"
    
    def test_target_all_exclusive(self):
        """测试all=True与其他定位方式互斥"""
        with pytest.raises(ValidationError) as exc_info:
            TargetSpec(all=True, by_id="mem123")
        assert "当 all=True 时，不能同时使用其他定位方式" in str(exc_info.value)
    
    def test_target_requires_selector(self):
        """测试必须提供至少一种定位方式"""
        with pytest.raises(ValidationError) as exc_info:
            TargetSpec()
        assert "目标规范至少需要提供一种定位方式" in str(exc_info.value)


class TestEmbedding:
    """测试Embedding向量模型"""
    
    def test_embedding_creation(self):
        """测试向量创建"""
        vec = [0.1, 0.2, 0.3, 0.4]
        emb = Embedding(vec)
        assert len(emb) == 4
        assert emb[0] == 0.1
        assert emb.root == vec
    
    def test_embedding_indexing(self):
        """测试向量索引访问"""
        emb = Embedding([1.0, 2.0, 3.0])
        assert emb[0] == 1.0
        assert emb[1] == 2.0
        assert emb[2] == 3.0


class TestEncodePayload:
    """测试EncodePayload编码负载模型"""
    
    def test_text_payload(self):
        """测试文本负载"""
        payload = EncodePayload(text="测试文本")
        assert payload.text == "测试文本"
        assert payload.url is None
        assert payload.structured is None
    
    def test_url_payload(self):
        """测试URL负载"""
        payload = EncodePayload(url="https://example.com")
        assert payload.url == "https://example.com"
        assert payload.text is None
    
    def test_structured_payload(self):
        """测试结构化负载"""
        data = {"title": "测试", "content": "内容"}
        payload = EncodePayload(structured=data)
        assert payload.structured == data
    
    def test_payload_mutual_exclusion(self):
        """测试负载类型互斥"""
        with pytest.raises(ValidationError) as exc_info:
            EncodePayload(text="测试", url="https://example.com")
        assert "必须且只能包含以下一种" in str(exc_info.value)
    
    def test_payload_required(self):
        """测试必须提供一种负载类型"""
        with pytest.raises(ValidationError) as exc_info:
            EncodePayload()
        assert "必须且只能包含以下一种" in str(exc_info.value)


class TestLabelArgs:
    """测试LabelArgs标签参数模型"""
    
    def test_label_with_tags(self):
        """测试提供标签"""
        args = LabelArgs(tags=["work", "important"])
        assert args.tags == ["work", "important"]
    
    def test_label_with_facets(self):
        """测试提供特性"""
        facets = Facets(subject="张三")
        args = LabelArgs(facets=facets)
        assert args.facets == facets
    
    def test_label_auto_generate(self):
        """测试自动生成标签"""
        args = LabelArgs(auto_generate_tags=True)
        assert args.auto_generate_tags is True
    
    def test_label_requires_something(self):
        """测试必须提供至少一种参数"""
        with pytest.raises(ValidationError) as exc_info:
            LabelArgs()
        assert "Label 操作至少需要提供" in str(exc_info.value)


class TestUpdateArgs:
    """测试UpdateArgs更新参数模型"""
    
    def test_update_text(self):
        """测试更新文本"""
        update_set = UpdateSet(text="新文本")
        args = UpdateArgs(set=update_set)
        assert args.set.text == "新文本"
    
    def test_update_multiple_fields(self):
        """测试更新多个字段"""
        update_set = UpdateSet(
            text="新文本",
            priority="high",
            tags=["updated"]
        )
        args = UpdateArgs(set=update_set)
        assert args.set.text == "新文本"
        assert args.set.priority == "high"
    
    def test_update_empty_set(self):
        """测试空的更新集合"""
        with pytest.raises(ValidationError) as exc_info:
            UpdateSet()
        assert "必须至少包含一个要更新的字段" in str(exc_info.value)


class TestPromoteArgs:
    """测试PromoteArgs提升参数模型"""
    
    def test_promote_priority(self):
        """测试提升优先级"""
        args = PromoteArgs(priority="high")
        assert args.priority == "high"
    
    def test_promote_weight(self):
        """测试调整权重"""
        args = PromoteArgs(weight_delta=0.5)
        assert args.weight_delta == 0.5
    
    def test_promote_remind(self):
        """测试设置提醒"""
        remind = {"rrule": "FREQ=DAILY", "until": "2023-12-31T23:59:59Z"}
        args = PromoteArgs(remind=remind)
        assert args.remind == remind
    
    def test_promote_mutual_exclusion(self):
        """测试参数互斥"""
        with pytest.raises(ValidationError) as exc_info:
            PromoteArgs(priority="high", weight_delta=0.5)
        assert "Promote 操作只能提供以下一种" in str(exc_info.value)
    
    def test_promote_requires_something(self):
        """测试必须提供至少一种参数"""
        with pytest.raises(ValidationError) as exc_info:
            PromoteArgs()
        assert "Promote 操作至少需要提供以下一种" in str(exc_info.value)


class TestIR:
    """测试IR中间表示模型"""
    
    def test_ir_basic_creation(self):
        """测试IR基本创建"""
        ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "测试"}})
        assert ir.stage == "ENC"
        assert ir.op == "Encode"
        assert ir.args == {"payload": {"text": "测试"}}
    
    def test_ir_with_target(self):
        """测试带目标的IR"""
        target = TargetSpec(by_id="mem123")
        ir = IR(stage="STO", op="Update", target=target, args={"set": {"text": "新文本"}})
        assert ir.target == target
    
    def test_ir_with_meta(self):
        """测试带元数据的IR"""
        meta = Meta(actor="user1", dry_run=True)
        ir = IR(stage="RET", op="Retrieve", meta=meta, args={"k": 10})
        assert ir.meta == meta
    
    def test_ir_parse_args_typed(self):
        """测试IR参数类型解析"""
        ir = IR(
            stage="ENC", 
            op="Encode", 
            args={"payload": {"text": "测试文本"}}
        )
        
        typed_args = ir.parse_args_typed()
        assert isinstance(typed_args, EncodeArgs)
        assert typed_args.payload.text == "测试文本"
    
    def test_ir_stage_operation_validation(self):
        """测试阶段与操作的匹配验证"""
        # 正确的匹配
        ir1 = IR(stage="ENC", op="Encode", args={"payload": {"text": "test"}})
        assert ir1.stage == "ENC"
        
        ir2 = IR(stage="STO", op="Update", args={"set": {"text": "test"}})
        assert ir2.stage == "STO"
        
        ir3 = IR(stage="RET", op="Retrieve", args={"k": 10})
        assert ir3.stage == "RET"
        
        # 错误的匹配
        with pytest.raises(ValidationError) as exc_info:
            IR(stage="STO", op="Encode", args={"payload": {"text": "test"}})
        assert "操作类型 Encode 需要在 ENC 或 RET 阶段执行" in str(exc_info.value)

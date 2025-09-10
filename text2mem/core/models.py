# moved from text2mem/models.py
from __future__ import annotations
from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, RootModel

Stage = Literal["ENC", "STO", "RET"]
Op = Literal[
    "Encode","Label","Update","Merge","Promote","Demote","Delete",
    "Retrieve","Summarize","Split","Lock","Expire"#,"Clarify"
]

class Meta(BaseModel):
    actor: Optional[str] = None
    lang: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: Optional[str] = None
    dry_run: bool = False
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        if v:
            try:
                from datetime import datetime
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"时间戳格式错误: '{v}' 不是有效的ISO8601格式")
        return v

class Facets(BaseModel):
    subject: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    
    @model_validator(mode="after")
    def validate_non_empty(self):
        # Access model_fields from the class to avoid Pydantic v2.11 deprecation
        if not any(getattr(self, field) for field in self.__class__.model_fields):
            raise ValueError("特性集合至少需要提供一个字段")
        if self.time:
            try:
                from datetime import datetime
                datetime.fromisoformat(self.time.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"时间格式错误: '{self.time}' 不是有效的ISO8601格式")
        return self

class Filters(BaseModel):
    time_range: Optional["TimeRange"] = None
    has_tags: Optional[List[str]] = None
    not_tags: Optional[List[str]] = None
    type: Optional[Literal["note","event","task","profile","preference","generic"]] = None
    limit: Optional[int] = Field(default=None, ge=1)
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        if v is not None and v < 1:
            raise ValueError("limit 必须大于或等于1")
        return v

class TimeRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    relative: Optional[Literal["last","next"]] = None
    amount: Optional[int] = Field(default=None, gt=0)
    unit: Optional[Literal["minutes","hours","days","weeks","months","years"]] = None

    @model_validator(mode="after")
    def _xor(self):
        abs_ok = self.start is not None and self.end is not None
        rel_ok = self.relative is not None and self.amount is not None and self.unit is not None
        if not (abs_ok or rel_ok):
            raise ValueError("时间范围设置不完整。请提供: (1)start+end 或 (2)relative+amount+unit")
        if abs_ok and rel_ok:
            raise ValueError("时间范围设置冲突。请只提供一组: (1)start+end 或 (2)relative+amount+unit")
        if (self.start is not None and self.end is None) or (self.end is not None and self.start is None):
            raise ValueError("使用绝对时间范围时，必须同时提供 start 和 end")
        if (self.relative is not None or self.unit is not None) and self.amount is None:
            raise ValueError("使用相对时间范围时，必须提供 amount（数量）")
        if self.amount is not None and (self.relative is None or self.unit is None):
            raise ValueError("使用相对时间范围时，必须同时提供 relative 和 unit")
        return self

class TargetSpec(BaseModel):
    by_id: Optional[Union[str, List[str]]] = None
    by_tags: Optional[List[str]] = None
    match: Literal["any","all"] = "any"
    by_query: Optional[str] = None
    topic: Optional[str] = None
    all: bool = False
    filters: Optional[Filters] = None
    
    @model_validator(mode="after")
    def validate_target_specification(self):
        has_selector = any([self.by_id, self.by_tags, self.by_query, self.topic, self.all])
        if not has_selector:
            raise ValueError("目标规范至少需要提供一种定位方式：by_id、by_tags、by_query、topic 或 all")
        if self.all and any([self.by_id, self.by_tags, self.by_query, self.topic]):
            raise ValueError("当 all=True 时，不能同时使用其他定位方式")
        return self

class Embedding(RootModel):
    root: List[float]
    def __len__(self):
        return len(self.root)
    def __getitem__(self, index):
        return self.root[index]

Priority = Literal["low","normal","high","urgent"]

class EncodePayload(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    structured: Optional[Dict[str, Any]] = None
    @model_validator(mode="after")
    def one_of(self):
        present = sum(v is not None for v in [self.text, self.url, self.structured])
        if present != 1:
            raise ValueError("payload 必须且只能包含以下一种：text（文本） | url（网址） | structured（结构化数据）")
        return self

class EncodeArgs(BaseModel):
    payload: EncodePayload
    type: Optional[Literal["note","event","task","profile","preference","generic"]] = None
    tags: Optional[List[str]] = None
    facets: Optional[Facets] = None
    time: Optional[str] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    embedding: Optional[List[float]] = None
    use_embedding: bool = False
    source: Optional[str] = None
    priority: Optional[Priority] = None
    auto_frequency: Optional[str] = None
    expire_at: Optional[str] = None
    next_auto_update_at: Optional[str] = None
    read_perm_level: Optional[Literal["public","team","private","custom"]] = None
    write_perm_level: Optional[Literal["open","maintainer","owner_only","custom"]] = None
    read_whitelist: Optional[List[str]] = None
    read_blacklist: Optional[List[str]] = None
    write_whitelist: Optional[List[str]] = None
    write_blacklist: Optional[List[str]] = None
    
    @model_validator(mode="after")
    def validate_time_format(self):
        if self.time:
            try:
                from datetime import datetime
                datetime.fromisoformat(self.time.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"时间格式错误: '{self.time}' 不是有效的ISO8601格式")
        return self

class LabelArgs(BaseModel):
    tags: Optional[List[str]] = None
    facets: Optional[Facets] = None
    auto_generate_tags: Optional[bool] = False
    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.tags and not self.facets and not self.auto_generate_tags:
            raise ValueError("Label 操作至少需要提供 tags、facets 或 auto_generate_tags 中的一个")
        return self

class UpdateSet(BaseModel):
    text: Optional[str] = None
    time: Optional[str] = None
    type: Optional[Literal["note","event","task","profile","preference","generic"]] = None
    ttl: Optional[str] = None
    priority: Optional[Priority] = None
    weight: Optional[float] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    facets: Optional[Facets] = None
    embedding: Optional[List[float]] = None
    auto_frequency: Optional[str] = None
    expire_at: Optional[str] = None
    next_auto_update_at: Optional[str] = None
    read_perm_level: Optional[Literal["public","team","private","custom"]] = None
    write_perm_level: Optional[Literal["open","maintainer","owner_only","custom"]] = None
    read_whitelist: Optional[List[str]] = None
    read_blacklist: Optional[List[str]] = None
    write_whitelist: Optional[List[str]] = None
    write_blacklist: Optional[List[str]] = None
    @model_validator(mode="after")
    def _non_empty(self):
        if not any(getattr(self, f) is not None for f in self.__class__.model_fields):
            raise ValueError("Update.set 必须至少包含一个要更新的字段")
        return self

class UpdateArgs(BaseModel):
    set: UpdateSet
    @model_validator(mode="after")
    def validate_updates(self):
        if not self.set:
            raise ValueError("更新操作必须指定至少一个要更新的字段")
        return self

class MergeArgs(BaseModel):
    strategy: Literal["link_and_keep","fold_into_primary"] = "fold_into_primary"
    primary_id: Optional[str] = None
    soft_delete_children: bool = True
    @model_validator(mode="after")
    def validate_strategy_dependencies(self):
        return self
        return self

class PromoteArgs(BaseModel):
    priority: Optional[Priority] = None
    weight_delta: Optional[float] = None
    remind: Optional[Dict[str, Optional[str]]] = None
    @model_validator(mode="after")
    def _one_of(self):
        provided = sum(1 for v in [self.priority is not None, self.weight_delta is not None, self.remind is not None] if v)
        if provided == 0:
            raise ValueError("Promote 操作至少需要提供以下一种：priority（优先级） | weight_delta（权重调整） | remind（提醒）")
        elif provided > 1:
            raise ValueError("Promote 操作只能提供以下一种：priority（优先级） | weight_delta（权重调整） | remind（提醒）")
        if self.remind and "rrule" not in self.remind:
            raise ValueError("remind 必须包含 rrule 字段")
        return self

class DemoteArgs(BaseModel):
    archive: Optional[bool] = None
    priority: Optional[Priority] = None
    weight_delta: Optional[float] = None
    @model_validator(mode="after")
    def validate_operations(self):
        if self.archive is None and self.priority is None and self.weight_delta is None:
            raise ValueError("Demote 操作至少需要提供以下一种：archive（归档） | priority（优先级） | weight_delta（权重调整）")
        return self

class DeleteArgs(BaseModel):
    older_than: Optional[str] = None
    time_range: Optional[TimeRange] = None
    soft: bool = True
    reason: Optional[str] = None
    @model_validator(mode="after")
    def validate_time_criteria(self):
        if self.older_than is not None and self.time_range is not None:
            raise ValueError("不能同时设置 older_than 和 time_range，请只选择一种时间条件")
        return self

class RetrieveArgs(BaseModel):
    query: Optional[str] = None
    time_range: Optional[TimeRange] = None
    k: int = 10
    order_by: Literal["relevance","time_desc","time_asc","priority_desc"] = "relevance"
    include: Optional[List[str]] = None
    @field_validator('k')
    @classmethod
    def validate_k(cls, v):
        if v < 1:
            raise ValueError("k 必须大于或等于1")
        if v > 100:
            raise ValueError("k 不能超过100，请考虑使用分页")
        return v
    @field_validator('include')
    @classmethod
    def validate_include(cls, v):
        if v is None:
            return v
        allowed_fields = [
            "id", "text", "type", "tags", "facets", "time", "subject", "location", "topic",
            "source", "priority", "weight", 
            "read_perm_level", "write_perm_level",
            "read_whitelist", "read_blacklist", "write_whitelist", "write_blacklist"
        ]
        for field in v:
            if field not in allowed_fields:
                raise ValueError(f"include 包含无效字段: '{field}'。允许的字段: {', '.join(allowed_fields)}")
        return v

class SummarizeArgs(BaseModel):
    focus: Optional[str] = None
    max_tokens: int = 256
    time_range: Optional[TimeRange] = None
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1:
            raise ValueError("max_tokens 必须至少为1")
        if v > 2000:
            raise ValueError("max_tokens 不建议超过2000，请考虑分段总结")
        return v

class SplitArgs(BaseModel):
    strategy: Literal["auto_by_patterns","headings","sentences","custom_spans"] = "auto_by_patterns"
    spans: Optional[List[Dict[str,int]]] = None
    inherit: Optional[Dict[str,bool]] = None
    link_back: Literal["none","bi_directional"] = "bi_directional"
    @model_validator(mode="after")
    def validate_strategy_and_spans(self):
        if self.strategy == "custom_spans" and not self.spans:
            raise ValueError("当使用 'custom_spans' 策略时，必须提供 spans 参数")
        if self.spans and self.strategy != "custom_spans":
            raise ValueError(f"当提供 spans 参数时，strategy 必须设置为 'custom_spans'，而不是 '{self.strategy}'")
        if self.spans:
            for i, span in enumerate(self.spans):
                if "start" not in span or "end" not in span:
                    raise ValueError(f"第 {i+1} 个跨度缺少 'start' 或 'end' 字段")
                if not isinstance(span.get("start"), int) or not isinstance(span.get("end"), int):
                    raise ValueError(f"第 {i+1} 个跨度的 'start' 和 'end' 必须是整数")
                if span.get("start") < 0 or span.get("end") <= span.get("start"):
                    raise ValueError(f"第 {i+1} 个跨度的 'start' 必须大于等于0，且 'end' 必须大于 'start'")
        if self.inherit:
            allowed_keys = ["tags", "time", "source"]
            for key in self.inherit:
                if key not in allowed_keys:
                    raise ValueError(f"inherit 只能包含以下字段：{', '.join(allowed_keys)}，发现无效字段: '{key}'")
                if not isinstance(self.inherit[key], bool):
                    raise ValueError(f"inherit.{key} 必须是布尔值")
        return self

class LockArgs(BaseModel):
    mode: Literal["read_only","append_only"] = "read_only"
    reason: Optional[str] = None
    policy: Optional[Dict[str, Any]] = None
    @model_validator(mode="after")
    def validate_policy(self):
        if self.policy:
            allowed_keys = ["allow", "deny", "reviewers", "expires"]
            for key in self.policy:
                if key not in allowed_keys:
                    raise ValueError(f"policy 只能包含以下字段：{', '.join(allowed_keys)}，发现无效字段: '{key}'")
            if "allow" in self.policy and not isinstance(self.policy["allow"], list):
                raise ValueError("policy.allow 必须是操作列表")
            if "deny" in self.policy and not isinstance(self.policy["deny"], list):
                raise ValueError("policy.deny 必须是操作列表")
            if "reviewers" in self.policy and not isinstance(self.policy["reviewers"], list):
                raise ValueError("policy.reviewers 必须是字符串列表")
            if "expires" in self.policy:
                try:
                    from datetime import datetime
                    datetime.fromisoformat(self.policy["expires"].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    raise ValueError(f"policy.expires 必须是有效的ISO8601格式时间")
        return self
    def is_read_only(self) -> bool:
        return self.mode == "read_only"
    def is_append_only(self) -> bool:
        return self.mode == "append_only"

class ExpireArgs(BaseModel):
    ttl: Optional[str] = None
    until: Optional[str] = None
    on_expire: Literal["soft_delete","hard_delete","demote","anonymize"] = "soft_delete"
    @model_validator(mode="after")
    def _one_of(self):
        if not ((self.ttl is not None) ^ (self.until is not None)):
            raise ValueError("Expire 操作必须且只能提供以下一种：ttl（生存时间） | until（过期日期）")
        if self.until:
            try:
                from datetime import datetime
                datetime.fromisoformat(self.until.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"过期日期格式错误: '{self.until}' 不是有效的ISO8601格式")
        return self

class IR(BaseModel):
    stage: Stage
    op: Op
    target: Optional[TargetSpec] = None
    args: Dict[str, Any] = {}
    meta: Optional[Meta] = None
    def parse_args_typed(self) -> BaseModel:
        mapper = {
            "Encode": EncodeArgs, "Label": LabelArgs, "Update": UpdateArgs,
            "Merge": MergeArgs, "Promote": PromoteArgs, "Demote": DemoteArgs,
            "Delete": DeleteArgs, "Retrieve": RetrieveArgs, "Summarize": SummarizeArgs,
            "Split": SplitArgs, "Lock": LockArgs, "Expire": ExpireArgs,
        }
        cls = mapper[self.op]
        return cls.model_validate(self.args)
    @model_validator(mode="after")
    def _stage_guard(self):
        enc_ops = {"Encode"}
        sto_ops = {"Label","Update","Merge","Promote","Demote","Delete","Split","Lock","Expire"}
        ret_ops = {"Retrieve","Summarize"}
        if self.op in enc_ops and self.stage not in {"ENC","RET"}:
            raise ValueError(f"操作类型 {self.op} 需要在 ENC 或 RET 阶段执行")
        if self.op in sto_ops and self.stage != "STO":
            raise ValueError(f"操作类型 {self.op} 需要在 STO 阶段执行")
        if self.op in ret_ops and self.stage != "RET":
            raise ValueError(f"操作类型 {self.op} 需要在 RET 阶段执行")
        return self

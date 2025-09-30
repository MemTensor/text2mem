# moved from text2mem/models.py
from __future__ import annotations
from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, RootModel

Stage = Literal["ENC", "STO", "RET"]
Op = Literal[
    "Encode","Label","Update","Merge","Promote","Demote","Delete",
    "Retrieve","Summarize","Split","Lock","Expire"
]

class Meta(BaseModel):
    actor: Optional[str] = None
    lang: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: Optional[str] = None
    dry_run: bool = False
    confirmation: bool = False
    
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
    type: Optional[str] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    facet_subject: Optional[str] = None
    facet_time: Optional[str] = None
    facet_location: Optional[str] = None
    facet_topic: Optional[str] = None
    weight_gte: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    weight_lte: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    expire_before: Optional[str] = None
    expire_after: Optional[str] = None
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

class SearchIntent(BaseModel):
    query: Optional[str] = None
    vector: Optional[List[float]] = None

    @model_validator(mode="after")
    def _one_of(self):
        if not ((self.query is not None) ^ (self.vector is not None)):
            raise ValueError("search.intent 必须且只能设置 query 或 vector 其中之一")
        return self

class SearchOverrides(BaseModel):
    k: Optional[int] = Field(default=None, ge=1)
    alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    order_by: Optional[Literal["relevance","time_desc","time_asc","weight_desc"]] = None

class TargetSearch(BaseModel):
    intent: SearchIntent
    overrides: Optional[SearchOverrides] = None
    limit: Optional[int] = Field(default=None, ge=1)

class Target(BaseModel):
    ids: Optional[Union[str, List[str]]] = None
    filter: Optional[Filters] = None
    search: Optional[TargetSearch] = None
    all: bool = False

    @model_validator(mode="after")
    def _xor(self):
        # Allow search+filter combo; keep ids/all mutually exclusive
        has_ids = self.ids is not None
        has_filter = self.filter is not None
        has_search = self.search is not None
        has_all = bool(self.all)
        if has_all and (has_ids or has_filter or has_search):
            # Keep legacy error message for compatibility with tests
            raise ValueError("target 必须且只能在 ids | filter | search | all 中选择一种")
        if has_ids and (has_filter or has_search or has_all):
            raise ValueError("target 必须且只能在 ids | filter | search | all 中选择一种")
        if not (has_ids or has_filter or has_search or has_all):
            raise ValueError("target 必须且只能在 ids | filter | search | all 中选择一种")
        return self

class Embedding(RootModel):
    root: List[float]
    def __len__(self):
        return len(self.root)
    def __getitem__(self, index):
        return self.root[index]


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
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    facets: Optional[Facets] = None
    time: Optional[str] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    skip_embedding: Optional[bool] = False
    source: Optional[str] = None
    
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
    type: Optional[str] = None
    ttl: Optional[str] = None
    
    weight: Optional[float] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    facets: Optional[Facets] = None
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
    @model_validator(mode="after")
    def _validate_weight_range(self):
        if self.weight is not None:
            if not (0.0 <= self.weight <= 1.0):
                raise ValueError("Update.set.weight 必须在 [0,1] 区间内")
        return self
    

class UpdateArgs(BaseModel):
    set: UpdateSet
    @model_validator(mode="after")
    def validate_updates(self):
        if not self.set:
            raise ValueError("更新操作必须指定至少一个要更新的字段")
        return self

class MergeArgs(BaseModel):
    strategy: Literal["merge_into_primary"] = "merge_into_primary"
    primary_id: str = "auto"
    soft_delete_children: bool = True
    skip_reembedding: bool = False

class PromoteArgs(BaseModel):
    weight: Optional[float] = None
    weight_delta: Optional[float] = None
    remind: Optional[Dict[str, Optional[str]]] = None
    @model_validator(mode="after")
    def _one_of(self):
        provided = sum(1 for v in [self.weight is not None, self.weight_delta is not None, self.remind is not None] if v)
        if provided == 0:
            raise ValueError("Promote 操作至少需要提供以下一种：weight（设置绝对权重） | weight_delta（权重调整） | remind（提醒）")
        elif provided > 1:
            raise ValueError("Promote 操作只能提供以下一种：weight（设置绝对权重） | weight_delta（权重调整） | remind（提醒）")
        if self.remind and "rrule" not in self.remind:
            raise ValueError("remind 必须包含 rrule 字段")
        return self
    @model_validator(mode="after")
    def _validate_weight_range(self):
        if self.weight is not None:
            if not (0.0 <= self.weight <= 1.0):
                raise ValueError("Promote.weight 必须在 [0,1] 区间内")
        if self.weight_delta is not None:
            try:
                delta = float(self.weight_delta)
            except (TypeError, ValueError):
                raise ValueError("Promote.weight_delta 必须是数值类型")
            if not (-1.0 <= delta <= 1.0):
                raise ValueError("Promote.weight_delta 建议在 [-1,1] 区间内，以避免权重越界")
        return self

class DemoteArgs(BaseModel):
    archive: Optional[bool] = None
    weight: Optional[float] = None
    weight_delta: Optional[float] = None
    @model_validator(mode="after")
    def validate_operations(self):
        provided = sum(1 for v in [self.archive is not None, self.weight is not None, self.weight_delta is not None] if v)
        if provided == 0:
            raise ValueError("Demote 操作至少需要提供以下一种：archive（归档） | weight（设置绝对权重） | weight_delta（权重调整）")
        if provided > 1:
            raise ValueError("Demote 操作只能提供以下一种：archive（归档） | weight（设置绝对权重） | weight_delta（权重调整）")
        return self
    @model_validator(mode="after")
    def _validate_weight_range(self):
        if self.weight is not None:
            if not (0.0 <= self.weight <= 1.0):
                raise ValueError("Demote.weight 必须在 [0,1] 区间内")
        if self.weight_delta is not None:
            try:
                delta = float(self.weight_delta)
            except (TypeError, ValueError):
                raise ValueError("Demote.weight_delta 必须是数值类型")
            if not (-1.0 <= delta <= 1.0):
                raise ValueError("Demote.weight_delta 建议在 [-1,1] 区间内，以避免权重越界")
        return self

class DeleteArgs(BaseModel):
    older_than: Optional[str] = None
    time_range: Optional[TimeRange] = None
    soft: bool = True
    reason: Optional[str] = None
    # Note: time scoping is recommended via target.filter.time_range.
    # older_than/time_range here are optional convenience fields.

class RetrieveArgs(BaseModel):
    include: Optional[List[str]] = None
    @field_validator('include')
    @classmethod
    def validate_include(cls, v):
        if v is None:
            return v
        allowed_fields = [
            "id", "text", "type", "tags", "facets", "time", "subject", "location", "topic",
            "source", "weight",
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
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1:
            raise ValueError("max_tokens 必须至少为1")
        if v > 2000:
            raise ValueError("max_tokens 不建议超过2000，请考虑分段总结")
        return v

class SplitArgs(BaseModel):
    strategy: Literal["by_sentences","by_chunks","custom"] = "by_sentences"
    params: Optional[Dict[str, Any]] = None
    # legacy compatibility
    spans: Optional[List[Dict[str,int]]] = None
    inherit: Optional[Dict[str,bool]] = None
    inherit_all: bool = True

    @field_validator('strategy', mode='before')
    @classmethod
    def _map_legacy_strategy(cls, v):
        mapping = {
            "sentences": "by_sentences",
            "headings": "by_sentences",
            "auto_by_patterns": "by_sentences",
            "custom_spans": "custom",  # handled via spans/custom
        }
        if isinstance(v, str) and v in mapping:
            return mapping[v]
        return v

    @model_validator(mode="after")
    def validate_params(self):
        # legacy inherit -> inherit_all
        if getattr(self, 'inherit', None):
            try:
                vals = [bool(x) for x in self.inherit.values()]
                if any(vals):
                    self.inherit_all = True
            except Exception:
                pass
        # Validate presence of correct params branch if provided
        if self.params:
            allowed = {"by_sentences", "by_chunks", "custom"}
            unknown = set(self.params.keys()) - allowed
            if unknown:
                raise ValueError(f"params 仅支持键 {allowed}，发现无效: {unknown}")
            # by_sentences
            if self.strategy == "by_sentences":
                conf = self.params.get("by_sentences") if isinstance(self.params, dict) else None
                if conf is not None:
                    lang = conf.get("lang")
                    if lang and lang not in {"zh","en","auto"}:
                        raise ValueError("by_sentences.lang 只能为 zh|en|auto")
                    max_sent = conf.get("max_sentences")
                    if max_sent is not None and (not isinstance(max_sent, int) or max_sent < 1):
                        raise ValueError("by_sentences.max_sentences 必须为 >=1 的整数")
            # by_chunks
            if self.strategy == "by_chunks":
                conf = self.params.get("by_chunks") if isinstance(self.params, dict) else None
                if conf is None:
                    raise ValueError("by_chunks 策略要求提供 params.by_chunks 配置")
                chunk = conf.get("chunk_size")
                num = conf.get("num_chunks")
                if chunk is None and num is None:
                    raise ValueError("by_chunks 需要 chunk_size 或 num_chunks 之一")
                if chunk is not None and (not isinstance(chunk, int) or chunk < 50):
                    raise ValueError("by_chunks.chunk_size 必须为 >=50 的整数")
                if num is not None and (not isinstance(num, int) or num < 1):
                    raise ValueError("by_chunks.num_chunks 必须为 >=1 的整数")
            # custom
            if self.strategy == "custom":
                conf = self.params.get("custom") if isinstance(self.params, dict) else None
                if conf is None:
                    raise ValueError("custom 策略要求提供 params.custom 配置")
                instr = conf.get("instruction")
                if not instr or not isinstance(instr, str):
                    raise ValueError("custom.instruction 必须提供且为字符串")
                max_splits = conf.get("max_splits")
                if max_splits is not None and (not isinstance(max_splits, int) or max_splits < 1):
                    raise ValueError("custom.max_splits 必须为 >=1 的整数")
        return self

class LockPolicy(BaseModel):
    allow: Optional[List[Op]] = None
    deny: Optional[List[Op]] = None
    reviewers: Optional[List[str]] = None
    expires: Optional[str] = None

    @model_validator(mode="after")
    def validate_policy(self):
        if self.allow is not None and not isinstance(self.allow, list):
            raise ValueError("policy.allow 必须是操作列表")
        if self.deny is not None and not isinstance(self.deny, list):
            raise ValueError("policy.deny 必须是操作列表")
        if self.reviewers is not None and not isinstance(self.reviewers, list):
            raise ValueError("policy.reviewers 必须是字符串列表")
        if self.expires:
            try:
                from datetime import datetime

                datetime.fromisoformat(self.expires.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError("policy.expires 必须是有效的ISO8601格式时间")
        return self


class LockArgs(BaseModel):
    mode: Literal["read_only","no_delete","append_only","disabled","custom"] = "read_only"
    reason: Optional[str] = None
    policy: Optional[LockPolicy] = None

    @model_validator(mode="after")
    def validate_custom_mode(self):
        if self.mode == "custom" and self.policy is None:
            raise ValueError("Lock 模式为 custom 时必须提供 policy")
        return self

    def is_read_only(self) -> bool:
        return self.mode == "read_only"

class ExpireArgs(BaseModel):
    ttl: Optional[str] = None
    expire_at: Optional[str] = None
    on_expire: Literal["soft_delete","hard_delete","archive","none"] = "soft_delete"
    reason: Optional[str] = None

    @model_validator(mode="after")
    def _one_of(self):
        if not ((self.ttl is not None) ^ (self.expire_at is not None)):
            raise ValueError("Expire 操作必须且只能提供以下一种：ttl（生存时间） | expire_at（过期日期）")
        if self.expire_at:
            try:
                from datetime import datetime

                datetime.fromisoformat(self.expire_at.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"过期日期格式错误: '{self.expire_at}' 不是有效的ISO8601格式")
        return self

class IR(BaseModel):
    stage: Stage
    op: Op
    target: Optional[Target] = None
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
        if self.op in enc_ops and self.stage != "ENC":
            raise ValueError(f"操作类型 {self.op} 需要在 ENC 阶段执行")
        if self.op in sto_ops and self.stage != "STO":
            raise ValueError(f"操作类型 {self.op} 需要在 STO 阶段执行")
        if self.op in ret_ops and self.stage != "RET":
            raise ValueError(f"操作类型 {self.op} 需要在 RET 阶段执行")
        return self

    @model_validator(mode="after")
    def _sto_safety(self):
        if self.stage == "STO" and self.target:
            # ids: fine; filter/search require limit; all requires dry_run or confirmation
            if isinstance(self.target, Target):
                if self.target.filter is not None and (self.target.filter.limit is None):
                    raise ValueError("STO 阶段使用 target.filter 时必须提供 limit 以保障安全")
                if self.target.search is not None and (self.target.search.limit is None):
                    raise ValueError("STO 阶段使用 target.search 时必须提供 limit 以保障安全")
                if self.target.all:
                    if not (self.meta and (self.meta.dry_run or getattr(self.meta, 'confirmation', False))):
                        raise ValueError("STO 阶段使用 target.all 时，必须设置 meta.dry_run=true 或 meta.confirmation=true")
        return self

    @model_validator(mode="after")
    def _ret_safety(self):
        if self.op == "Retrieve" and self.target is None:
            raise ValueError("Retrieve 操作必须提供 target")
        if self.stage == "RET" and isinstance(self.target, Target) and self.target.all:
            if not (self.meta and getattr(self.meta, "confirmation", False)):
                raise ValueError("RET 阶段使用 target.all 时，必须设置 meta.confirmation=true")
        return self

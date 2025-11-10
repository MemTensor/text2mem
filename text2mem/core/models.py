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
                raise ValueError(f"Invalid timestamp format: '{v}' is not a valid ISO8601 format")
        return v

class Facets(BaseModel):
    model_config = {"extra": "allow"}  # Allow extra fields
    
    subject: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    topic: Optional[str] = None
    
    @model_validator(mode="after")
    def validate_non_empty(self):
        # Check if any field (including extra fields) has a value
        # Use model_dump to get all fields (including extra fields)
        all_fields = self.model_dump(exclude_none=True)
        if not all_fields:
            raise ValueError("Facets must provide at least one field")
        if self.time:
            try:
                from datetime import datetime
                datetime.fromisoformat(self.time.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid time format: '{self.time}' is not a valid ISO8601 format")
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
            raise ValueError("limit must be greater than or equal to 1")
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
            raise ValueError("Incomplete time range settings. Please provide: (1) start+end OR (2) relative+amount+unit")
        if abs_ok and rel_ok:
            raise ValueError("Conflicting time range settings. Please provide only one set: (1) start+end OR (2) relative+amount+unit")
        if (self.start is not None and self.end is None) or (self.end is not None and self.start is None):
            raise ValueError("When using absolute time range, both start and end must be provided")
        if (self.relative is not None or self.unit is not None) and self.amount is None:
            raise ValueError("When using relative time range, amount must be provided")
        if self.amount is not None and (self.relative is None or self.unit is None):
            raise ValueError("When using relative time range, both relative and unit must be provided")
        return self

class SearchIntent(BaseModel):
    query: Optional[str] = None
    vector: Optional[List[float]] = None

    @model_validator(mode="after")
    def _one_of(self):
        if not ((self.query is not None) ^ (self.vector is not None)):
            raise ValueError("search.intent must set either query OR vector, but not both")
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
            raise ValueError("target must choose exactly one of: ids | filter | search | all")
        if has_ids and (has_filter or has_search or has_all):
            raise ValueError("target must choose exactly one of: ids | filter | search | all")
        if not (has_ids or has_filter or has_search or has_all):
            raise ValueError("target must choose exactly one of: ids | filter | search | all")
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
            raise ValueError("payload must contain exactly one of: text | url | structured")
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
    weight: Optional[float] = None
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
                raise ValueError(f"Invalid time format: '{self.time}' is not a valid ISO8601 format")
        return self
    

class LabelArgs(BaseModel):
    tags: Optional[List[str]] = None
    facets: Optional[Facets] = None
    auto_generate_tags: Optional[bool] = False
    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.tags and not self.facets and not self.auto_generate_tags:
            raise ValueError("Label operation requires at least one of: tags, facets, or auto_generate_tags")
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
            raise ValueError("Update.set must contain at least one field to update")
        return self
    @model_validator(mode="after")
    def _validate_weight_range(self):
        if self.weight is not None:
            if not (0.0 <= self.weight <= 1.0):
                raise ValueError("Update.set.weight must be in range [0,1]")
        return self
    

class UpdateArgs(BaseModel):
    set: UpdateSet
    @model_validator(mode="after")
    def validate_updates(self):
        if not self.set:
            raise ValueError("Update operation must specify at least one field to update")
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
            raise ValueError("Promote operation requires at least one of: weight (absolute) | weight_delta (adjustment) | remind")
        elif provided > 1:
            raise ValueError("Promote operation must specify only one of: weight (absolute) | weight_delta (adjustment) | remind")
        if self.remind and "rrule" not in self.remind:
            raise ValueError("remind must contain rrule field")
        return self
    @model_validator(mode="after")
    def _validate_weight_range(self):
        if self.weight is not None:
            if not (0.0 <= self.weight <= 1.0):
                raise ValueError("Promote.weight must be in range [0,1]")
        if self.weight_delta is not None:
            try:
                delta = float(self.weight_delta)
            except (TypeError, ValueError):
                raise ValueError("Promote.weight_delta must be numeric")
            if not (-1.0 <= delta <= 1.0):
                raise ValueError("Promote.weight_delta should be in range [-1,1] to avoid weight overflow")
        return self

class DemoteArgs(BaseModel):
    archive: Optional[bool] = None
    weight: Optional[float] = None
    weight_delta: Optional[float] = None
    @model_validator(mode="after")
    def validate_operations(self):
        provided = sum(1 for v in [self.archive is not None, self.weight is not None, self.weight_delta is not None] if v)
        if provided == 0:
            raise ValueError("Demote operation requires at least one of: archive | weight (absolute) | weight_delta (adjustment)")
        if provided > 1:
            raise ValueError("Demote operation must specify only one of: archive | weight (absolute) | weight_delta (adjustment)")
        return self
    @model_validator(mode="after")
    def _validate_weight_range(self):
        if self.weight is not None:
            if not (0.0 <= self.weight <= 1.0):
                raise ValueError("Demote.weight must be in range [0,1]")
        if self.weight_delta is not None:
            try:
                delta = float(self.weight_delta)
            except (TypeError, ValueError):
                raise ValueError("Demote.weight_delta must be numeric")
            if not (-1.0 <= delta <= 1.0):
                raise ValueError("Demote.weight_delta should be in range [-1,1] to avoid weight overflow")
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
                raise ValueError(f"include contains invalid field: '{field}'. Allowed fields: {', '.join(allowed_fields)}")
        return v

class SummarizeArgs(BaseModel):
    focus: Optional[str] = None
    max_tokens: int = 256
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1:
            raise ValueError("max_tokens must be at least 1")
        if v > 2000:
            raise ValueError("max_tokens should not exceed 2000, consider using split summarization")
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
                raise ValueError(f"params only supports keys {allowed}, found invalid: {unknown}")
            # by_sentences
            if self.strategy == "by_sentences":
                conf = self.params.get("by_sentences") if isinstance(self.params, dict) else None
                if conf is not None:
                    lang = conf.get("lang")
                    if lang and lang not in {"zh","en","auto"}:
                        raise ValueError("by_sentences.lang must be one of: zh|en|auto")
                    max_sent = conf.get("max_sentences")
                    if max_sent is not None and (not isinstance(max_sent, int) or max_sent < 1):
                        raise ValueError("by_sentences.max_sentences must be an integer >= 1")
            # by_chunks
            if self.strategy == "by_chunks":
                conf = self.params.get("by_chunks") if isinstance(self.params, dict) else None
                if conf is None:
                    raise ValueError("by_chunks strategy requires params.by_chunks configuration")
                chunk = conf.get("chunk_size")
                num = conf.get("num_chunks")
                if chunk is None and num is None:
                    raise ValueError("by_chunks requires either chunk_size or num_chunks")
                if chunk is not None and (not isinstance(chunk, int) or chunk < 50):
                    raise ValueError("by_chunks.chunk_size must be an integer >= 50")
                if num is not None and (not isinstance(num, int) or num < 1):
                    raise ValueError("by_chunks.num_chunks must be an integer >= 1")
            # custom
            if self.strategy == "custom":
                conf = self.params.get("custom") if isinstance(self.params, dict) else None
                if conf is None:
                    raise ValueError("custom strategy requires params.custom configuration")
                instr = conf.get("instruction")
                if not instr or not isinstance(instr, str):
                    raise ValueError("custom.instruction must be provided and be a string")
                max_splits = conf.get("max_splits")
                if max_splits is not None and (not isinstance(max_splits, int) or max_splits < 1):
                    raise ValueError("custom.max_splits must be an integer >= 1")
        return self

class LockPolicy(BaseModel):
    allow: Optional[List[Op]] = None
    deny: Optional[List[Op]] = None
    reviewers: Optional[List[str]] = None
    expires: Optional[str] = None

    @model_validator(mode="after")
    def validate_policy(self):
        if self.allow is not None and not isinstance(self.allow, list):
            raise ValueError("policy.allow must be a list of operations")
        if self.deny is not None and not isinstance(self.deny, list):
            raise ValueError("policy.deny must be a list of operations")
        if self.reviewers is not None and not isinstance(self.reviewers, list):
            raise ValueError("policy.reviewers must be a list of strings")
        if self.expires:
            try:
                from datetime import datetime

                datetime.fromisoformat(self.expires.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError("policy.expires must be a valid ISO8601 format timestamp")
        return self


class LockArgs(BaseModel):
    mode: Literal["read_only","no_delete","append_only","disabled","custom"] = "read_only"
    reason: Optional[str] = None
    policy: Optional[LockPolicy] = None

    @model_validator(mode="after")
    def validate_custom_mode(self):
        if self.mode == "custom" and self.policy is None:
            raise ValueError("Lock mode 'custom' requires a policy to be provided")
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
            raise ValueError("Expire operation must provide exactly one of: ttl | expire_at")
        if self.expire_at:
            try:
                from datetime import datetime

                datetime.fromisoformat(self.expire_at.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid expiration date format: '{self.expire_at}' is not a valid ISO8601 format")
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
            raise ValueError(f"Operation {self.op} must be executed in ENC stage")
        if self.op in sto_ops and self.stage != "STO":
            raise ValueError(f"Operation {self.op} must be executed in STO stage")
        if self.op in ret_ops and self.stage != "RET":
            raise ValueError(f"Operation {self.op} must be executed in RET stage")
        return self

    @model_validator(mode="after")
    def _sto_safety(self):
        if self.stage == "STO" and self.target:
            # ids/filter/search: fine (no limit required); all requires dry_run or confirmation
            if isinstance(self.target, Target):
                # Removed: filter/search limit requirements - limit is optional
                # Users can choose to add limit for safety, but it's not mandatory
                if self.target.all:
                    if not (self.meta and (self.meta.dry_run or getattr(self.meta, 'confirmation', False))):
                        raise ValueError("STO stage using target.all requires meta.dry_run=true or meta.confirmation=true")
        return self

    @model_validator(mode="after")
    def _ret_safety(self):
        if self.op == "Retrieve" and self.target is None:
            raise ValueError("Retrieve operation must provide a target")
        if self.stage == "RET" and isinstance(self.target, Target) and self.target.all:
            if not (self.meta and getattr(self.meta, "confirmation", False)):
                raise ValueError("RET stage using target.all requires meta.confirmation=true")
        return self

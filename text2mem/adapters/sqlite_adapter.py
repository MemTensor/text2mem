# text2mem/adapters/sqlite_adapter.py
from __future__ import annotations
import json, logging, re, sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple, Optional
from text2mem.adapters.base import BaseAdapter, ExecutionResult
from text2mem.core.models import IR, EncodeArgs, UpdateArgs, DeleteArgs, RetrieveArgs, Target, Filters
from text2mem.core.models import LabelArgs, PromoteArgs, DemoteArgs, SummarizeArgs
from text2mem.core.models import MergeArgs, SplitArgs, LockArgs, ExpireArgs # , ClarifyArgs
from text2mem.services.models_service import ModelsService, get_models_service

logger = logging.getLogger(__name__)


DDL = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Content
    text TEXT,
    type TEXT,

    -- Facets and labels
    subject TEXT,
    time TEXT,
    location TEXT,
    topic TEXT,
    tags TEXT,            -- JSON array
    facets TEXT,          -- JSON object {subject,time,location,topic}

    -- Importance
    weight REAL,

    -- Embedding
    embedding TEXT,       -- JSON array, 原型先存 json
    embedding_dim INTEGER,        -- 嵌入向量维度（用于兼容性检索）
    embedding_model TEXT,         -- 嵌入模型名
    embedding_provider TEXT,      -- 嵌入提供商（ollama/openai/dummy等）

    -- Provenance & lifecycle
    source TEXT,
    auto_frequency TEXT,
    next_auto_update_at TEXT,
    expire_at TEXT,
    expire_action TEXT,
    expire_reason TEXT,

    -- Lock metadata
    lock_mode TEXT,
    lock_reason TEXT,
    lock_policy TEXT,
    lock_expires TEXT,

    -- Lineage (optional for merge/split audits)
    lineage_parents TEXT,    -- JSON array of ancestor IDs
    lineage_children TEXT,   -- JSON array of descendant IDs

    -- Permissions
    read_perm_level TEXT,
    write_perm_level TEXT,
    read_whitelist TEXT,  -- JSON array
    read_blacklist TEXT,
    write_whitelist TEXT,
    write_blacklist TEXT,

    -- Flags
    deleted INTEGER DEFAULT 0
);
"""

MIGRATION_COLUMNS: dict[str, str] = {
    "embedding_dim": "INTEGER",
    "embedding_model": "TEXT",
    "embedding_provider": "TEXT",
    "expire_action": "TEXT",
    "expire_reason": "TEXT",
    "lock_mode": "TEXT",
    "lock_reason": "TEXT",
    "lock_policy": "TEXT",
    "lock_expires": "TEXT",
    "lineage_parents": "TEXT",
    "lineage_children": "TEXT",
}


def _json(obj):
    return json.dumps(obj, ensure_ascii=False) if obj is not None else None

class SQLiteAdapter(BaseAdapter):
    def __init__(self, path: str = ":memory:", models_service: ModelsService = None, virtual_now=None):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DDL)
        self.models_service = models_service or get_models_service()
        self.virtual_now = virtual_now  # 虚拟"当前时间"，用于测试相对时间查询
        
        # Load search configuration from ModelConfig
        from text2mem.core.config import ModelConfig
        config = ModelConfig.from_env()
        self.search_alpha = config.search_alpha
        self.search_beta = config.search_beta
        self.search_phrase_bonus = config.search_phrase_bonus
        self.search_default_limit = config.search_default_limit
        self.search_max_limit = config.search_max_limit
        self.search_default_k = config.search_default_k

        self._ensure_schema_columns()

    def _ensure_schema_columns(self) -> None:
        """Perform lightweight migrations to backfill newly added columns."""

        try:
            cur = self.conn.execute("PRAGMA table_info(memory)")
            existing = {row[1] for row in cur.fetchall()}
        except sqlite3.Error as exc:
            logger.warning("无法获取 memory 表结构信息，跳过列迁移: %s", exc)
            return

        pending = {
            column: definition
            for column, definition in MIGRATION_COLUMNS.items()
            if column not in existing
        }

        if not pending:
            return

        for column, definition in pending.items():
            sql = f"ALTER TABLE memory ADD COLUMN {column} {definition}"
            try:
                self.conn.execute(sql)
            except sqlite3.OperationalError as exc:
                logger.warning("新增列失败 %s: %s", column, exc)
        self.conn.commit()

    # ---------- lock helpers ----------
    def _lock_perm_values(self, mode: str) -> tuple[Optional[str], Optional[str]]:
        if mode == "read_only":
            return "locked_read_only", "locked_no_write"
        if mode == "no_delete":
            return "locked_no_delete", "locked_no_delete"
        if mode == "append_only":
            return "locked_append_only", "locked_append_only"
        if mode == "custom":
            return "locked_custom", "locked_custom"
        return None, None

    def _parse_lock_policy(self, policy_json: str | None) -> Dict[str, Any]:
        if not policy_json:
            return {}
        try:
            data = json.loads(policy_json)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _lock_is_expired(self, expires: str | None) -> bool:
        if not expires:
            return False
        try:
            ts = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        except ValueError:
            return False
        now = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts <= now

    def _assert_operation_allowed(self, ir: IR, where: str, params: tuple[Any, ...]):
        """Raise if any targeted row is locked against the current operation."""
        if ir.op == "Lock":
            return
        sql = f"SELECT id, lock_mode, lock_policy, lock_expires FROM memory WHERE {where}"
        rows = self.conn.execute(sql, params).fetchall()
        if not rows:
            return
        actor = getattr(ir.meta, "actor", None) if ir.meta else None
        for row in rows:
            row_dict = dict(row)
            mode = row_dict.get("lock_mode")
            if not mode or mode == "disabled":
                continue
            expires = row_dict.get("lock_expires")
            if self._lock_is_expired(expires):
                continue
            policy = self._parse_lock_policy(row_dict.get("lock_policy"))

            # custom reviewer check
            reviewers = policy.get("reviewers") if isinstance(policy.get("reviewers"), list) else None
            if reviewers and actor not in reviewers:
                raise PermissionError(f"记忆 {row_dict['id']} 已锁定，需要 reviewer 才能执行 {ir.op}")

            if mode == "read_only":
                raise PermissionError(f"记忆 {row_dict['id']} 已锁定为只读，无法执行 {ir.op}")
            if mode == "no_delete" and ir.op == "Delete":
                raise PermissionError(f"记忆 {row_dict['id']} 已锁定禁止删除")
            if mode == "append_only" and ir.op in {"Update","Delete","Promote","Demote","Merge","Split","Lock","Expire"}:
                raise PermissionError(f"记忆 {row_dict['id']} 锁定为 append_only，禁止执行 {ir.op}")
            if mode == "custom":
                allow = policy.get("allow") if isinstance(policy.get("allow"), list) else None
                deny = policy.get("deny") if isinstance(policy.get("deny"), list) else None
                if allow and ir.op not in allow:
                    raise PermissionError(f"记忆 {row_dict['id']} 自定义策略仅允许 {allow}，不允许 {ir.op}")
                if deny and ir.op in deny:
                    raise PermissionError(f"记忆 {row_dict['id']} 自定义策略禁止 {ir.op}")

    def _parse_iso_duration(self, duration: str) -> timedelta:
        pattern = r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?"
        match = re.fullmatch(pattern, duration)
        if not match:
            raise ValueError(f"无效的 ISO8601 时长: {duration}")
        years, months, weeks, days, hours, minutes, seconds = match.groups()
        total = timedelta(0)
        if years:
            total += timedelta(days=365 * int(years))
        if months:
            total += timedelta(days=30 * int(months))
        if weeks:
            total += timedelta(weeks=int(weeks))
        if days:
            total += timedelta(days=int(days))
        if hours:
            total += timedelta(hours=int(hours))
        if minutes:
            total += timedelta(minutes=int(minutes))
        if seconds:
            total += timedelta(seconds=int(seconds))
        return total

    # ---------- helpers ----------
    def _where_from_target(self, target: Target | None, require_limit: bool = True) -> Tuple[str, tuple]:
        """Translate Target(ids|filter|search|all) into SQL WHERE and params.

        For STO-stage ops using target.search, we resolve search to top-K IDs via
        semantic similarity and return an id IN (...) clause. Retrieve should
        not call this with search present; it handles search itself.
        
        Args:
            target: Target selector (ids/filter/search/all)
            require_limit: If True, requires explicit limit for search (STO ops).
                          If False, allows fallback to overrides.k (RET ops).
        """
        if target is None:
            return "1=1", ()

        # search: resolve to IDs for non-Retrieve ops; allow intersection with filter/ids
        if target.search is not None:
            try:
                ids = self._resolve_search_ids(target, require_limit=require_limit)
            except Exception as e:
                # Log the error for debugging
                logger.warning(f"Failed to resolve search IDs: {e}")
                ids = []
            if not ids:
                return "0=1", ()  # no matches; guard wide writes
            placeholders = ",".join(["?"] * len(ids))
            base_ids_sql = f"id IN ({placeholders})"
            clauses: list[str] = [base_ids_sql]
            params: list[Any] = list(ids)
            # Merge additional filters (excluding search)
            if target.ids is not None or target.filter is not None or target.all:
                base_target = Target(ids=target.ids, filter=target.filter, all=target.all, search=None)  # type: ignore
                base_where, base_params = self._where_from_target(base_target, require_limit=require_limit)
                if base_where and base_where != "1=1":
                    clauses.append(f"({base_where})")
                    params.extend(list(base_params))
            return " AND ".join(clauses), tuple(params)

        clauses: list[str] = []
        params: list[Any] = []

        # ids: 单个或列表
        if target.ids is not None:
            ids = target.ids
            if isinstance(ids, list):
                placeholders = ",".join(["?"] * len(ids))
                clauses.append(f"id IN ({placeholders})")
                params.extend(ids)
            else:
                clauses.append("id = ?")
                params.append(ids)

        # filter: 支持 has_tags / not_tags / type / time_range（相对或绝对）以及扩展字段
        if target.filter is not None:
            f: Filters = target.filter
            if f.has_tags:
                for t in f.has_tags:
                    clauses.append("tags LIKE ?")
                    params.append(f'%"{t}"%')
            if f.not_tags:
                for t in f.not_tags:
                    clauses.append("(tags IS NULL OR tags NOT LIKE ?)")
                    params.append(f'%"{t}"%')
            if f.type:
                clauses.append("type = ?")
                params.append(f.type)
            if f.time_range:
                tr = f.time_range
                if getattr(tr, 'start', None) and getattr(tr, 'end', None):
                    clauses.append("time >= ? AND time <= ?")
                    params.extend([tr.start, tr.end])
                elif getattr(tr, 'relative', None) and getattr(tr, 'amount', None) and getattr(tr, 'unit', None):
                    from datetime import datetime, timedelta, timezone
                    # 使用虚拟时间（如果提供）或实际当前时间
                    now = self.virtual_now if self.virtual_now else datetime.now(timezone.utc)
                    amount = int(tr.amount)
                    unit = tr.unit
                    delta = None
                    if unit == 'minutes':
                        delta = timedelta(minutes=amount)
                    elif unit == 'hours':
                        delta = timedelta(hours=amount)
                    elif unit == 'days':
                        delta = timedelta(days=amount)
                    elif unit == 'weeks':
                        delta = timedelta(weeks=amount)
                    elif unit == 'months':
                        delta = timedelta(days=30*amount)
                    elif unit == 'years':
                        delta = timedelta(days=365*amount)
                    if delta is not None:
                        if tr.relative == 'last':
                            start = (now - delta).isoformat()
                            end = now.isoformat()
                        else:  # 'next'
                            start = now.isoformat()
                            end = (now + delta).isoformat()
                        clauses.append("time >= ? AND time <= ?")
                        params.extend([start, end])
            if getattr(f, 'subject', None):
                clauses.append("subject = ?")
                params.append(f.subject)
            if getattr(f, 'location', None):
                clauses.append("location = ?")
                params.append(f.location)
            if getattr(f, 'topic', None):
                clauses.append("topic = ?")
                params.append(f.topic)
            if getattr(f, 'facet_subject', None):
                clauses.append("subject = ?")
                params.append(f.facet_subject)
            if getattr(f, 'facet_location', None):
                clauses.append("location = ?")
                params.append(f.facet_location)
            if getattr(f, 'facet_topic', None):
                clauses.append("topic = ?")
                params.append(f.facet_topic)
            if getattr(f, 'facet_time', None):
                clauses.append("time = ?")
                params.append(f.facet_time)
            if getattr(f, 'weight_gte', None) is not None:
                clauses.append("weight >= ?")
                params.append(f.weight_gte)
            if getattr(f, 'weight_lte', None) is not None:
                clauses.append("weight <= ?")
                params.append(f.weight_lte)
            if getattr(f, 'expire_before', None):
                clauses.append("expire_at IS NOT NULL AND expire_at < ?")
                params.append(f.expire_before)
            if getattr(f, 'expire_after', None):
                clauses.append("expire_at IS NOT NULL AND expire_at > ?")
                params.append(f.expire_after)

        # all: 不加任何 where 条件
        if target.all:
            pass

        if not clauses:
            return "1=1", ()
        return " AND ".join(clauses), tuple(params)

    # ---------- op handlers ----------
    def _keyword_score(self, text: str | None, query: str | None) -> tuple[float, bool]:
        """Compute a simple keyword score in [0,1] and whether exact phrase matched.

        - Exact phrase (case-insensitive) -> score 1.0 and exact=True
        - Otherwise, token overlap ratio: (#tokens present in text)/(#tokens in query)
        """
        if not text or not query:
            return 0.0, False
        t = text.lower()
        q = query.lower().strip()
        if not q:
            return 0.0, False
        exact = q in t
        if exact:
            return 1.0, True
        tokens = [tok for tok in re.split(r"\W+", q) if tok]
        if not tokens:
            return 0.0, False
        hits = sum(1 for tok in tokens if tok in t)
        return (hits / len(tokens)), False
    def _resolve_search_ids(self, target: Target, require_limit: bool = True) -> list[int]:
        """Compute top-K memory IDs using semantic search from Target.search.

        Reuses the same approach as _exec_retrieve but returns a list of IDs,
        suitable for STO-stage WHERE clause construction.
        
        Args:
            target: Target object with search configuration
            require_limit: If True, requires explicit limit for safety (default for STO ops).
                          If False, uses overrides.k or default 10 (for RET ops like Summarize).
        """
        search = target.search
        if search is None:
            return []
        intent = search.intent
        
        # Determine k value
        if getattr(search, 'limit', None):
            # Explicit limit provided
            try:
                k = int(search.limit)  # type: ignore
            except Exception:
                k = 10
        elif not require_limit:
            # For RET operations: fallback to overrides.k or default
            if search.overrides and getattr(search.overrides, 'k', None):
                k = search.overrides.k
            else:
                k = 10
        else:
            # For STO operations: require explicit limit for safety
            raise ValueError("target.search.limit is required for write operations")
        
        # Apply any filter/all constraints in conjunction with search
        # (build a base WHERE from filter/ids/all minus search)
        if target.ids or target.filter or target.all:
            base_target = Target(ids=target.ids, filter=target.filter, all=target.all, search=None)  # type: ignore
            where, params = self._where_from_target(base_target)
        else:
            where, params = ("1=1", ())
        where = f"({where}) AND deleted=0"  # ignore deleted
        select_sql = f"SELECT id, text, embedding, embedding_dim FROM memory WHERE {where}"
        rows = self.conn.execute(select_sql, params).fetchall()

        memory_vectors = []
        try:
            target_dim = self.models_service.embedding_model.get_dimension()  # type: ignore
        except Exception:
            target_dim = None
        for row in rows:
            embedding = json.loads(row["embedding"]) if row["embedding"] else None
            if embedding:
                row_dim = row["embedding_dim"] if row["embedding_dim"] is not None else (len(embedding) if embedding else None)
                if target_dim is None or row_dim == target_dim:
                    memory_vectors.append({"id": row["id"], "text": row["text"], "vector": embedding})

        if not memory_vectors:
            return []

        # Choose query vector
        if intent.vector is not None:
            query_vector = intent.vector
            if target_dim is not None and len(query_vector) != target_dim:
                return []
            # score manually
            scored = []
            for item in memory_vectors:
                try:
                    sim = self.models_service.compute_similarity(query_vector, item["vector"])  # type: ignore
                except Exception:
                    continue
                # hybrid score: semantic + keyword
                qtext = getattr(intent, 'query', None)
                kw, exact = self._keyword_score(item.get("text"), qtext)
                alpha = self.search_alpha
                beta = self.search_beta
                phrase_bonus = self.search_phrase_bonus
                final_sim = alpha * sim + beta * kw + (phrase_bonus if exact else 0.0)
                scored.append({**item, "similarity": min(1.0, final_sim)})
            scored.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            top = scored[:k]
        else:
            # use service semantic_search
            base = self.models_service.semantic_search(intent.query, memory_vectors, k=k)  # type: ignore
            # re-rank with keyword boost
            alpha = self.search_alpha
            beta = self.search_beta
            phrase_bonus = self.search_phrase_bonus
            rescored = []
            for r in base:
                kw, exact = self._keyword_score(r.get("text"), intent.query)
                sim = r.get("similarity", 0)
                final_sim = alpha * sim + beta * kw + (phrase_bonus if exact else 0.0)
                rescored.append({**r, "similarity": min(1.0, final_sim)})
            rescored.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            top = rescored[:k]
        return [t["id"] for t in top]
    def _exec_encode(self, ir: IR, args: EncodeArgs) -> ExecutionResult:
        text_val = args.payload.text or (json.dumps(args.payload.structured, ensure_ascii=False) if args.payload.structured else None)

        # 自动生成嵌入向量（如果未显式跳过）。安全策略：不接受外部直接提供的 embedding。
        embedding_val = None
        embedding_dim = None
        embedding_model_name = None
        embedding_provider = None
        if text_val and not bool(getattr(args, 'skip_embedding', False)):
            # 使用模型服务生成嵌入
            embedding_result = self.models_service.encode_memory(text_val)
            embedding_val = embedding_result.vector
            embedding_dim = getattr(embedding_result, "dimension", None) or (len(embedding_val) if embedding_val else None)
            embedding_model_name = getattr(embedding_result, "model_name", None) or getattr(embedding_result, "model", None)
            # 尝试从模型实例推断提供商
            try:
                em = getattr(self.models_service, "embedding_model", None)
                if em is not None:
                    # 优先使用模型自带属性
                    embedding_provider = getattr(em, "provider", None) or getattr(em, "provider_name", None)
                    if not embedding_provider:
                        cls = em.__class__.__name__.lower()
                        if "ollama" in cls:
                            embedding_provider = "ollama"
                        elif "openai" in cls:
                            embedding_provider = "openai"
                        elif "dummy" in cls:
                            embedding_provider = "dummy"
                        else:
                            embedding_provider = "unknown"
            except Exception:
                embedding_provider = None

        sql = """
        INSERT INTO memory (text,type,tags,facets,time,subject,location,topic,embedding,embedding_dim,embedding_model,embedding_provider,source,
                                auto_frequency,expire_at,next_auto_update_at,
                                read_perm_level,write_perm_level,
                                read_whitelist,read_blacklist,write_whitelist,write_blacklist,weight,deleted)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """
        params = (
            text_val,
            args.type,
            _json(args.tags),
            _json(args.facets.model_dump(exclude_none=True) if args.facets else None),
            args.time or (args.facets.time if args.facets and args.facets.time else None),
            args.subject or (args.facets.subject if args.facets and args.facets.subject else None),
            args.location or (args.facets.location if args.facets and args.facets.location else None),
            args.topic or (args.facets.topic if args.facets and args.facets.topic else None),
            _json(embedding_val),
            embedding_dim,
            embedding_model_name,
            embedding_provider,
            args.source,
            args.auto_frequency,
            args.expire_at,
            args.next_auto_update_at,
            args.read_perm_level,
            args.write_perm_level,
            _json(args.read_whitelist),
            _json(args.read_blacklist),
            _json(args.write_whitelist),
            _json(args.write_blacklist),
            args.weight  # weight
        )
        if ir.meta and ir.meta.dry_run:
            return {
                "sql": sql,
                "params": params,
                "generated_embedding": bool((not bool(getattr(args, 'skip_embedding', False)))),
                "embedding_dim": embedding_dim,
                "embedding_model": embedding_model_name,
                "embedding_provider": embedding_provider,
            }
        cur = self.conn.execute(sql, params); self.conn.commit()
        return {
            "inserted_id": cur.lastrowid,
            "generated_embedding": bool((not bool(getattr(args, 'skip_embedding', False)))),
            "embedding_dim": embedding_dim,
            "embedding_model": embedding_model_name,
            "embedding_provider": embedding_provider,
        }

    def _exec_label(self, ir: IR, args: LabelArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        # avoid soft-deleted
        wh = f"({wh}) AND deleted=0"
        try:
            self._assert_operation_allowed(ir, wh, ps)
        except PermissionError as err:
            raise ValueError(str(err))
        updates, vals = [], []
        # Determine language preference: meta.lang -> env TEXT2MEM_LANG -> en
        import os
        lang_pref = (
            ir.meta.lang.lower() if getattr(ir, "meta", None) and ir.meta.lang else os.getenv("TEXT2MEM_LANG", "en").lower()
        )
        
        # 如果没有提供标签但有auto_generate_tags，自动生成标签
        tags_to_use = args.tags
        if not tags_to_use and args.auto_generate_tags:
            # 获取记忆内容来生成标签
            select_sql = f"SELECT text, tags FROM memory WHERE {wh}"
            if not (ir.meta and ir.meta.dry_run):
                rows = self.conn.execute(select_sql, ps).fetchall()
                if rows:
                    existing_tags = []
                    for row in rows:
                        if row["tags"]:
                            existing_tags.extend(json.loads(row["tags"]))
                    
                    # 使用第一行内容生成标签
                    text_content = rows[0]["text"]
                    if text_content:
                        label_result = self.models_service.suggest_labels(
                            text_content,
                            existing_labels=list(set(existing_tags)),
                            lang=lang_pref,
                        )
                        # 解析生成的标签
                        generated_labels = [tag.strip() for tag in label_result.text.split(',')]
                        tags_to_use = generated_labels
        
        # 处理 tags
        if tags_to_use:
            updates.append("tags = ?")
            vals.append(_json(tags_to_use))
        
        # 处理 facets
        if args.facets:
            # 先获取现有 facets
            select_sql = f"SELECT facets FROM memory WHERE {wh}"
            if ir.meta and ir.meta.dry_run:
                existing_facets = {}
            else:
                rows = self.conn.execute(select_sql, ps).fetchall()
                if not rows:
                    return {"affected_rows": 0}
                
                # 获取第一行的 facets（作为示例）
                existing_facets = json.loads(rows[0]["facets"]) if rows[0]["facets"] else {}
            
            # 合并 facets
            new_facets = args.facets.model_dump(exclude_none=True)
            merged_facets = {**existing_facets, **new_facets}
            
            updates.append("facets = ?")
            vals.append(_json(merged_facets))
            
            # 更新关联字段
            for key in ["subject", "time", "location", "topic"]:
                if getattr(args.facets, key):
                    updates.append(f"{key} = ?")
                    vals.append(getattr(args.facets, key))
        
        if not updates:
            return {"affected_rows": 0, "message": "No fields to update"}
        
        sql = f"UPDATE memory SET {', '.join(updates)} WHERE {wh}"
        
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": tuple(vals) + ps}
            
        cur = self.conn.execute(sql, tuple(vals) + ps)
        self.conn.commit()
        return {"affected_rows": cur.rowcount}

    def _exec_update(self, ir: IR, args: UpdateArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        # avoid soft-deleted
        wh = f"({wh}) AND deleted=0"
        try:
            self._assert_operation_allowed(ir, wh, ps)
        except PermissionError as err:
            raise ValueError(str(err))
        sets, vals = [], []
        d = args.set.model_dump(exclude_none=True)
        for k, v in d.items():
            col = {"facets":"facets","tags":"tags"}.get(k, k)
            if k in {"tags","facets","read_whitelist","read_blacklist","write_whitelist","write_blacklist"}:
                if k == "facets":
                    src = v if isinstance(v, dict) else {}
                    facets_dict = {kk: vv for kk, vv in src.items() if vv is not None}
                    sets.append("facets=?"); vals.append(_json(facets_dict))
                    for fk in ("subject","time","location","topic"):
                        if fk in facets_dict:
                            sets.append(f"{fk}=?"); vals.append(facets_dict[fk])
                else:
                    sets.append(f"{col}=?"); vals.append(_json(v))
            elif k == "embedding":
                # 拒绝通过 Update 写入embedding，返回安全错误
                raise ValueError("安全策略：禁止通过 Update 直接写入 embedding")
            else:
                if k == "weight":
                    try:
                        v = max(0.0, min(1.0, float(v)))
                    except Exception:
                        pass
                sets.append(f"{col}=?"); vals.append(v)
        sql = f"UPDATE memory SET {', '.join(sets)} WHERE {wh}"
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": tuple(vals)+ps}
        cur = self.conn.execute(sql, tuple(vals)+ps); self.conn.commit()
        return {"updated_rows": cur.rowcount}

    def _exec_promote(self, ir: IR, args: PromoteArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        # avoid soft-deleted
        wh = f"({wh}) AND deleted=0"
        try:
            self._assert_operation_allowed(ir, wh, ps)
        except PermissionError as err:
            raise ValueError(str(err))
        sets, vals = [], []
        
        # 处理 weight 绝对值
        if getattr(args, "weight", None) is not None:
            sets.append("weight = ?")
            w = args.weight
            try:
                w = max(0.0, min(1.0, float(w)))
            except Exception:
                pass
            vals.append(w)
        
        # 处理 weight_delta
        if args.weight_delta is not None:
            # 先加，再夹紧
            sets.append("weight = MIN(1.0, MAX(0.0, COALESCE(weight, 0) + ?))")
            vals.append(args.weight_delta)
        
        # 处理 remind
        if args.remind:
            if "rrule" in args.remind:
                sets.append("auto_frequency = ?")
                vals.append(args.remind["rrule"])
            
            if "until" in args.remind and args.remind["until"]:
                sets.append("expire_at = ?")
                vals.append(args.remind["until"])
        
        if not sets:
            return {"affected_rows": 0, "message": "No fields to update"}
        
        sql = f"UPDATE memory SET {', '.join(sets)} WHERE {wh}"
        
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": tuple(vals) + ps}
            
        cur = self.conn.execute(sql, tuple(vals) + ps)
        self.conn.commit()
        return {"affected_rows": cur.rowcount}

    def _exec_demote(self, ir: IR, args: DemoteArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        # avoid soft-deleted
        wh = f"({wh}) AND deleted=0"
        try:
            self._assert_operation_allowed(ir, wh, ps)
        except PermissionError as err:
            raise ValueError(str(err))
        sets, vals = [], []
        
        # 处理 archive 参数（原型：降级为低权重）
        if args.archive:
            # 原型实现：减小权重（并夹紧）
            sets.append("weight = MAX(0.0, COALESCE(weight, 0) - 1.0)")
        
        # 处理 weight 绝对值
        if getattr(args, "weight", None) is not None:
            sets.append("weight = ?")
            w = args.weight
            try:
                w = max(0.0, min(1.0, float(w)))
            except Exception:
                pass
            vals.append(w)
        
        # 处理 weight_delta
        if args.weight_delta is not None:
            # weight_delta 在 demote 中通常为负值；加后夹紧
            sets.append("weight = MIN(1.0, MAX(0.0, COALESCE(weight, 0) + ?))")
            vals.append(args.weight_delta)
        
        if not sets:
            return {"affected_rows": 0, "message": "No fields to update"}
        
        sql = f"UPDATE memory SET {', '.join(sets)} WHERE {wh}"
        
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": tuple(vals) + ps}
            
        cur = self.conn.execute(sql, tuple(vals) + ps)
        self.conn.commit()
        return {"affected_rows": cur.rowcount}

    def _exec_delete(self, ir: IR, args: DeleteArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        if wh == "0=1":
            final_where = wh
            params: list[Any] = list(ps)
        else:
            clauses: list[str] = []
            params = list(ps)
            if wh and wh != "1=1":
                clauses.append(f"({wh})")
            if args.soft:
                clauses.append("deleted=0")

            def _iso(dt: datetime) -> str:
                return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

            if args.time_range:
                tr = args.time_range
                if getattr(tr, "start", None) and getattr(tr, "end", None):
                    clauses.append("time >= ? AND time <= ?")
                    params.extend([tr.start, tr.end])
                elif getattr(tr, "relative", None) and getattr(tr, "amount", None) and getattr(tr, "unit", None):
                    # 使用虚拟时间（如果提供）或实际当前时间
                    now = self.virtual_now if self.virtual_now else datetime.now(timezone.utc)
                    amount = int(tr.amount)
                    unit = tr.unit
                    delta = None
                    if unit == "minutes":
                        delta = timedelta(minutes=amount)
                    elif unit == "hours":
                        delta = timedelta(hours=amount)
                    elif unit == "days":
                        delta = timedelta(days=amount)
                    elif unit == "weeks":
                        delta = timedelta(weeks=amount)
                    elif unit == "months":
                        delta = timedelta(days=30 * amount)
                    elif unit == "years":
                        delta = timedelta(days=365 * amount)
                    if delta is not None:
                        if tr.relative == "last":
                            start = _iso(now - delta)
                            end = _iso(now)
                        else:  # "next"
                            start = _iso(now)
                            end = _iso(now + delta)
                        clauses.append("time >= ? AND time <= ?")
                        params.extend([start, end])

            if getattr(args, "older_than", None):
                delta = self._parse_iso_duration(args.older_than)
                cutoff = _iso(datetime.now(timezone.utc) - delta)
                clauses.append("time < ?")
                params.append(cutoff)

            final_where = " AND ".join(clauses) if clauses else "1=1"

        try:
            self._assert_operation_allowed(ir, final_where, tuple(params))
        except PermissionError as err:
            raise ValueError(str(err))

        sql = (
            f"UPDATE memory SET deleted=1 WHERE {final_where}"
            if args.soft
            else f"DELETE FROM memory WHERE {final_where}"
        )
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": tuple(params)}
        cur = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return {"affected_rows": cur.rowcount, "soft": args.soft, "reason": args.reason}

    def _exec_summarize(self, ir: IR, args: SummarizeArgs) -> ExecutionResult:
        # For Summarize (RET operation), don't require explicit limit - allow overrides.k fallback
        wh, ps = self._where_from_target(ir.target, require_limit=False)
        
        # 添加忽略已删除
        wh = f"({wh}) AND deleted=0"
        
        # 检索内容
        sql = f"SELECT id, text, topic, subject FROM memory WHERE {wh} ORDER BY time DESC"
        
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": ps}
        
        rows = self.conn.execute(sql, ps).fetchall()
        
        # Language preference
        import os
        lang_pref = (
            ir.meta.lang.lower() if getattr(ir, "meta", None) and ir.meta.lang else os.getenv("TEXT2MEM_LANG", "en").lower()
        )

        if not rows:
            return {"summary": "", "count": 0}
        
        # 使用LLM生成摘要
        texts = []
        for row in rows:
            if row["text"]:
                texts.append(row["text"])
        
        if texts:
            summary_result = self.models_service.generate_summary(
                texts,
                focus=args.focus,
                max_tokens=args.max_tokens,
                lang=lang_pref,
            )
            summary = summary_result.text
            model_name = getattr(summary_result, "model", None)
            usage = getattr(summary_result, "usage", None)
        else:
            summary = "无可摘要的文本内容" if lang_pref == "zh" else "No text available for summarization"
            model_name = None
            usage = None
        
        return {
            "summary": summary,
            "count": len(rows),
            "model_used": True,
            "model": model_name,
            "tokens": usage,
            "focus": args.focus,
            "source_ids": [r["id"] for r in rows]
        }

    def _exec_merge(self, ir: IR, args: MergeArgs) -> ExecutionResult:
        """合并记忆操作（仅支持 merge_into_primary）"""
        wh, ps = self._where_from_target(ir.target)
        where_clause = f"({wh}) AND deleted=0"
        try:
            self._assert_operation_allowed(ir, where_clause, ps)
        except PermissionError as err:
            raise ValueError(str(err))

        # 获取目标记忆
        sql = f"SELECT * FROM memory WHERE {where_clause}"
        rows = [dict(r) for r in self.conn.execute(sql, ps).fetchall()]

        if not rows:
            return {"message": "没有找到需要合并的记忆", "merged_count": 0}

        if len(rows) < 2:
            return {"message": "至少需要2条记忆才能进行合并", "merged_count": 0}

        if ir.meta and ir.meta.dry_run:
            # 预览：若未跳过，将会对主记忆进行重嵌入
            return {"message": f"模拟合并 {len(rows)} 条记忆", "strategy": "merge_into_primary", "would_reembed": (not getattr(args, 'skip_reembedding', False))}

        # 主记忆选择：显式 primary_id 或第一条（默认 "auto" 表示自动）
        if args.primary_id in (None, "auto"):
            primary_id = str(rows[0]["id"])
        else:
            primary_id = str(args.primary_id)
        primary = next((r for r in rows if str(r["id"]) == primary_id), None)
        if not primary:
            return {"error": f"找不到主记忆 ID: {primary_id}", "merged_count": 0}

        # 合并文本内容
        texts = [r.get("text") for r in rows if r.get("text") and str(r["id"]) != primary_id]
        if texts:
            base_text = primary.get("text") or ""
            merged_text = (base_text + ("\n\n" if base_text else "") + "\n".join(texts))
            self.conn.execute("UPDATE memory SET text = ? WHERE id = ?", (merged_text, primary_id))

        # 处理其他子记忆删除方式
        other_ids = [r["id"] for r in rows if str(r["id"]) != primary_id]
        if other_ids:
            if args.soft_delete_children:
                sql_del = "UPDATE memory SET deleted = 1 WHERE id IN ({})".format(",".join("?" * len(other_ids)))
            else:
                sql_del = "DELETE FROM memory WHERE id IN ({})".format(",".join("?" * len(other_ids)))
            self.conn.execute(sql_del, other_ids)

        # 合并提交文本与删除
        self.conn.commit()

        # 合并后重嵌入（除非明确跳过）
        reembedded = False
        if not getattr(args, 'skip_reembedding', False):
            # 读取主记忆当前文本
            try:
                row = self.conn.execute("SELECT id, text FROM memory WHERE id = ?", (primary_id,)).fetchone()
                primary_text = row["text"] if row else None
                if primary_text:
                    emb_res = self.models_service.encode_memory(primary_text)
                    emb_val = emb_res.vector
                    emb_dim = getattr(emb_res, "dimension", None) or (len(emb_val) if emb_val else None)
                    emb_model = getattr(emb_res, "model_name", None) or getattr(emb_res, "model", None)
                    # 尝试推断提供商
                    emb_provider = None
                    try:
                        em = getattr(self.models_service, "embedding_model", None)
                        if em is not None:
                            emb_provider = getattr(em, "provider", None) or getattr(em, "provider_name", None)
                            if not emb_provider:
                                cls = em.__class__.__name__.lower()
                                if "ollama" in cls:
                                    emb_provider = "ollama"
                                elif "openai" in cls:
                                    emb_provider = "openai"
                                elif "dummy" in cls:
                                    emb_provider = "dummy"
                                else:
                                    emb_provider = "unknown"
                    except Exception:
                        emb_provider = None

                    self.conn.execute(
                        "UPDATE memory SET embedding = ?, embedding_dim = ?, embedding_model = ?, embedding_provider = ? WHERE id = ?",
                        (_json(emb_val), emb_dim, emb_model, emb_provider, primary_id)
                    )
                    self.conn.commit()
                    reembedded = True
            except Exception:
                # 安全起见，忽略重嵌入错误，不影响合并结果
                reembedded = False

        return {"primary_id": primary_id, "merged_count": len(other_ids), "strategy": "merge_into_primary", "reembedded": reembedded}

    def _exec_split(self, ir: IR, args: SplitArgs) -> ExecutionResult:
        """分割记忆操作（by_sentences | by_chunks | custom）"""
        wh, ps = self._where_from_target(ir.target)

        # 获取目标记忆
        sql = f"SELECT * FROM memory WHERE {wh} AND deleted=0"
        rows = [dict(r) for r in self.conn.execute(sql, ps).fetchall()]

        if not rows:
            return {"message": "没有找到需要分割的记忆", "split_count": 0}

        if ir.meta and ir.meta.dry_run:
            return {"message": f"模拟分割 {len(rows)} 条记忆", "strategy": args.strategy}

        params = args.params if isinstance(args.params, dict) else {}

        def _get_conf(name: str) -> dict:
            conf = params.get(name)
            return conf if isinstance(conf, dict) else {}

        def split_by_sentences(text: str, lang: str = "auto", max_sentences: int | None = None) -> list[str]:
            parts = re.split(r"(?<=[。！？；.!?;])\s+", text.strip())
            parts = [p.strip() for p in parts if p.strip()]
            if max_sentences and max_sentences > 0:
                merged: list[str] = []
                buf: list[str] = []
                for sent in parts:
                    buf.append(sent)
                    if len(buf) >= max_sentences:
                        merged.append(" ".join(buf))
                        buf = []
                if buf:
                    merged.append(" ".join(buf))
                return merged
            return parts

        def split_by_chunks(text: str, chunk_size: int | None = None, num_chunks: int | None = None) -> list[str]:
            if num_chunks and num_chunks > 0:
                size = max(1, len(text) // num_chunks + (1 if len(text) % num_chunks else 0))
            else:
                size = max(50, chunk_size or 1000)
            chunks = [text[i : i + size] for i in range(0, len(text), size)]
            return [c.strip() for c in chunks if c.strip()]

        def split_by_headings(text: str) -> list[dict]:
            segments: list[dict] = []
            lines = text.splitlines(keepends=True)
            offsets: list[int] = []
            total = 0
            for ln in lines:
                offsets.append(total)
                total += len(ln)
            heading_idx = [i for i, ln in enumerate(lines) if re.match(r"^#{1,6}\s+", ln)]
            if not heading_idx:
                return []
            heading_idx.append(len(lines))
            for idx, next_idx in zip(heading_idx[:-1], heading_idx[1:]):
                start = offsets[idx]
                end = offsets[next_idx] if next_idx < len(offsets) else len(text)
                chunk = text[start:end].strip()
                if not chunk:
                    continue
                title = lines[idx].lstrip('#').strip()
                segments.append({"title": title, "text": chunk, "range": [start, end]})
            return segments

        def normalize_custom_segments(raw_segments: list[dict], src: str) -> list[dict]:
            normalized: list[dict] = []
            for item in raw_segments or []:
                if not isinstance(item, dict):
                    continue
                text_val = (item.get("text") or "").strip()
                rng = item.get("range") if isinstance(item.get("range"), list) else None
                if not text_val and rng and len(rng) == 2:
                    try:
                        start, end = int(rng[0]), int(rng[1])
                        start = max(0, min(start, len(src)))
                        end = max(start, min(end, len(src)))
                        text_val = src[start:end].strip()
                    except Exception:
                        text_val = ""
                if not text_val:
                    continue
                normalized.append({
                    "title": item.get("title") if isinstance(item.get("title"), str) else None,
                    "text": text_val,
                    "range": rng if rng and len(rng) == 2 else None,
                })
            return normalized

        def split_custom(text: str, instruction: str, max_splits: int = 10, force_model: bool = False) -> tuple[list[dict], str]:
            # 1) markdown heading heuristic (unless forcing model)
            if not force_model:
                heading_segments = split_by_headings(text)
                if heading_segments:
                    return heading_segments[:max_splits], "custom:headings"

            # 2) delegate to models service
            service_used = False
            try:
                service_segments = self.models_service.split_custom(text, instruction or "按主题拆分", max_splits=max_splits)
                service_used = True
            except Exception:
                service_segments = []
            normalized = normalize_custom_segments(service_segments if isinstance(service_segments, list) else [], text)
            if normalized:
                return normalized[:max_splits], "custom:model" if service_used else "custom:model_fallback"

            # 3) fallback: paragraph split by blank lines (unless force_model requested)
            if not force_model:
                paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
                if len(paragraphs) > 1:
                    return ([{"text": p} for p in paragraphs[:max_splits]], "custom:paragraphs")

            # 4) final fallback: sentence split
            sentences = split_by_sentences(text)
            if len(sentences) > 1:
                return ([{"text": s} for s in sentences[:max_splits]], "custom:sentences")

            return ([{"text": text.strip()}], "custom:single")

        # 处理各条目
        split_results = []
        for row in rows:
            text = row.get("text") or ""
            if not text.strip():
                continue

            strategy = args.strategy
            children: list[dict]
            if strategy == "by_sentences":
                conf = _get_conf("by_sentences")
                segs = split_by_sentences(
                    text,
                    lang=(conf.get("lang") or "auto"),
                    max_sentences=conf.get("max_sentences"),
                )
                children = [{"text": seg} for seg in segs if seg.strip()]
                child_strategy = "by_sentences"
            elif strategy == "by_chunks":
                conf = _get_conf("by_chunks")
                segs = split_by_chunks(
                    text,
                    chunk_size=conf.get("chunk_size"),
                    num_chunks=conf.get("num_chunks"),
                )
                children = [{"text": seg} for seg in segs if seg.strip()]
                child_strategy = "by_chunks"
            else:
                conf = _get_conf("custom")
                instr = conf.get("instruction") if conf else None
                max_splits = conf.get("max_splits") if conf else 10
                splits, split_mode = split_custom(
                    text,
                    instruction=instr or "按主题拆分",
                    max_splits=max_splits or 10,
                    force_model=bool(conf.get("force_model")) if conf else False,
                )
                children = [{
                    "text": s.get("text"),
                    "title": s.get("title"),
                    "range": s.get("range"),
                } for s in splits if s.get("text")]
                child_strategy = split_mode

            if not children or len(children) <= 1:
                continue

            # 构建并插入子记录
            child_ids = []
            for child in children:
                split_text = (child.get("text") or "").strip()
                if not split_text:
                    continue

                # 继承逻辑
                inherit = bool(getattr(args, 'inherit_all', True))
                tags = json.loads(row["tags"]) if (inherit and row.get("tags")) else []
                tags = tags if isinstance(tags, list) else []
                tags.append(f"split_from_{row['id']}")

                insert_sql = (
                    "INSERT INTO memory (text,type,tags,time,subject,location,topic,source,deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)"
                )
                cursor = self.conn.execute(
                    insert_sql,
                    (
                        split_text,
                        row.get("type"),
                        _json(tags) if inherit else None,
                        row.get("time") if inherit else None,
                        row.get("subject"),
                        row.get("location"),
                        row.get("topic"),
                        row.get("source") if inherit else None,
                    )
                )
                child_id = cursor.lastrowid
                child_ids.append(child_id)

            if child_ids:
                split_results.append({
                    "parent_id": row["id"],
                    "split_count": len(child_ids),
                    "child_ids": child_ids,
                    "strategy_used": child_strategy,
                })

        self.conn.commit()
        return {
            "results": split_results,
            "total_splits": sum(r.get("split_count", 0) for r in split_results),
        }

    def _exec_lock(self, ir: IR, args: LockArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        wh = f"({wh}) AND deleted=0"

        policy_dict = args.policy.model_dump(exclude_none=True) if args.policy else None
        lock_policy_json = _json(policy_dict) if policy_dict else None
        lock_expires = policy_dict.get("expires") if policy_dict else None

        if args.mode == "disabled":
            lock_mode = None
            lock_reason = None
            lock_policy_json = None
            lock_expires = None
            policy_dict = None
            read_perm = None
            write_perm = None
        else:
            lock_mode = args.mode
            lock_reason = args.reason
            read_perm, write_perm = self._lock_perm_values(args.mode)

        if ir.meta and ir.meta.dry_run:
            return {
                "preview": "lock",
                "mode": args.mode,
                "policy": policy_dict,
                "where": wh,
                "params": ps,
            }

        sql = (
            "UPDATE memory SET lock_mode = ?, lock_reason = ?, lock_policy = ?, lock_expires = ?, "
            "read_perm_level = ?, write_perm_level = ? WHERE "
            f"{wh}"
        )
        values = (lock_mode, lock_reason, lock_policy_json, lock_expires, read_perm, write_perm)
        cur = self.conn.execute(sql, values + ps)
        self.conn.commit()
        return {
            "affected_rows": cur.rowcount,
            "mode": args.mode,
            "reason": args.reason,
            "policy": policy_dict,
        }

    def _exec_expire(self, ir: IR, args: ExpireArgs) -> ExecutionResult:
        """设置记忆过期"""
        wh, ps = self._where_from_target(ir.target)
        wh = f"({wh}) AND deleted=0"

        try:
            self._assert_operation_allowed(ir, wh, ps)
        except PermissionError as err:
            raise ValueError(str(err))

        if args.expire_at:
            expire_at = args.expire_at
        else:
            delta = self._parse_iso_duration(args.ttl)
            expire_at = (datetime.now(timezone.utc) + delta).isoformat().replace("+00:00", "Z")

        update_sql = (
            "UPDATE memory SET expire_at = ?, expire_action = ?, expire_reason = ? "
            f"WHERE {wh}"
        )
        params = (expire_at, args.on_expire, args.reason) + ps

        if ir.meta and ir.meta.dry_run:
            return {"sql": update_sql, "params": params}

        cur = self.conn.execute(update_sql, params)
        self.conn.commit()
        return {
            "affected_rows": cur.rowcount,
            "expire_time": expire_at,
            "on_expire": args.on_expire,
            "reason": args.reason,
        }

    # def _exec_clarify(self, ir: IR, args: ClarifyArgs) -> ExecutionResult:
    #     """澄清操作"""
    #     
    #     if ir.meta and ir.meta.dry_run:
    #         return {"message": "模拟澄清请求", "incomplete_input": args.incomplete_input}
    #     
    #     # 获取上下文信息（如果target指定了相关记忆）
    #     context = None
    #     if ir.target:
    #         wh, ps = self._where_from_target(ir.target)
    #         context_sql = f"SELECT text FROM memory WHERE {wh} AND deleted=0 LIMIT 3"
    #         context_rows = self.conn.execute(context_sql, ps).fetchall()
    #         if context_rows:
    #             context = " ".join([row["text"] for row in context_rows if row["text"]])
    #     
    #     # 使用LLM生成澄清问题
    #     clarify_result = self.models_service.generate_clarification(
    #         args.incomplete_input,
    #         context=context
    #     )
    #     
    #     try:
    #         # 解析结构化响应
    #         import json
    #         clarify_data = json.loads(clarify_result.text)
    #         
    #         response = {
    #             "question": clarify_data.get("question", "请提供更多信息"),
    #             "missing_slots": clarify_data.get("missing_slots", []),
    #             "suggestions": clarify_data.get("suggestions", []),
    #             "timeout": args.timeout,
#                "fallback": args.fallback,
#                "status": "waiting_for_user_input",
#                "context_used": bool(context),
#                "model_used": True
#            }
#        except json.JSONDecodeError:
#            # 如果解析失败，使用文本作为问题
#            response = {
#                "question": clarify_result.text,
#                "missing_slots": [],
#                "suggestions": [],
#                "timeout": args.timeout,
#                "fallback": args.fallback,
#                "status": "waiting_for_user_input",
#                "context_used": bool(context),
#                "model_used": True
#            }
#        
#        return response

    def _exec_retrieve(self, ir: IR, args: RetrieveArgs) -> ExecutionResult:
        # 检索：基于 target
        target = ir.target
        base_target = target
        if target and target.search is not None:
            base_kwargs: dict[str, Any] = {}
            if target.ids is not None:
                base_kwargs["ids"] = target.ids
            if target.filter is not None:
                base_kwargs["filter"] = target.filter
            if target.all:
                base_kwargs["all"] = True
            base_target = Target(**base_kwargs) if base_kwargs else None  # type: ignore[arg-type]
        wh, ps = self._where_from_target(base_target)
        # 忽略 deleted
        wh = f"({wh}) AND deleted=0"

    # 语义检索模式：当 target.search 存在
        if target and target.search is not None:
            search = target.search
            intent = search.intent
            limit = search.limit or (search.overrides.k if search.overrides and search.overrides.k else 10)
            if ir.meta and ir.meta.dry_run:
                return {"mode": "semantic_search", "intent": intent.model_dump(), "limit": limit}

            select_sql = f"SELECT id, text, embedding, embedding_dim, embedding_model, embedding_provider FROM memory WHERE {wh}"
            rows = self.conn.execute(select_sql, ps).fetchall()

            # 收集向量
            memory_vectors = []
            try:
                target_dim = self.models_service.embedding_model.get_dimension()
            except Exception:
                target_dim = None
            skipped = 0
            for row in rows:
                embedding = json.loads(row["embedding"]) if row["embedding"] else None
                if embedding:
                    row_dim = row["embedding_dim"] if row["embedding_dim"] is not None else (len(embedding) if embedding else None)
                    if target_dim is None or row_dim == target_dim:
                        memory_vectors.append({"id": row["id"], "text": row["text"], "vector": embedding})
                    else:
                        skipped += 1

            # 计算相似度排序（混合：语义 + 关键词）
            if not memory_vectors:
                note = "no_embeddings"
                if skipped:
                    note += f", skipped_incompatible_vectors={skipped}"
                return {"rows": [], "count": 0, "mode": "semantic", "note": note}

            # 根据意图选择查询向量
            if intent.vector is not None:
                query_vector = intent.vector
                # 如果维度可获取，过滤不匹配
                if target_dim is not None and len(query_vector) != target_dim:
                    return {"rows": [], "count": 0, "mode": "semantic", "note": "query_vector_dimension_mismatch"}
                # 手动打分
                scored = []
                alpha = self.search_alpha
                beta = self.search_beta
                phrase_bonus = self.search_phrase_bonus
                for item in memory_vectors:
                    try:
                        sim = self.models_service.compute_similarity(query_vector, item["vector"])  # type: ignore
                    except Exception:
                        continue
                    kw, exact = self._keyword_score(item.get("text"), getattr(intent, 'query', None))
                    final_sim = alpha * sim + beta * kw + (phrase_bonus if exact else 0.0)
                    scored.append({**item, "similarity": min(1.0, final_sim)})
                scored.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                search_results = scored[:limit]
            else:
                # 通过服务的语义检索
                base = self.models_service.semantic_search(intent.query, memory_vectors, k=limit)  # type: ignore
                # 关键词加权重排
                alpha = self.search_alpha
                beta = self.search_beta
                phrase_bonus = self.search_phrase_bonus
                rescored = []
                for r in base:
                    kw, exact = self._keyword_score(r.get("text"), intent.query)
                    sim = r.get("similarity", 0)
                    final_sim = alpha * sim + beta * kw + (phrase_bonus if exact else 0.0)
                    rescored.append({**r, "similarity": min(1.0, final_sim)})
                rescored.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                search_results = rescored[:limit]

            result_ids = [r["id"] for r in search_results]
            if not result_ids:
                result = {"rows": [], "count": 0, "mode": "semantic"}
                if skipped:
                    result["note"] = f"skipped_incompatible_vectors={skipped}"
                return result

            placeholders = ",".join("?" * len(result_ids))
            final_sql = f"SELECT * FROM memory WHERE id IN ({placeholders})"
            final_rows = [dict(r) for r in self.conn.execute(final_sql, result_ids).fetchall()]
            id_to_similarity = {r["id"]: r.get("similarity", 0) for r in search_results}
            final_rows.sort(key=lambda x: id_to_similarity.get(x["id"], 0), reverse=True)
            for row in final_rows:
                row["_similarity"] = id_to_similarity.get(row["id"], 0)
            result = {"rows": final_rows, "count": len(final_rows), "mode": "semantic"}
            if skipped:
                result["note"] = f"skipped_incompatible_vectors={skipped}"
            return result

        # 传统过滤和排序
        order_by = "time_desc"
        order_sql = {
            "time_desc": "time DESC",
            "time_asc": "time ASC",
            "weight_desc": "weight DESC",
        }[order_by]
        limit = 100 if target is None else 50
        if target and target.filter and target.filter.limit:
            limit = target.filter.limit  # type: ignore
        sql = f"SELECT * FROM memory WHERE {wh} ORDER BY {order_sql} LIMIT ?"
        params = ps + (limit,)
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": params}
        rows = [dict(r) for r in self.conn.execute(sql, params).fetchall()]
        result: dict[str, Any] = {"rows": rows, "count": len(rows), "mode": "traditional"}
        if target is None:
            result["warnings"] = ["Default limit applied (100) because Retrieve target was omitted."]
        return result

    # ---------- main dispatch ----------
    def execute(self, ir: IR) -> ExecutionResult:
        typed = ir.parse_args_typed()
        try:
            if ir.op == "Encode":
                result = self._exec_encode(ir, typed)  # type: ignore
            elif ir.op == "Label":
                result = self._exec_label(ir, typed)  # type: ignore
            elif ir.op == "Update":
                result = self._exec_update(ir, typed)  # type: ignore
            elif ir.op == "Promote":
                result = self._exec_promote(ir, typed)  # type: ignore
            elif ir.op == "Demote":
                result = self._exec_demote(ir, typed)  # type: ignore
            elif ir.op == "Delete":
                result = self._exec_delete(ir, typed)  # type: ignore
            elif ir.op == "Retrieve":
                result = self._exec_retrieve(ir, typed)  # type: ignore
            elif ir.op == "Summarize":
                result = self._exec_summarize(ir, typed)  # type: ignore
            elif ir.op == "Merge":
                result = self._exec_merge(ir, typed)  # type: ignore
            elif ir.op == "Split":
                result = self._exec_split(ir, typed)  # type: ignore
            elif ir.op == "Lock":
                result = self._exec_lock(ir, typed)  # type: ignore
            elif ir.op == "Expire":
                result = self._exec_expire(ir, typed)  # type: ignore
            # elif ir.op == "Clarify":
            #     result = self._exec_clarify(ir, typed)  # type: ignore
            else:
                # 其他操作给出占位，便于你逐步补全
                result = {"todo": f"{ir.op} not implemented in SQLiteAdapter prototype"}
            
            # 将字典结果包装成ExecutionResult对象
            if isinstance(result, ExecutionResult):
                return result
            else:
                return ExecutionResult(success=True, data=result, meta={})
                
        except Exception as e:
            return ExecutionResult(success=False, error=str(e), data=None, meta={})
            
    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def get_table_stats(self) -> dict:
        """获取数据库表统计信息"""
        stats = {}
        try:
            # 获取memory表的行数
            cur = self.conn.execute("SELECT COUNT(*) as count, SUM(CASE WHEN deleted=0 THEN 1 ELSE 0 END) as active FROM memory")
            row = cur.fetchone()
            stats["total_rows"] = row["count"] if row["count"] is not None else 0
            stats["active_rows"] = row["active"] if row["active"] is not None else 0
            
            # 获取类型分布
            cur = self.conn.execute("SELECT type, COUNT(*) as count FROM memory WHERE deleted=0 GROUP BY type")
            stats["types"] = {row["type"] if row["type"] else "null": row["count"] for row in cur.fetchall()}
            
            # 获取优先级分布
            cur = self.conn.execute("SELECT CASE WHEN weight IS NULL THEN 'null' ELSE 'non_null' END as bucket, COUNT(*) as count FROM memory WHERE deleted=0 GROUP BY bucket")
            stats["weight_non_null"] = {row["bucket"]: row["count"] for row in cur.fetchall()}
            
            # 获取标签统计（这只是一个近似值，因为tags存储为JSON）
            cur = self.conn.execute("SELECT id, tags FROM memory WHERE deleted=0 AND tags IS NOT NULL")
            tag_counts = {}
            for row in cur.fetchall():
                try:
                    tags = json.loads(row["tags"])
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except:
                    pass
            stats["top_tags"] = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def dump_recent_rows(self, limit=5) -> list:
        """获取最近添加的记录"""
        try:
            cur = self.conn.execute(
                "SELECT id, text, type, tags, weight, deleted FROM memory ORDER BY id DESC LIMIT ?", 
                (limit,)
            )
            rows = []
            for row in cur.fetchall():
                row_dict = dict(row)
                # 格式化JSON字段以便于阅读
                if row_dict["tags"]:
                    try:
                        row_dict["tags"] = json.loads(row_dict["tags"])
                    except:
                        pass
                rows.append(row_dict)
            return rows
        except Exception as e:
            return [{"error": str(e)}]
            
    def optimize_database(self) -> dict:
        """
        执行数据库优化操作
        
        包括:
        1. 创建索引
        2. 执行ANALYZE更新统计信息
        3. 整理数据库结构(VACUUM)
        
        Returns:
            dict: 操作结果
        """
        results = {}
        
        try:
            # 1. 创建索引以加速查询
            indexes = [
                ("idx_memory_type", "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(type)"),
                ("idx_memory_deleted", "CREATE INDEX IF NOT EXISTS idx_memory_deleted ON memory(deleted)"),
                ("idx_memory_weight", "CREATE INDEX IF NOT EXISTS idx_memory_weight ON memory(weight)"),
                ("idx_memory_time", "CREATE INDEX IF NOT EXISTS idx_memory_time ON memory(time)")
            ]
            
            for name, sql in indexes:
                start = datetime.now()
                self.conn.execute(sql)
                duration = (datetime.now() - start).total_seconds()
                results[name] = {"status": "success", "time": f"{duration:.3f}秒"}
            
            # 2. 更新统计信息
            start = datetime.now()
            self.conn.execute("ANALYZE")
            duration = (datetime.now() - start).total_seconds()
            results["analyze"] = {"status": "success", "time": f"{duration:.3f}秒"}
            
            # 3. 清理结构
            start = datetime.now()
            self.conn.execute("VACUUM")
            duration = (datetime.now() - start).total_seconds()
            results["vacuum"] = {"status": "success", "time": f"{duration:.3f}秒"}
            
            self.conn.commit()
            return results
        except Exception as e:
            return {"error": str(e)}
            
    def get_database_info(self) -> dict:
        """
        获取数据库详细信息
        
        Returns:
            dict: 数据库信息
        """
        info = {}
        try:
            # SQLite版本
            cur = self.conn.execute("SELECT sqlite_version()")
            info["sqlite_version"] = cur.fetchone()[0]
            
            # 表结构
            tables = {}
            for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                table_name = row[0]
                tables[table_name] = []
                for column in self.conn.execute(f"PRAGMA table_info({table_name})"):
                    tables[table_name].append({
                        "name": column[1],
                        "type": column[2],
                        "nullable": not column[3],
                        "pk": column[5] > 0
                    })
            info["tables"] = tables
            
            # 索引
            indexes = {}
            for row in self.conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'"):
                index_name, table_name, sql = row
                if not indexes.get(table_name):
                    indexes[table_name] = []
                indexes[table_name].append({
                    "name": index_name,
                    "sql": sql
                })
            info["indexes"] = indexes
            
            # 数据库状态
            info["pragma"] = {}
            for pragma in ["page_size", "page_count", "freelist_count", "auto_vacuum"]:
                cur = self.conn.execute(f"PRAGMA {pragma}")
                info["pragma"][pragma] = cur.fetchone()[0]
            
            return info
        except Exception as e:
            return {"error": str(e)}

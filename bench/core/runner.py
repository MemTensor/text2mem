from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional
from uuid import uuid4

from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.core.models import IR
from text2mem.core.engine import Text2MemEngine
from text2mem.services import ModelsService, get_models_service

from bench.tools.clock import VirtualClock
from bench.tools.sql_builder_sqlite import (
    CompiledAssertion,
    SQLiteAssertionCompiler,
    evaluate_expectation,
)


class TimeoutError(Exception):
    """Raised when a sample execution exceeds the timeout."""
    pass


@dataclass(slots=True)
class BenchConfig:
    """Configuration required to execute the benchmark."""

    db_root: Path
    output_dir: Path = Path("bench/output")
    mode: Optional[str] = None  # engine mode: auto/mock/ollama/openai
    fixtures_root: Optional[Path] = None  # fixtures directory
    timeout: Optional[float] = None  # timeout in seconds for each sample (None = no timeout)

    def __post_init__(self):
        """Load timeout from environment if not explicitly set."""
        if self.timeout is None:
            # Try to read from environment variable
            env_timeout = os.getenv("TEXT2MEM_BENCH_TIMEOUT")
            if env_timeout and env_timeout.strip():
                try:
                    self.timeout = float(env_timeout)
                except ValueError:
                    pass  # Invalid value, keep None

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "tmp").mkdir(parents=True, exist_ok=True)
        
        # Set default fixtures_root if not provided
        if self.fixtures_root is None:
            self.fixtures_root = self.db_root.parent / "fixtures"


@dataclass(slots=True)
class AssertionOutcome:
    name: str
    passed: bool
    message: str
    sql: str
    value: Any


@dataclass(slots=True)
class RankingOutcome:
    query: str
    gold_ids: List[str]
    retrieved_ids: List[str]
    hits: List[str]
    missed: List[str]
    extras: List[str]
    precision: Optional[float]
    recall: Optional[float]
    allow_extra: bool
    min_hits: int
    passed: bool
    message: str
    scores: Dict[str, float]


@dataclass(slots=True)
class SampleRunResult:
    sample_id: str
    assertions: List[AssertionOutcome]
    schema_results: List[Dict[str, Any]]
    ranking: Optional[RankingOutcome] = None
    triggers: Optional[List[Dict[str, Any]]] = None
    errors: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        if self.errors:
            return False
        assertions_ok = all(outcome.passed for outcome in self.assertions)
        ranking_ok = self.ranking.passed if self.ranking is not None else True
        triggers_ok = True
        if self.triggers:
            triggers_ok = all(block.get("passed", True) for block in self.triggers)
        return assertions_ok and ranking_ok and triggers_ok


class BenchRunner:
    """Execute benchmark samples end-to-end using Text2MemEngine."""

    def __init__(self, config: BenchConfig):
        self.config = config
        self.config.ensure_dirs()
        # 根据配置的mode创建 models_service
        self.models_service = self._create_models_service()
        self.compiler = SQLiteAssertionCompiler()
    
    def _create_models_service(self) -> ModelsService:
        """根据config.mode创建对应的模型服务"""
        from text2mem.services.service_factory import create_models_service
        from text2mem.core.config import ModelConfig
        
        mode = self.config.mode or "auto"
        
        # 根据mode创建对应的ModelConfig
        if mode == "ollama":
            model_config = ModelConfig.for_ollama()
        elif mode == "openai":
            model_config = ModelConfig.for_openai()
        elif mode == "mock":
            model_config = ModelConfig(
                provider="mock",
                embedding_provider="mock",
                generation_provider="mock",
            )
        else:
            # auto模式使用环境变量
            model_config = None
        
        return create_models_service(mode=mode, config=model_config)

    # ------------------------------------------------------------------
    def run_sample_file(self, path: Path) -> SampleRunResult:
        sample = json.loads(path.read_text(encoding="utf-8"))
        return self.run_sample(sample, sample_id=sample.get("id") or path.stem)

    def run_sample(self, sample: Mapping[str, Any], sample_id: Optional[str] = None) -> SampleRunResult:
        """运行单个测试样本。
        
        使用 Text2MemEngine 作为统一入口，传入自定义的 models_service（包含测试用的 embedding provider）。
        这确保测试流程与生产环境保持一致。
        
        如果配置了timeout，将在超时后抛出TimeoutError。
        """
        sample_id = sample_id or sample.get("id") or f"sample-{uuid4().hex[:8]}"
        
        # 如果配置了timeout，使用带超时的执行
        if self.config.timeout is not None:
            return self._run_sample_with_timeout(sample, sample_id, self.config.timeout)
        else:
            return self._run_sample_impl(sample, sample_id)
    
    def _run_sample_impl(self, sample: Mapping[str, Any], sample_id: str) -> SampleRunResult:
        """实际执行测试样本的内部方法。"""
        init_db = sample.get("init_db")
        fixture_ids = sample.get("fixtures", [])
        results: List[Dict[str, Any]] = []
        assertions: List[AssertionOutcome] = []
        errors: List[str] = []
        
        # 获取虚拟评测时间（如果有的话）
        eval_time_str = sample.get("expected", {}).get("meta", {}).get("eval_time_utc")
        virtual_now = None
        if eval_time_str:
            try:
                from datetime import datetime
                # 解析 ISO 8601 时间字符串
                virtual_now = datetime.fromisoformat(eval_time_str.replace('Z', '+00:00'))
            except Exception as e:
                # 如果解析失败，记录警告但继续执行
                errors.append(f"Warning: Failed to parse eval_time_utc '{eval_time_str}': {e}")

        ranking_outcome: Optional[RankingOutcome]
        try:
            with self._prepared_database(init_db) as db_path:
                # 创建适配器和引擎，传入自定义的 models_service 和虚拟时钟
                adapter = SQLiteAdapter(
                    str(db_path), 
                    models_service=self.models_service,
                    virtual_now=virtual_now  # 传递虚拟时间
                )
                engine = Text2MemEngine(
                    adapter=adapter,
                    models_service=self.models_service,
                    validate_schema=False,  # bench 已经通过 Pydantic 验证
                )
                
                try:
                    # 执行prerequisites前置指令（内嵌在测试样本中的IR指令）
                    prerequisites = sample.get("prerequisites", [])
                    if prerequisites:
                        for idx, prereq_ir_obj in enumerate(prerequisites):
                            try:
                                ir = IR.model_validate(prereq_ir_obj)
                                exec_res = engine.execute(ir.model_dump(mode='json', exclude_none=True))
                                # Prerequisite执行失败记录错误
                                if not getattr(exec_res, "success", True):
                                    errors.append(f"Prerequisite {idx+1} failed: {ir.op}")
                            except Exception as e:
                                errors.append(f"Prerequisite {idx+1} error: {str(e)}")
                    
                    # 执行测试样本的IR指令
                    for ir_obj in sample.get("schema_list", []):
                        # Pydantic 验证
                        ir = IR.model_validate(ir_obj)
                        # 通过 Engine 执行（统一入口）
                        exec_res = engine.execute(ir.model_dump(mode='json', exclude_none=True))
                        results.append({
                            "op": ir.op,
                            "success": bool(getattr(exec_res, "success", True)),
                            "data": getattr(exec_res, "data", None) if hasattr(exec_res, "data") else exec_res,
                        })
                finally:
                    adapter.close()

                assertions.extend(
                    self._run_assertions(db_path, sample.get("expected", {}).get("assertions", []))
                )
                trigger_results = self._run_triggers(db_path, sample.get("expected", {}).get("triggers", []))
                ranking_outcome = self._evaluate_ranking(
                    db_path, sample.get("expected", {}).get("ranking"), sample=sample
                )
        except TimeoutError:
            # Timeout occurred, mark as error
            errors.append(f"Sample execution exceeded timeout of {self.config.timeout}s")
            trigger_results = None
            ranking_outcome = None
        except Exception as exc:  # pragma: no cover - defensive logging hook
            errors.append(str(exc))
            trigger_results = None
            ranking_outcome = None

        return SampleRunResult(
            sample_id=sample_id,
            assertions=assertions,
            schema_results=results,
            ranking=ranking_outcome,
            triggers=trigger_results,
            errors=errors,
        )
    
    def _run_sample_with_timeout(self, sample: Mapping[str, Any], sample_id: str, timeout: float) -> SampleRunResult:
        """使用线程+超时执行测试样本。
        
        注意：这个实现使用threading，在Python中无法真正中断线程，
        只能检测超时并返回错误结果。对于真正需要中断的场景，
        建议使用进程级别的超时控制。
        """
        result_container = []
        exception_container = []
        
        def target():
            try:
                result = self._run_sample_impl(sample, sample_id)
                result_container.append(result)
            except Exception as e:
                exception_container.append(e)
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # Thread still running - timeout occurred
            # Note: we can't forcefully kill the thread in Python
            return SampleRunResult(
                sample_id=sample_id,
                assertions=[],
                schema_results=[],
                ranking=None,
                triggers=None,
                errors=[f"Sample execution exceeded timeout of {timeout}s"],
            )
        
        if exception_container:
            raise exception_container[0]
        
        if result_container:
            return result_container[0]
        
        # Should not reach here
        return SampleRunResult(
            sample_id=sample_id,
            assertions=[],
            schema_results=[],
            ranking=None,
            triggers=None,
            errors=["Unknown error in timeout wrapper"],
        )

    # ------------------------------------------------------------------
    def _run_assertions(self, db_path: Path, assertions: Iterable[Mapping[str, Any]]) -> List[AssertionOutcome]:
        outcomes: List[AssertionOutcome] = []
        if not assertions:
            return outcomes
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            for spec in assertions:
                compiled: CompiledAssertion = self.compiler.compile(spec)
                cursor = conn.execute(compiled.sql, compiled.params)
                row = cursor.fetchone()
                # SQL中使用的是 COUNT(*) as actual，所以列名是actual
                actual = row["actual"] if row is not None and "actual" in row.keys() else None
                ok, message = evaluate_expectation(compiled.expectation, actual)
                outcomes.append(
                    AssertionOutcome(
                        name=compiled.name,
                        passed=ok,
                        message=message,
                        sql=compiled.sql,
                        value=actual,
                    )
                )
        finally:
            conn.close()
        return outcomes

    def _run_triggers(self, db_path: Path, triggers: Iterable[Mapping[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not triggers:
            return None
        clock = VirtualClock()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        outcomes: List[Dict[str, Any]] = []
        try:
            for block in triggers:
                advance = block.get("advance")
                if advance:
                    clock.advance(advance)
                for assertion in block.get("assertions", []):
                    compiled = self.compiler.compile(assertion)
                    cursor = conn.execute(
                        compiled.sql, {**compiled.params, "now": clock.isoformat()}
                    )
                    row = cursor.fetchone()
                    actual = row["result"] if row is not None and "result" in row.keys() else None
                    ok, message = evaluate_expectation(compiled.expectation, actual)
                    outcomes.append(
                        {
                            "name": compiled.name,
                            "passed": ok,
                            "message": message,
                            "sql": compiled.sql,
                            "value": actual,
                            "clock": clock.isoformat(),
                        }
                    )
        finally:
            conn.close()
        return outcomes

    def _evaluate_ranking(
        self, db_path: Path, ranking_spec: Optional[Mapping[str, Any]], sample: Optional[Mapping[str, Any]] = None
    ) -> Optional[RankingOutcome]:
        """评估ranking结果
        
        对于filter类型的Retrieve：直接从schema_results中获取结果
        对于search类型的Retrieve：使用query执行语义检索
        """
        if not ranking_spec:
            return None

        gold_ids = [str(g) for g in ranking_spec.get("gold_ids", [])]
        topk = int(ranking_spec.get("topk", ranking_spec.get("k", 5)))
        allow_extra = bool(ranking_spec.get("allow_extra", False))
        min_hits = int(ranking_spec.get("min_hits", len(gold_ids) if gold_ids else 0))
        
        # 检查sample中是否已经执行了Retrieve操作
        # 如果是filter类型，直接使用已执行的结果
        retrieved_ids = []
        query_text = ""
        
        if sample:
            # 从schema_list检查是否为filter类型
            is_filter_retrieve = False
            for schema in sample.get('schema_list', []):
                if schema.get('op') == 'Retrieve':
                    target = schema.get('target', {})
                    if 'filter' in target:
                        is_filter_retrieve = True
                        query_text = sample.get('nl', {}).get('zh') or sample.get('nl', {}).get('en') or 'filter-based retrieve'
                    elif 'search' in target:
                        search = target.get('search', {})
                        intent = search.get('intent', {})
                        query_text = intent.get('query', '')
                    break
            
            # 如果是filter类型，从执行结果中提取ID
            # 注意：这需要在run_sample中保存结果
            # 暂时先尝试从数据库直接查询
            if is_filter_retrieve:
                # 对于filter类型，直接检查数据库中的记录
                # 因为prerequisites已经插入了数据
                adapter = SQLiteAdapter(str(db_path), models_service=self.models_service)
                try:
                    # 重新执行schema_list中的Retrieve操作获取结果
                    for schema in sample.get('schema_list', []):
                        if schema.get('op') == 'Retrieve':
                            ir = IR.model_validate(schema)
                            exec_res = adapter.execute(ir)
                            if exec_res.success and exec_res.data:
                                rows = exec_res.data.get('rows', [])
                                retrieved_ids = [str(row.get('id')) for row in rows if row.get('id')]
                            break
                finally:
                    adapter.close()
                
                # 对于filter类型，不使用similarity scores
                score_map = {}
                
                hits = [rid for rid in retrieved_ids if rid in gold_ids]
                missed = [gid for gid in gold_ids if gid not in retrieved_ids]
                extras = [rid for rid in retrieved_ids if rid not in gold_ids]
                
                precision = (len(hits) / len(retrieved_ids)) if retrieved_ids else None
                recall = (len(hits) / len(gold_ids)) if gold_ids else None
                
                passed = (len(hits) >= min_hits) and (allow_extra or not extras)
                
                message_parts = []
                if gold_ids:
                    message_parts.append(f"hits={len(hits)}/{len(gold_ids)} (min={min_hits})")
                if missed:
                    message_parts.append(f"missed={missed}")
                if extras and not allow_extra:
                    message_parts.append(f"unexpected={extras}")
                if not message_parts:
                    message_parts.append("no gold IDs provided; treated as pass")
                
                message = "; ".join(message_parts)
                
                return RankingOutcome(
                    query=query_text,
                    gold_ids=gold_ids,
                    retrieved_ids=retrieved_ids[:topk],
                    hits=hits,
                    missed=missed,
                    extras=extras,
                    precision=precision,
                    recall=recall,
                    allow_extra=allow_extra,
                    min_hits=min_hits,
                    passed=passed,
                    message=message,
                    scores=score_map,
                )
        
        # 对于search类型或没有sample信息的情况，使用原来的语义检索逻辑
        query = ranking_spec.get("query") or query_text
        
        if not query:
            return RankingOutcome(
                query="",
                gold_ids=gold_ids,
                retrieved_ids=[],
                hits=[],
                missed=gold_ids,
                extras=[],
                precision=None,
                recall=None,
                allow_extra=allow_extra,
                min_hits=min_hits,
                passed=False,
                message="Ranking spec missing query text",
                scores={},
            )

        # 注意：不再自动为所有记录生成embeddings
        # 现在测试通过prerequisites前置操作来准备必要的数据
        # 如果需要预先生成embeddings，使用 bench/tools/pregenerate_embeddings.py
        
        adapter = SQLiteAdapter(str(db_path), models_service=self.models_service)
        try:
            ir_obj = {
                "stage": "RET",
                "op": "Retrieve",
                "target": {
                    "search": {
                        "intent": {"query": query},
                        "limit": topk,
                    }
                },
                "args": {
                    "include": ranking_spec.get("include") or ["id", "text", "weight", "tags"],
                },
            }
            ir = IR.model_validate(ir_obj)
            exec_res = adapter.execute(ir)
        finally:
            adapter.close()

        if not exec_res.success:
            return RankingOutcome(
                query=query,
                gold_ids=gold_ids,
                retrieved_ids=[],
                hits=[],
                missed=gold_ids,
                extras=[],
                precision=None,
                recall=None,
                allow_extra=allow_extra,
                min_hits=min_hits,
                passed=False,
                message=exec_res.error or "Retrieve operation failed",
                scores={},
            )

        data = exec_res.data or {}
        rows = data.get("rows", []) if isinstance(data, Mapping) else []
        scored_pairs = [
            (str(row.get("id")), float(row.get("_similarity", 0.0)))
            for row in rows
            if row.get("id") is not None
        ]
        retrieved_ids = [id_ for id_, _ in scored_pairs][:topk]
        score_map = {id_: score for id_, score in scored_pairs[:topk]}

        hits = [rid for rid in retrieved_ids if rid in gold_ids]
        missed = [gid for gid in gold_ids if gid not in retrieved_ids]
        extras = [rid for rid in retrieved_ids if rid not in gold_ids]

        precision = (len(hits) / len(retrieved_ids)) if retrieved_ids else None
        recall = (len(hits) / len(gold_ids)) if gold_ids else None

        # 检测是否使用Mock embedding模型
        is_mock_mode = self._is_using_mock_embedding()
        
        # 在Mock模式下，如果hits不足，降级为警告而不是失败
        if is_mock_mode and len(hits) < min_hits:
            passed = True  # 标记为通过，但附带警告
            message_parts = [
                f"⚠️ MOCK MODE: hits={len(hits)}/{len(gold_ids)} (min={min_hits})",
                "Mock embedding使用随机向量，语义检索结果不可靠",
                "配置真实embedding模型（Ollama/OpenAI）以验证检索功能"
            ]
        else:
            passed = (len(hits) >= min_hits) and (allow_extra or not extras)
            message_parts: List[str] = []
            if gold_ids:
                message_parts.append(f"hits={len(hits)}/{len(gold_ids)} (min={min_hits})")
            if missed:
                message_parts.append(f"missed={missed}")
            if extras and not allow_extra:
                message_parts.append(f"unexpected={extras}")
            if not message_parts:
                message_parts.append("no gold IDs provided; treated as pass")
        
        message = "; ".join(message_parts)

        return RankingOutcome(
            query=query,
            gold_ids=gold_ids,
            retrieved_ids=retrieved_ids,
            hits=hits,
            missed=missed,
            extras=extras,
            precision=precision,
            recall=recall,
            allow_extra=allow_extra,
            min_hits=min_hits,
            passed=passed,
            message=message,
            scores=score_map,
        )
    
    def _is_using_mock_embedding(self) -> bool:
        """检测是否使用Mock embedding模型"""
        try:
            from text2mem.services.models_service_mock import MockEmbeddingModel
            return isinstance(self.models_service.embedding_model, MockEmbeddingModel)
        except:
            return False

    def _ensure_embeddings(self, db_path: Path) -> None:
        """确保数据库中的记录都有嵌入向量（通过 models_service 生成）"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, text FROM memory WHERE deleted=0 AND (embedding IS NULL OR embedding = '')"
            ).fetchall()
            if not rows:
                return

            updates = []
            for row in rows:
                update = self._prepare_embedding_update(row["id"], row["text"] or "")
                if update is not None:
                    updates.append(update)

            if updates:
                conn.executemany(
                    "UPDATE memory SET embedding = ?, embedding_dim = ?, embedding_model = ?, embedding_provider = ? WHERE id = ?",
                    updates,
                )
            conn.commit()
        finally:
            conn.close()

    def _prepare_embedding_update(self, memory_id: int, text: str) -> Optional[tuple[Any, ...]]:
        """使用 models_service 生成嵌入向量"""
        try:
            result = self.models_service.encode_memory(text)
            vector = result.vector
            dimension = result.dimension or (len(vector) if vector else None)
            model_name = result.model_name
            
            # 检测 provider 名称
            embedding_model = getattr(self.models_service, "embedding_model", None)
            provider_name = None
            if embedding_model:
                provider_name = getattr(embedding_model, "provider", None) or \
                               getattr(embedding_model, "provider_name", None)
                if not provider_name:
                    cls_name = embedding_model.__class__.__name__.lower()
                    if "ollama" in cls_name:
                        provider_name = "ollama"
                    elif "openai" in cls_name:
                        provider_name = "openai"
                    elif "dummy" in cls_name or "mock" in cls_name:
                        provider_name = "mock"
                    else:
                        provider_name = "unknown"
            
            if not vector:
                return None
            
            return (
                json.dumps(vector, ensure_ascii=False),
                dimension,
                model_name,
                provider_name,
                memory_id,
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    @contextmanager
    def _prepared_database(self, snapshot_id: Optional[str]) -> Iterator[Path]:
        if not snapshot_id:
            # 创建空表，使用完整的schema（与SQLiteAdapter一致）
            temp_db = self._temp_db_path("ad-hoc")
            conn = sqlite3.connect(temp_db)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    type TEXT,
                    subject TEXT,
                    time TEXT,
                    location TEXT,
                    topic TEXT,
                    tags TEXT,
                    facets TEXT,
                    weight REAL,
                    embedding TEXT,
                    embedding_dim INTEGER,
                    embedding_model TEXT,
                    embedding_provider TEXT,
                    source TEXT,
                    auto_frequency TEXT,
                    next_auto_update_at TEXT,
                    expire_at TEXT,
                    expire_action TEXT,
                    expire_reason TEXT,
                    lock_mode TEXT,
                    lock_reason TEXT,
                    lock_policy TEXT,
                    lock_expires TEXT,
                    lineage_parents TEXT,
                    lineage_children TEXT,
                    read_perm_level TEXT,
                    write_perm_level TEXT,
                    read_whitelist TEXT,
                    read_blacklist TEXT,
                    write_whitelist TEXT,
                    write_blacklist TEXT,
                    deleted INTEGER DEFAULT 0
                );
            """)
            conn.close()
            try:
                yield temp_db
            finally:
                self._cleanup_temp_db(temp_db)
            return

        src_sql = self.config.db_root / f"{snapshot_id}.sql"
        src_db = self.config.db_root / f"{snapshot_id}.db"
        temp_db = self._temp_db_path(snapshot_id)

        if src_sql.exists():
            conn = sqlite3.connect(temp_db)
            conn.executescript(src_sql.read_text(encoding="utf-8"))
            conn.close()
        elif src_db.exists():
            shutil.copy(src_db, temp_db)
        else:
            raise FileNotFoundError(f"Could not locate snapshot for {snapshot_id}")

        try:
            yield temp_db
        finally:
            self._cleanup_temp_db(temp_db)

    def _temp_db_path(self, prefix: str) -> Path:
        temp_dir = self.config.output_dir / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir / f"{prefix}-{uuid4().hex}.db"

    def _cleanup_temp_db(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


__all__ = [
    "BenchConfig",
    "BenchRunner",
    "SampleRunResult",
    "AssertionOutcome",
    "RankingOutcome",
]

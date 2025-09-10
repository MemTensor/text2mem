# text2mem/adapters/sqlite_adapter.py
from __future__ import annotations
import json, sqlite3
from datetime import datetime
from typing import Any, Dict, Tuple
from text2mem.adapters.base import BaseAdapter, ExecutionResult
from text2mem.core.models import IR, EncodeArgs, UpdateArgs, DeleteArgs, RetrieveArgs, TargetSpec, Filters
from text2mem.core.models import LabelArgs, PromoteArgs, DemoteArgs, SummarizeArgs
from text2mem.core.models import MergeArgs, SplitArgs, LockArgs, ExpireArgs # , ClarifyArgs
from text2mem.services.models_service import ModelsService, get_models_service

DDL = """
CREATE TABLE IF NOT EXISTS memory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT,
  type TEXT,
  tags TEXT,            -- JSON array
  facets TEXT,          -- JSON object {subject,time,location,topic}
  time TEXT,
  subject TEXT,
  location TEXT,
  topic TEXT,
  embedding TEXT,       -- JSON array, 原型先存 json
    embedding_dim INTEGER,        -- 嵌入向量维度（用于兼容性检索）
    embedding_model TEXT,         -- 嵌入模型名
    embedding_provider TEXT,      -- 嵌入提供商（ollama/openai/dummy等）
  source TEXT,
  priority TEXT,
  auto_frequency TEXT,
  expire_at TEXT,
  next_auto_update_at TEXT,
  read_perm_level TEXT,
  write_perm_level TEXT,
  read_whitelist TEXT,  -- JSON array
  read_blacklist TEXT,
  write_whitelist TEXT,
  write_blacklist TEXT,
  weight REAL,
  deleted INTEGER DEFAULT 0
);
"""

def _json(obj): return json.dumps(obj, ensure_ascii=False) if obj is not None else None

class SQLiteAdapter(BaseAdapter):
    def __init__(self, path: str = ":memory:", models_service: ModelsService = None):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DDL)
        self.models_service = models_service or get_models_service()

        # 迁移：确保新列存在
        try:
            cur = self.conn.execute("PRAGMA table_info(memory)")
            cols = {row[1] for row in cur.fetchall()}
            alters = []
            if "embedding_dim" not in cols:
                alters.append("ALTER TABLE memory ADD COLUMN embedding_dim INTEGER")
            if "embedding_model" not in cols:
                alters.append("ALTER TABLE memory ADD COLUMN embedding_model TEXT")
            if "embedding_provider" not in cols:
                alters.append("ALTER TABLE memory ADD COLUMN embedding_provider TEXT")
            for sql in alters:
                self.conn.execute(sql)
            if alters:
                self.conn.commit()
        except Exception:
            # 兼容旧SQLite或其它异常，忽略迁移失败以不阻塞
            pass

    # ---------- helpers ----------
    def _where_from_target(self, target: TargetSpec | None) -> Tuple[str, tuple]:
        if target is None:
            return "1=1", ()
        clauses, params = [], []

        if target.by_id:
            if isinstance(target.by_id, list):
                placeholders = ",".join(["?"]*len(target.by_id))
                clauses.append(f"id IN ({placeholders})"); params += target.by_id
            else:
                clauses.append("id = ?"); params.append(target.by_id)

        if target.by_tags:
            # 简单包含匹配：tags JSON LIKE '%"tag"%'
            for t in target.by_tags:
                clauses.append("tags LIKE ?")
                params.append(f'%"{t}"%')  # 原型做近似匹配，真实系统应用 JSON 查询/倒排
            if target.match == "all":
                pass  # 上面是 AND 累积；"any" 需 OR，这里简单地 AND 即可作为原型

        if target.by_query:
            # 原型关键词匹配 text/topic/subject
            clauses.append("(text LIKE ? OR topic LIKE ? OR subject LIKE ?)")
            q = f"%{target.by_query}%"
            params.extend([q, q, q])

        if target.topic:
            clauses.append("topic = ?"); params.append(target.topic)

        if target.all:
            pass

        if target.filters and target.filters.limit:
            # limit 交给执行阶段处理，这里不入 where
            pass

        if not clauses:
            return "1=1", ()
        return " AND ".join(clauses), tuple(params)

    # ---------- op handlers ----------
    def _exec_encode(self, ir: IR, args: EncodeArgs) -> ExecutionResult:
        text_val = args.payload.text or (json.dumps(args.payload.structured, ensure_ascii=False) if args.payload.structured else None)
        
        # 自动生成嵌入向量（如果未提供）
        embedding_val = args.embedding
        embedding_dim = None
        embedding_model_name = None
        embedding_provider = None
        if embedding_val is None and text_val:
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
        INSERT INTO memory (text,type,tags,facets,time,subject,location,topic,embedding,embedding_dim,embedding_model,embedding_provider,source,priority,
                            auto_frequency,expire_at,next_auto_update_at,
                            read_perm_level,write_perm_level,
                            read_whitelist,read_blacklist,write_whitelist,write_blacklist,weight,deleted)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
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
            args.priority,
            args.auto_frequency,
            args.expire_at,
            args.next_auto_update_at,
            args.read_perm_level,
            args.write_perm_level,
            _json(args.read_whitelist),
            _json(args.read_blacklist),
            _json(args.write_whitelist),
            _json(args.write_blacklist),
            None  # weight
        )
        if ir.meta and ir.meta.dry_run:
            return {
                "sql": sql,
                "params": params,
                "generated_embedding": bool(args.embedding is None),
                "embedding_dim": embedding_dim,
                "embedding_model": embedding_model_name,
                "embedding_provider": embedding_provider,
            }
        cur = self.conn.execute(sql, params); self.conn.commit()
        return {
            "inserted_id": cur.lastrowid,
            "generated_embedding": bool(args.embedding is None),
            "embedding_dim": embedding_dim,
            "embedding_model": embedding_model_name,
            "embedding_provider": embedding_provider,
        }

    def _exec_label(self, ir: IR, args: LabelArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        updates, vals = [], []
        
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
                            existing_labels=list(set(existing_tags))
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
        sets, vals = [], []
        d = args.set.model_dump(exclude_none=True)
        for k, v in d.items():
            col = {"facets":"facets","tags":"tags"}.get(k, k)
            if k in {"tags","facets","embedding","read_whitelist","read_blacklist","write_whitelist","write_blacklist"}:
                sets.append(f"{col}=?"); vals.append(_json(v if k!="embedding" else v))
            else:
                sets.append(f"{col}=?"); vals.append(v)
        sql = f"UPDATE memory SET {', '.join(sets)} WHERE {wh}"
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": tuple(vals)+ps}
        cur = self.conn.execute(sql, tuple(vals)+ps); self.conn.commit()
        return {"updated_rows": cur.rowcount}

    def _exec_promote(self, ir: IR, args: PromoteArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        sets, vals = [], []
        
        # 处理 priority
        if args.priority:
            sets.append("priority = ?")
            vals.append(args.priority)
        
        # 处理 weight_delta
        if args.weight_delta is not None:
            # 原型实现：直接设置 weight = weight + delta
            sets.append("weight = COALESCE(weight, 0) + ?")
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
        sets, vals = [], []
        
        # 处理 archive 参数（原型使用优先级降级或标记删除表示）
        if args.archive:
            # 原型实现：设置低优先级并减小权重
            sets.append("priority = ?")
            vals.append("low")
        
        # 处理 priority
        if args.priority:
            sets.append("priority = ?")
            vals.append(args.priority)
        
        # 处理 weight_delta
        if args.weight_delta is not None:
            # weight_delta 在 demote 中通常为负值
            sets.append("weight = COALESCE(weight, 0) + ?")
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
        extra = []
        if args.time_range and args.time_range.start and args.time_range.end:
            extra.append("time >= ? AND time <= ?")
            ps += (args.time_range.start, args.time_range.end)
        sql = f"UPDATE memory SET deleted=1 WHERE {wh}" if args.soft else f"DELETE FROM memory WHERE {wh}"
        if extra:
            sql = sql.replace(" WHERE ", f" WHERE {' AND '.join(extra)} AND ")
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": ps}
        cur = self.conn.execute(sql, ps); self.conn.commit()
        return {"affected_rows": cur.rowcount, "soft": args.soft}

    def _exec_summarize(self, ir: IR, args: SummarizeArgs) -> ExecutionResult:
        wh, ps = self._where_from_target(ir.target)
        
        # 添加忽略已删除
        wh = f"({wh}) AND deleted=0"
        
        # 可选的时间范围过滤
        if args.time_range:
            if args.time_range.start and args.time_range.end:
                wh += " AND time >= ? AND time <= ?"
                ps = ps + (args.time_range.start, args.time_range.end)
        
        # 检索内容
        sql = f"SELECT id, text, topic, subject FROM memory WHERE {wh} ORDER BY time DESC"
        
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": ps}
        
        rows = self.conn.execute(sql, ps).fetchall()
        
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
                max_tokens=args.max_tokens
            )
            summary = summary_result.text
            model_name = getattr(summary_result, "model", None)
            usage = getattr(summary_result, "usage", None)
        else:
            summary = "无可摘要的文本内容"
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
        """合并记忆操作"""
        wh, ps = self._where_from_target(ir.target)
        
        # 获取目标记忆
        sql = f"SELECT * FROM memory WHERE {wh} AND deleted=0"
        rows = [dict(r) for r in self.conn.execute(sql, ps).fetchall()]
        
        if not rows:
            return {"message": "没有找到需要合并的记忆", "merged_count": 0}
        
        if len(rows) < 2:
            return {"message": "至少需要2条记忆才能进行合并", "merged_count": 0}
        
        if ir.meta and ir.meta.dry_run:
            return {"message": f"模拟合并 {len(rows)} 条记忆", "strategy": args.strategy}
        
        if args.strategy == "fold_into_primary":
            # 合并到主记忆
            primary_id = args.primary_id
            if not primary_id:
                # 选择第一条作为主记忆
                primary_id = str(rows[0]["id"])
            
            # 获取主记忆
            primary = next((r for r in rows if str(r["id"]) == primary_id), None)
            if not primary:
                return {"error": f"找不到主记忆 ID: {primary_id}", "merged_count": 0}
            
            # 合并文本
            texts = [r["text"] for r in rows if r["text"] and str(r["id"]) != primary_id]
            if texts:
                merged_text = primary["text"] + "\n\n" + "\n".join(texts)
                update_sql = "UPDATE memory SET text = ? WHERE id = ?"
                self.conn.execute(update_sql, (merged_text, primary_id))
            
            # 软删除或硬删除其他记忆
            other_ids = [r["id"] for r in rows if str(r["id"]) != primary_id]
            if args.soft_delete_children:
                delete_sql = "UPDATE memory SET deleted = 1 WHERE id IN ({})".format(",".join("?" * len(other_ids)))
            else:
                delete_sql = "DELETE FROM memory WHERE id IN ({})".format(",".join("?" * len(other_ids)))
            self.conn.execute(delete_sql, other_ids)
            
            self.conn.commit()
            return {"primary_id": primary_id, "merged_count": len(other_ids), "strategy": "fold_into_primary"}
            
        else:  # link_and_keep
            # 保持所有记忆，只添加链接标记
            # 在SQLite原型中，我们通过添加标签来表示链接关系
            link_tag = f"merged_group_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            for row in rows:
                existing_tags = json.loads(row["tags"]) if row["tags"] else []
                if link_tag not in existing_tags:
                    existing_tags.append(link_tag)
                    update_sql = "UPDATE memory SET tags = ? WHERE id = ?"
                    self.conn.execute(update_sql, (_json(existing_tags), row["id"]))
            
            self.conn.commit()
            return {"link_tag": link_tag, "linked_count": len(rows), "strategy": "link_and_keep"}

    def _exec_split(self, ir: IR, args: SplitArgs) -> ExecutionResult:
        """分割记忆操作"""
        wh, ps = self._where_from_target(ir.target)
        
        # 获取目标记忆
        sql = f"SELECT * FROM memory WHERE {wh} AND deleted=0"
        rows = [dict(r) for r in self.conn.execute(sql, ps).fetchall()]
        
        if not rows:
            return {"message": "没有找到需要分割的记忆", "split_count": 0}
        
        if ir.meta and ir.meta.dry_run:
            return {"message": f"模拟分割 {len(rows)} 条记忆", "strategy": args.strategy}
        
        split_results = []
        
        for row in rows:
            text = row["text"]
            if not text:
                continue
                
            # 根据策略分割文本
            if args.strategy == "custom_spans" and args.spans:
                splits = []
                for span in args.spans:
                    start, end = span["start"], span["end"]
                    if start < len(text) and end <= len(text):
                        splits.append(text[start:end])
            elif args.strategy == "sentences":
                # 简单按句子分割
                splits = [s.strip() for s in text.split('.') if s.strip()]
            elif args.strategy == "headings":
                # 按标题分割（简单实现）
                splits = [s.strip() for s in text.split('\n') if s.strip() and (s.startswith('#') or len(s) < 100)]
            else:  # auto_by_patterns
                # 自动分割：按段落
                splits = [s.strip() for s in text.split('\n\n') if s.strip()]
            
            if len(splits) <= 1:
                continue  # 无需分割
            
            # 创建子记忆
            child_ids = []
            for i, split_text in enumerate(splits):
                if not split_text.strip():
                    continue
                    
                # 继承属性
                inherit_tags = args.inherit and args.inherit.get("tags", False)
                inherit_time = args.inherit and args.inherit.get("time", False)
                inherit_source = args.inherit and args.inherit.get("source", False)
                
                child_data = {
                    "text": split_text,
                    "type": row["type"],
                    "tags": row["tags"] if inherit_tags else None,
                    "time": row["time"] if inherit_time else None,
                    "source": row["source"] if inherit_source else None,
                    "subject": row["subject"],
                    "location": row["location"],
                    "topic": row["topic"],
                }
                
                # 添加分割标记
                if child_data["tags"]:
                    tags = json.loads(child_data["tags"])
                else:
                    tags = []
                tags.append(f"split_from_{row['id']}")
                child_data["tags"] = _json(tags)
                
                # 插入子记忆
                insert_sql = """
                INSERT INTO memory (text, type, tags, time, subject, location, topic, source, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """
                cursor = self.conn.execute(insert_sql, (
                    child_data["text"], child_data["type"], child_data["tags"],
                    child_data["time"], child_data["subject"], child_data["location"],
                    child_data["topic"], child_data["source"]
                ))
                child_ids.append(cursor.lastrowid)
            
            # 如果需要双向链接，更新原记忆
            if args.link_back == "bi_directional" and child_ids:
                original_tags = json.loads(row["tags"]) if row["tags"] else []
                original_tags.append(f"split_to_{','.join(map(str, child_ids))}")
                update_sql = "UPDATE memory SET tags = ? WHERE id = ?"
                self.conn.execute(update_sql, (_json(original_tags), row["id"]))
            
            split_results.append({
                "original_id": row["id"],
                "child_ids": child_ids,
                "split_count": len(child_ids)
            })
        
        self.conn.commit()
        return {"results": split_results, "total_splits": sum(r["split_count"] for r in split_results)}

    def _exec_lock(self, ir: IR, args: LockArgs) -> ExecutionResult:
        """锁定记忆操作"""
        wh, ps = self._where_from_target(ir.target)
        
        # 在SQLite原型中，我们通过添加特殊字段来模拟锁定
        # 实际系统中应该有专门的权限表
        lock_info = {
            "mode": args.mode,
            "reason": args.reason,
            "policy": args.policy,
            "locked_at": datetime.now().isoformat()
        }
        
        if ir.meta and ir.meta.dry_run:
            return {"message": f"模拟锁定记忆", "mode": args.mode}
        
        # 更新记忆的锁定状态（通过read_perm_level字段模拟）
        update_sql = f"""
        UPDATE memory 
        SET read_perm_level = ?, write_perm_level = ?
        WHERE {wh} AND deleted=0
        """
        
        if args.mode == "read_only":
            read_perm = "locked_read_only"
            write_perm = "locked_no_write"
        else:  # append_only
            read_perm = "locked_read_only"
            write_perm = "locked_append_only"
        
        cursor = self.conn.execute(update_sql, (read_perm, write_perm) + ps)
        affected_rows = cursor.rowcount
        
        self.conn.commit()
        return {"affected_rows": affected_rows, "mode": args.mode, "reason": args.reason}

    def _exec_expire(self, ir: IR, args: ExpireArgs) -> ExecutionResult:
        """设置记忆过期"""
        wh, ps = self._where_from_target(ir.target)
        
        # 计算过期时间
        if args.until:
            expire_time = args.until
        else:  # ttl
            # 简化处理：将ISO8601 duration转换为过期时间
            # 实际应用需要更完善的duration解析
            from datetime import datetime, timedelta
            try:
                # 简单解析，如 "P7D" -> 7天
                if args.ttl.startswith("P") and args.ttl.endswith("D"):
                    days = int(args.ttl[1:-1])
                    expire_time = (datetime.now() + timedelta(days=days)).isoformat()
                else:
                    # 默认7天后过期
                    expire_time = (datetime.now() + timedelta(days=7)).isoformat()
            except:
                expire_time = (datetime.now() + timedelta(days=7)).isoformat()
        
        if ir.meta and ir.meta.dry_run:
            return {"message": f"模拟设置过期时间", "expire_time": expire_time}
        
        # 更新过期时间
        update_sql = f"""
        UPDATE memory 
        SET expire_at = ?
        WHERE {wh} AND deleted=0
        """
        
        cursor = self.conn.execute(update_sql, (expire_time,) + ps)
        affected_rows = cursor.rowcount
        
        self.conn.commit()
        return {"affected_rows": affected_rows, "expire_time": expire_time, "on_expire": args.on_expire}

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
        wh, ps = self._where_from_target(ir.target)
        # 忽略 deleted
        wh = f"({wh}) AND deleted=0"
        
        # 语义搜索模式
        if args.order_by == "relevance" and hasattr(args, 'query') and args.query:
            if ir.meta and ir.meta.dry_run:
                return {"mode": "semantic_search", "query": args.query, "k": args.k}
            
            # 获取所有记忆的向量表示
            select_sql = f"SELECT id, text, embedding, embedding_dim, embedding_model, embedding_provider FROM memory WHERE {wh}"
            rows = self.conn.execute(select_sql, ps).fetchall()
            
            # 准备语义搜索数据
            memory_vectors = []
            # 目标维度（基于当前嵌入模型）
            try:
                target_dim = self.models_service.embedding_model.get_dimension()
            except Exception:
                target_dim = None
            skipped = 0
            for row in rows:
                embedding = json.loads(row["embedding"]) if row["embedding"] else None
                if embedding:
                    row_dim = row["embedding_dim"] if row["embedding_dim"] is not None else (len(embedding) if embedding else None)
                    # 仅收集与当前查询维度相同的向量，避免维度不匹配
                    if target_dim is None or row_dim == target_dim:
                        memory_vectors.append({
                            "id": row["id"],
                            "text": row["text"],
                            "vector": embedding
                        })
                    else:
                        skipped += 1
            
            # 执行语义搜索
            if memory_vectors:
                search_results = self.models_service.semantic_search(
                    args.query, memory_vectors, k=args.k
                )
                
                # 获取完整记忆数据
                result_ids = [r["id"] for r in search_results]
                if result_ids:
                    placeholders = ",".join("?" * len(result_ids))
                    final_sql = f"SELECT * FROM memory WHERE id IN ({placeholders})"
                    final_rows = [dict(r) for r in self.conn.execute(final_sql, result_ids).fetchall()]
                    
                    # 按相似度排序
                    id_to_similarity = {r["id"]: r["similarity"] for r in search_results}
                    final_rows.sort(key=lambda x: id_to_similarity.get(x["id"], 0), reverse=True)
                    
                    # 添加相似度信息
                    for row in final_rows:
                        row["_similarity"] = id_to_similarity.get(row["id"], 0)
                    
                    result = {"rows": final_rows, "count": len(final_rows), "mode": "semantic"}
                    if skipped:
                        result["note"] = f"skipped_incompatible_vectors={skipped}"
                    return result
                else:
                    result = {"rows": [], "count": 0, "mode": "semantic"}
                    if skipped:
                        result["note"] = f"skipped_incompatible_vectors={skipped}"
                    return result
            else:
                note = "no_embeddings"
                if skipped:
                    note += f", skipped_incompatible_vectors={skipped}"
                return {"rows": [], "count": 0, "mode": "semantic", "note": note}
        
        # 传统排序模式
        order_sql = {
            "time_desc": "time DESC",
            "time_asc": "time ASC", 
            "priority_desc": "priority DESC",
            "relevance": "id DESC"  # 降级到按ID排序
        }[args.order_by]
        limit = args.k
        sql = f"SELECT * FROM memory WHERE {wh} ORDER BY {order_sql} LIMIT ?"
        params = ps + (limit,)
        if ir.meta and ir.meta.dry_run:
            return {"sql": sql, "params": params}
        rows = [dict(r) for r in self.conn.execute(sql, params).fetchall()]
        return {"rows": rows, "count": len(rows), "mode": "traditional"}

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
            cur = self.conn.execute("SELECT priority, COUNT(*) as count FROM memory WHERE deleted=0 GROUP BY priority")
            stats["priorities"] = {row["priority"] if row["priority"] else "null": row["count"] for row in cur.fetchall()}
            
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
                "SELECT id, text, type, tags, priority, deleted FROM memory ORDER BY id DESC LIMIT ?", 
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
                ("idx_memory_priority", "CREATE INDEX IF NOT EXISTS idx_memory_priority ON memory(priority)"),
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

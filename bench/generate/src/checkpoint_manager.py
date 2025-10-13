"""
Checkpoint Manager - 断点管理器
支持进度保存和恢复
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class StageProgress:
    """阶段进度"""
    stage_name: str
    status: str  # pending, running, completed, failed
    total_batches: int
    completed_batches: int
    failed_batches: List[int] = field(default_factory=list)
    output_file: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_batches == 0:
            return 0.0
        return (self.completed_batches / self.total_batches) * 100


@dataclass
class Checkpoint:
    """断点数据"""
    plan_name: str
    total_samples: int
    created_at: str
    updated_at: str
    
    # 阶段进度
    stages: Dict[str, StageProgress] = field(default_factory=dict)
    
    # 完成的样本统计
    completed_by_scenario: Dict[str, int] = field(default_factory=dict)
    completed_by_operation: Dict[str, int] = field(default_factory=dict)
    
    # 输出文件
    output_files: Dict[str, str] = field(default_factory=dict)
    
    # 错误记录
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def total_completed(self) -> int:
        """总完成数"""
        return sum(self.completed_by_scenario.values())
    
    @property
    def progress_percentage(self) -> float:
        """总进度百分比"""
        if self.total_samples == 0:
            return 0.0
        return (self.total_completed / self.total_samples) * 100


class CheckpointManager:
    """断点管理器"""
    
    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self.checkpoint: Optional[Checkpoint] = None
    
    def load(self) -> Optional[Checkpoint]:
        """加载断点"""
        if not self.checkpoint_file.exists():
            return None
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重建Checkpoint对象
            checkpoint = Checkpoint(
                plan_name=data["plan_name"],
                total_samples=data["total_samples"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                completed_by_scenario=data.get("completed_by_scenario", {}),
                completed_by_operation=data.get("completed_by_operation", {}),
                output_files=data.get("output_files", {}),
                errors=data.get("errors", []),
            )
            
            # 重建StageProgress对象
            for stage_name, stage_data in data.get("stages", {}).items():
                checkpoint.stages[stage_name] = StageProgress(
                    stage_name=stage_data["stage_name"],
                    status=stage_data["status"],
                    total_batches=stage_data["total_batches"],
                    completed_batches=stage_data["completed_batches"],
                    failed_batches=stage_data.get("failed_batches", []),
                    output_file=stage_data.get("output_file"),
                    started_at=stage_data.get("started_at"),
                    completed_at=stage_data.get("completed_at"),
                )
            
            self.checkpoint = checkpoint
            return checkpoint
            
        except Exception as e:
            print(f"⚠️  加载断点失败: {e}")
            return None
    
    def save(self, checkpoint: Optional[Checkpoint] = None):
        """保存断点"""
        if checkpoint:
            self.checkpoint = checkpoint
        
        if not self.checkpoint:
            return
        
        # 更新时间
        self.checkpoint.updated_at = datetime.now().isoformat()
        
        # 确保目录存在
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为字典
        data = {
            "plan_name": self.checkpoint.plan_name,
            "total_samples": self.checkpoint.total_samples,
            "created_at": self.checkpoint.created_at,
            "updated_at": self.checkpoint.updated_at,
            "completed_by_scenario": self.checkpoint.completed_by_scenario,
            "completed_by_operation": self.checkpoint.completed_by_operation,
            "output_files": self.checkpoint.output_files,
            "errors": self.checkpoint.errors,
            "stages": {},
        }
        
        # 转换StageProgress
        for stage_name, stage_progress in self.checkpoint.stages.items():
            data["stages"][stage_name] = asdict(stage_progress)
        
        # 保存
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_new(self, plan_name: str, total_samples: int) -> Checkpoint:
        """创建新断点"""
        now = datetime.now().isoformat()
        self.checkpoint = Checkpoint(
            plan_name=plan_name,
            total_samples=total_samples,
            created_at=now,
            updated_at=now,
        )
        return self.checkpoint
    
    def delete(self):
        """删除断点文件"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self.checkpoint = None
    
    def update_stage_progress(
        self,
        stage_name: str,
        status: Optional[str] = None,
        total_batches: Optional[int] = None,
        completed_batches: Optional[int] = None,
        output_file: Optional[str] = None,
    ):
        """更新阶段进度"""
        if not self.checkpoint:
            return
        
        if stage_name not in self.checkpoint.stages:
            self.checkpoint.stages[stage_name] = StageProgress(
                stage_name=stage_name,
                status="pending",
                total_batches=0,
                completed_batches=0,
            )
        
        stage = self.checkpoint.stages[stage_name]
        
        if status:
            stage.status = status
            if status == "running" and not stage.started_at:
                stage.started_at = datetime.now().isoformat()
            elif status == "completed":
                stage.completed_at = datetime.now().isoformat()
        
        if total_batches is not None:
            stage.total_batches = total_batches
        
        if completed_batches is not None:
            stage.completed_batches = completed_batches
        
        if output_file:
            stage.output_file = output_file
            self.checkpoint.output_files[stage_name] = output_file
        
        self.save()
    
    def add_completed_samples(
        self,
        count: int,
        scenario: str,
        operation: str,
    ):
        """添加完成的样本统计"""
        if not self.checkpoint:
            return
        
        self.checkpoint.completed_by_scenario[scenario] = \
            self.checkpoint.completed_by_scenario.get(scenario, 0) + count
        
        self.checkpoint.completed_by_operation[operation] = \
            self.checkpoint.completed_by_operation.get(operation, 0) + count
        
        self.save()
    
    def mark_batch_failed(self, stage_name: str, batch_id: int, error: str):
        """标记批次失败"""
        if not self.checkpoint:
            return
        
        if stage_name in self.checkpoint.stages:
            stage = self.checkpoint.stages[stage_name]
            if batch_id not in stage.failed_batches:
                stage.failed_batches.append(batch_id)
        
        self.checkpoint.errors.append({
            "stage": stage_name,
            "batch_id": batch_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })
        
        self.save()
    
    def record_error(self, stage: str, batch_id: int, error: str):
        """记录错误"""
        self.mark_batch_failed(stage, batch_id, error)
    
    def get_stage_progress(self, stage_name: str) -> Optional[StageProgress]:
        """获取阶段进度"""
        if not self.checkpoint:
            return None
        return self.checkpoint.stages.get(stage_name)
    
    def get_progress_summary(self) -> str:
        """获取进度摘要"""
        if not self.checkpoint:
            return "No checkpoint found"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"📊 Generation Progress: {self.checkpoint.plan_name}")
        lines.append("=" * 60)
        lines.append(f"Overall: {self.checkpoint.total_completed}/{self.checkpoint.total_samples} "
                    f"({self.checkpoint.progress_percentage:.1f}%)")
        lines.append("")
        
        # 阶段进度
        for stage_name, stage in self.checkpoint.stages.items():
            status_emoji = {
                "pending": "⏸️",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(stage.status, "❓")
            
            lines.append(f"{status_emoji} {stage_name}: {stage.completed_batches}/{stage.total_batches} batches "
                        f"({stage.progress_percentage:.1f}%)")
        
        lines.append("")
        
        # 场景统计
        if self.checkpoint.completed_by_scenario:
            lines.append("By Scenario:")
            for scenario, count in sorted(self.checkpoint.completed_by_scenario.items()):
                lines.append(f"  {scenario}: {count}")
        
        lines.append("")
        
        # 操作统计
        if self.checkpoint.completed_by_operation:
            lines.append("By Operation:")
            for operation, count in sorted(self.checkpoint.completed_by_operation.items()):
                lines.append(f"  {operation}: {count}")
        
        # 错误统计
        if self.checkpoint.errors:
            lines.append("")
            lines.append(f"Errors: {len(self.checkpoint.errors)}")
            for error in self.checkpoint.errors[-3:]:  # 显示最后3个错误
                lines.append(f"  [{error['stage']}] Batch {error['batch_id']}: {error['error'][:60]}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)

"""
Plan Loader - 加载和解析生成计划配置
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class GenerationPlan:
    """生成计划"""
    name: str
    total_samples: int
    batch_size: int
    
    # 场景和操作配置
    scenario_proportions: Dict[str, float]
    operation_proportions: Dict[str, float]
    scenarios: Dict[str, Any]
    operations: Dict[str, Any]
    
    # 特征分布
    characteristics: Dict[str, Any]
    
    # LLM配置
    llm: Dict[str, Any]
    
    # 阶段配置
    stages: Dict[str, Any]
    
    # 输出配置
    output: Dict[str, Any]
    
    # 其他配置
    min_context_length: int = 100
    max_context_length: int = 350
    resume_from_checkpoint: bool = True
    checkpoint_file: str = ""
    validation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskBatch:
    """任务批次"""
    batch_id: int
    scenario: str
    operation: str
    count: int
    lang: str = "zh"
    structures: Optional[List[str]] = None  # single, workflow


class PlanLoader:
    """计划加载器"""
    
    @staticmethod
    def load(plan_file: Path) -> GenerationPlan:
        """加载生成计划"""
        with open(plan_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        plan_config = data.get("plan", {})
        
        return GenerationPlan(
            name=plan_config.get("name", "unnamed"),
            total_samples=plan_config.get("total_samples", 100),
            batch_size=plan_config.get("batch_size", 10),
            scenario_proportions=data.get("scenario_proportions", {}),
            operation_proportions=data.get("operation_proportions", {}),
            scenarios=data.get("scenarios", {}),
            operations=data.get("operations", {}),
            characteristics=data.get("characteristics", {}),
            llm=data.get("llm", {}),
            stages=data.get("stages", {}),
            output=data.get("output", {}),
            min_context_length=plan_config.get("min_context_length", 100),
            max_context_length=plan_config.get("max_context_length", 350),
            resume_from_checkpoint=plan_config.get("resume_from_checkpoint", True),
            checkpoint_file=plan_config.get("checkpoint_file", ""),
            validation=data.get("validation", {}),
        )
    
    @staticmethod
    def validate_plan(plan: GenerationPlan) -> List[str]:
        """验证计划配置"""
        errors = []
        
        # 验证比例总和
        scenario_sum = sum(plan.scenario_proportions.values())
        if abs(scenario_sum - 1.0) > 0.01:
            errors.append(f"场景比例总和应为1.0，当前为{scenario_sum:.3f}")
        
        operation_sum = sum(plan.operation_proportions.values())
        if abs(operation_sum - 1.0) > 0.01:
            errors.append(f"操作比例总和应为1.0，当前为{operation_sum:.3f}")
        
        # 验证场景和操作定义存在
        for scenario in plan.scenario_proportions.keys():
            if scenario not in plan.scenarios:
                errors.append(f"场景 '{scenario}' 未在scenarios中定义")
        
        for operation in plan.operation_proportions.keys():
            if operation not in plan.operations:
                errors.append(f"操作 '{operation}' 未在operations中定义")
        
        return errors


class TaskAllocator:
    """任务分配器 - 按比例分配场景和操作组合"""
    
    def __init__(self, plan: GenerationPlan):
        self.plan = plan
    
    def allocate_tasks(self, stage_name: str) -> List[TaskBatch]:
        """
        根据计划分配任务批次
        返回按 (scenario, operation) 组合的批次列表
        """
        stage_config = self.plan.stages.get(stage_name, {})
        batch_size = stage_config.get("batch_size", self.plan.batch_size)
        
        # 计算每个(scenario, operation)组合的样本数
        allocations = self._calculate_allocations()
        
        # 创建批次
        batches = []
        batch_id = 0
        
        for (scenario, operation), count in allocations.items():
            if count <= 0:
                continue
            
            # 计算该组合需要的批次数
            num_batches = (count + batch_size - 1) // batch_size
            
            for i in range(num_batches):
                # 计算该批次的样本数
                remaining = count - i * batch_size
                batch_count = min(batch_size, remaining)
                
                # 确定该批次的structure分布
                structures = self._get_structures_for_batch(batch_count)
                
                batches.append(TaskBatch(
                    batch_id=batch_id,
                    scenario=scenario,
                    operation=operation,
                    count=batch_count,
                    lang="zh",  # 默认中文
                    structures=structures,
                ))
                
                batch_id += 1
        
        return batches
    
    def _calculate_allocations(self) -> Dict[tuple, int]:
        """
        计算每个(scenario, operation)组合的样本数
        使用更合理的分配策略，确保所有操作都有样本
        """
        total = self.plan.total_samples
        allocations = {}
        
        # 检查是否是小样本情况（样本数 < 操作数 * 场景数）
        num_scenarios = len(self.plan.scenario_proportions)
        num_operations = len(self.plan.operation_proportions)
        is_small_sample = total <= (num_operations * 2)  # 每个操作至少2个样本才算正常
        
        if is_small_sample:
            # 小样本情况：优先确保操作多样性
            print(f"   ℹ️  小样本模式（{total}个样本），优先确保操作多样性")
            
            # 为每个操作分配至少1个样本
            operation_samples = {}
            remaining = total
            
            # 按操作比例分配
            for operation, prop in sorted(self.plan.operation_proportions.items(), 
                                         key=lambda x: -x[1]):  # 从大到小
                # 至少1个，最多按比例
                count = max(1, round(total * prop))
                count = min(count, remaining)  # 不超过剩余数
                operation_samples[operation] = count
                remaining -= count
                if remaining == 0:
                    break
            
            # 如果还有剩余，分配给比例最大的操作
            if remaining > 0:
                max_op = max(self.plan.operation_proportions, 
                           key=self.plan.operation_proportions.get)
                operation_samples[max_op] = operation_samples.get(max_op, 0) + remaining
            
            # 为每个操作选择场景
            for operation, op_count in operation_samples.items():
                # 在场景中轮流分配
                scenarios = list(self.plan.scenario_proportions.keys())
                for i in range(op_count):
                    scenario = scenarios[i % len(scenarios)]
                    key = (scenario, operation)
                    allocations[key] = allocations.get(key, 0) + 1
        
        else:
            # 正常样本情况：按比例分配
            # 第一步：计算理论分配（使用浮点数）
            theoretical = {}
            for scenario, scenario_prop in self.plan.scenario_proportions.items():
                for operation, operation_prop in self.plan.operation_proportions.items():
                    count = total * scenario_prop * operation_prop
                    if count >= 0.1:  # 只要理论值 >= 0.1 就考虑
                        theoretical[(scenario, operation)] = count
            
            # 第二步：先分配整数部分
            for key, value in theoretical.items():
                allocations[key] = int(value)
            
            # 第三步：计算剩余样本数
            allocated = sum(allocations.values())
            remaining = total - allocated
            
            if remaining > 0:
                # 按小数部分排序，分配剩余样本
                fractional_parts = []
                for key, value in theoretical.items():
                    fractional = value - int(value)
                    if fractional > 0:
                        fractional_parts.append((fractional, key))
                
                # 按小数部分降序排序
                fractional_parts.sort(reverse=True)
                
                # 分配剩余样本给小数部分最大的组合
                for i in range(min(remaining, len(fractional_parts))):
                    key = fractional_parts[i][1]
                    allocations[key] += 1
            
            elif remaining < 0:
                # 分配过多，从最大的组合中减少
                while remaining < 0:
                    max_key = max(allocations, key=allocations.get)
                    if allocations[max_key] > 1:  # 确保不会减到0
                        allocations[max_key] -= 1
                        remaining += 1
                    else:
                        break
        
        # 移除值为0的组合
        allocations = {k: v for k, v in allocations.items() if v > 0}
        
        return allocations
    
    def _get_structures_for_batch(self, count: int) -> List[str]:
        """
        根据计划配置的特征分布确定批次的structure列表
        
        这是structure分类的唯一决定点：
        - 从 plan.characteristics.structure 读取配置的比例（如 85% single, 15% workflow）
        - 为当前批次的样本分配具体的structure类型
        - 返回的列表将传递给Stage1 prompt，指定每个样本的structure要求
        
        这样确保structure分类完全由计划配置控制，而不是在prompt中用脆弱的百分比描述
        """
        structure_dist = self.plan.characteristics.get("structure", {})
        single_pct = self._parse_percentage(structure_dist.get("single", "85%"))
        workflow_pct = self._parse_percentage(structure_dist.get("workflow", "15%"))
        
        # 计算该批次中workflow的数量
        workflow_count = round(count * workflow_pct / 100)
        single_count = count - workflow_count
        
        structures = ["single"] * single_count + ["workflow"] * workflow_count
        return structures
    
    @staticmethod
    def _parse_percentage(value: str) -> float:
        """解析百分比字符串"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.endswith("%"):
            return float(value[:-1])
        return float(value)

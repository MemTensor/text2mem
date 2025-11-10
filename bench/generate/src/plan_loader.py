"""
Plan Loader - Load and parse generation plan configuration
"""
from __future__ import annotations

import random
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class GenerationPlan:
    """Generation plan definition"""
    name: str
    total_samples: int
    batch_size: int
    
    # Scenario and operation configuration
    scenario_proportions: Dict[str, float]
    operation_proportions: Dict[str, float]
    scenarios: Dict[str, Any]
    operations: Dict[str, Any]
    
    # Feature distributions
    characteristics: Dict[str, Any]
    
    # LLM configuration
    llm: Dict[str, Any]
    
    # Stage configuration
    stages: Dict[str, Any]
    
    # Output configuration
    output: Dict[str, Any]
    
    # Other configuration
    min_context_length: int = 100
    max_context_length: int = 350
    resume_from_checkpoint: bool = True
    checkpoint_file: str = ""
    validation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskBatch:
    """Task batch unit"""
    batch_id: int
    scenario: str
    operation: str
    count: int
    lang: str = "zh"
    structures: Optional[List[str]] = None  # e.g., ["single", "workflow"]


class PlanLoader:
    """Plan loader"""
    
    @staticmethod
    def load(plan_file: Path) -> GenerationPlan:
        """Load generation plan from YAML file"""
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
        """Validate generation plan configuration"""
        errors = []
        
        # Validate proportions sum to 1.0
        scenario_sum = sum(plan.scenario_proportions.values())
        if abs(scenario_sum - 1.0) > 0.01:
            errors.append(f"Scenario proportions must sum to 1.0, got {scenario_sum:.3f}")
        
        operation_sum = sum(plan.operation_proportions.values())
        if abs(operation_sum - 1.0) > 0.01:
            errors.append(f"Operation proportions must sum to 1.0, got {operation_sum:.3f}")
        
        # Validate scenario and operation definitions exist
        for scenario in plan.scenario_proportions.keys():
            if scenario not in plan.scenarios:
                errors.append(f"Scenario '{scenario}' not defined in 'scenarios'")
        
        for operation in plan.operation_proportions.keys():
            if operation not in plan.operations:
                errors.append(f"Operation '{operation}' not defined in 'operations'")
        
        return errors


class TaskAllocator:
    """Task allocator - distribute (scenario, operation) combinations proportionally"""
    
    def __init__(self, plan: GenerationPlan):
        self.plan = plan
    
    def allocate_tasks(self, stage_name: str) -> List[TaskBatch]:
        """
        Allocate task batches based on the plan configuration.
        Returns a list of TaskBatch objects for each (scenario, operation) combination.
        """
        stage_config = self.plan.stages.get(stage_name, {})
        batch_size = stage_config.get("batch_size", self.plan.batch_size)
        
        # Calculate sample allocation for each (scenario, operation)
        allocations = self._calculate_allocations()
        
        # Create batches
        batches = []
        batch_id = 0
        
        for (scenario, operation), count in allocations.items():
            if count <= 0:
                continue
            
            # Determine the number of batches for this combination
            num_batches = (count + batch_size - 1) // batch_size
            
            for i in range(num_batches):
                # Determine sample count for the current batch
                remaining = count - i * batch_size
                batch_count = min(batch_size, remaining)
                
                # Determine structure distribution for this batch
                structures = self._get_structures_for_batch(batch_count)
                
                # Determine language for this batch
                lang = self._get_lang_for_batch()
                
                batches.append(TaskBatch(
                    batch_id=batch_id,
                    scenario=scenario,
                    operation=operation,
                    count=batch_count,
                    lang=lang,
                    structures=structures,
                ))
                
                batch_id += 1
        
        return batches
    
    def _calculate_allocations(self) -> Dict[tuple, int]:
        """
        Calculate the number of samples for each (scenario, operation) combination.
        Uses an adaptive strategy to ensure every operation has at least some samples.
        """
        total = self.plan.total_samples
        allocations = {}
        
        # Check if this is a small-sample case (few samples compared to combinations)
        num_scenarios = len(self.plan.scenario_proportions)
        num_operations = len(self.plan.operation_proportions)
        is_small_sample = total <= (num_operations * 2)  # at least ~2 samples per operation
        
        if is_small_sample:
            # Small sample case: prioritize operation diversity
            print(f"   ℹ️  Small-sample mode ({total} samples), prioritizing operation diversity")
            
            # Allocate at least one sample per operation
            operation_samples = {}
            remaining = total
            
            # Sort operations by proportion (descending)
            for operation, prop in sorted(self.plan.operation_proportions.items(), key=lambda x: -x[1]):
                count = max(1, round(total * prop))
                count = min(count, remaining)
                operation_samples[operation] = count
                remaining -= count
                if remaining == 0:
                    break
            
            # Distribute remaining samples to the highest-proportion operation
            if remaining > 0:
                max_op = max(self.plan.operation_proportions, key=self.plan.operation_proportions.get)
                operation_samples[max_op] = operation_samples.get(max_op, 0) + remaining
            
            # Assign scenarios for each operation
            for operation, op_count in operation_samples.items():
                scenarios = list(self.plan.scenario_proportions.keys())
                for i in range(op_count):
                    scenario = scenarios[i % len(scenarios)]
                    key = (scenario, operation)
                    allocations[key] = allocations.get(key, 0) + 1
        
        else:
            # Normal sample case: proportional allocation
            theoretical = {}
            for scenario, scenario_prop in self.plan.scenario_proportions.items():
                for operation, operation_prop in self.plan.operation_proportions.items():
                    count = total * scenario_prop * operation_prop
                    if count >= 0.1:
                        theoretical[(scenario, operation)] = count
            
            # Assign integer parts
            for key, value in theoretical.items():
                allocations[key] = int(value)
            
            # Compute remaining samples
            allocated = sum(allocations.values())
            remaining = total - allocated
            
            if remaining > 0:
                # Distribute remaining samples based on fractional parts
                fractional_parts = []
                for key, value in theoretical.items():
                    fractional = value - int(value)
                    if fractional > 0:
                        fractional_parts.append((fractional, key))
                
                fractional_parts.sort(reverse=True)
                
                for i in range(min(remaining, len(fractional_parts))):
                    key = fractional_parts[i][1]
                    allocations[key] += 1
            
            elif remaining < 0:
                # Over-allocated: reduce from largest allocations
                while remaining < 0:
                    max_key = max(allocations, key=allocations.get)
                    if allocations[max_key] > 1:
                        allocations[max_key] -= 1
                        remaining += 1
                    else:
                        break
        
        # Remove zero-value entries
        allocations = {k: v for k, v in allocations.items() if v > 0}
        
        return allocations
    
    def _get_structures_for_batch(self, count: int) -> List[str]:
        """
        Determine structure types for this batch based on plan configuration.
        
        This is the only point that determines structure classification:
        - Read distribution from plan.characteristics['structure'] (e.g., 85% single, 15% workflow)
        - Assign each sample in the batch a concrete structure type
        - The resulting list will be passed to Stage 1 prompts
        
        Ensures structure distribution is fully controlled by plan configuration,
        rather than relying on prompt instructions.
        """
        structure_dist = self.plan.characteristics.get("structure", {})
        single_pct = self._parse_percentage(structure_dist.get("single", "85%"))
        workflow_pct = self._parse_percentage(structure_dist.get("workflow", "15%"))
        
        workflow_count = round(count * workflow_pct / 100)
        single_count = count - workflow_count
        
        structures = ["single"] * single_count + ["workflow"] * workflow_count
        return structures
    
    def _get_lang_for_batch(self) -> str:
        """Randomly select language for this batch based on 'lang' distribution in characteristics"""
        lang_dist = self.plan.characteristics.get("lang", {})
        
        if not lang_dist:
            # Default to Chinese if no configuration
            return "zh"
        
        langs = []
        weights = []
        for lang, pct in lang_dist.items():
            langs.append(lang)
            weights.append(self._parse_percentage(pct))
        
        return random.choices(langs, weights=weights, k=1)[0]
    
    @staticmethod
    def _parse_percentage(value: str) -> float:
        """Parse percentage string to float"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.endswith("%"):
            return float(value[:-1])
        return float(value)

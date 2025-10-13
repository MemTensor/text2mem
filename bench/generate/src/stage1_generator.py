"""
Stage 1 Generator - 自然语言指令生成器
根据场景和操作生成真实的用户指令
"""
from __future__ import annotations

import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from bench.generate.src.llm_client import LLMClient
from bench.generate.src.plan_loader import TaskBatch, GenerationPlan


@dataclass
class NLInstruction:
    """自然语言指令"""
    instruction: str
    context: str
    classification: Dict[str, str]
    scenario_info: Dict[str, Any]


class Stage1Generator:
    """Stage 1: NL指令生成器"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        plan: GenerationPlan,
        seeds_dir: Path,
    ):
        self.llm_client = llm_client
        self.plan = plan
        self.seeds_dir = seeds_dir
        
        # 加载prompt模板
        self.prompt_template = self._load_prompt_template()
        
        # 加载seeds数据
        self.scenarios_config = self._load_scenarios()
        self.operations_config = self._load_operations()
    
    def _load_prompt_template(self) -> str:
        """加载prompt模板"""
        template_file = self.seeds_dir.parent / "prompts" / "stage1_nl_generation.md"
        
        if not template_file.exists():
            raise FileNotFoundError(f"Prompt模板未找到: {template_file}")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_scenarios(self) -> Dict[str, Any]:
        """加载场景配置"""
        scenarios_file = self.seeds_dir / "scenarios.yaml"
        
        if not scenarios_file.exists():
            return {}
        
        with open(scenarios_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return data.get("scenarios", {})
    
    def _load_operations(self) -> Dict[str, Any]:
        """加载操作配置"""
        operations_file = self.seeds_dir / "operations.yaml"
        
        if not operations_file.exists():
            return {}
        
        with open(operations_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return data.get("operations", {})
    
    def generate_batch(self, batch: TaskBatch) -> List[NLInstruction]:
        """
        生成一批NL指令
        支持多次重试
        
        Args:
            batch: 任务批次
            
        Returns:
            NL指令列表
        """
        max_attempts = 3  # 最多尝试3次
        
        for attempt in range(max_attempts):
            try:
                # 构建prompt
                prompt = self._build_prompt(batch)
                
                # 调用LLM
                response = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=4000,
                )
                
                # 解析响应
                instructions = self._parse_response(response.content, batch)
                
                if instructions:
                    # 验证
                    errors = self.validate_instructions(instructions, batch)
                    
                    # 如果没有严重错误，或者数量足够，就接受
                    if not errors or len(instructions) >= batch.count * 0.8:
                        if attempt > 0:
                            print(f"      ✅ 第{attempt + 1}次尝试成功")
                        return instructions
                    else:
                        # 验证失败太多，重试
                        if attempt < max_attempts - 1:
                            print(f"      ⚠️  第{attempt + 1}次尝试质量不足")
                            print(f"      🔄 重试中...")
                            continue
                else:
                    # 解析失败，重试
                    if attempt < max_attempts - 1:
                        print(f"      ⚠️  第{attempt + 1}次尝试解析失败")
                        print(f"      🔄 重试中...")
                        continue
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"      ⚠️  第{attempt + 1}次尝试出错: {e}")
                    print(f"      🔄 重试中...")
                    import time
                    time.sleep(2)
                    continue
                else:
                    raise
        
        # 如果所有尝试都失败了，返回空列表（而不是抛出异常）
        return []
    
    def _build_prompt(self, batch: TaskBatch) -> str:
        """构建生成prompt"""
        # 获取场景和操作配置
        scenario_config = self.scenarios_config.get(batch.scenario, {})
        operation_config = self.operations_config.get(batch.operation, {})
        
        # 判断是否为workflow批次
        is_workflow = batch.structures and "workflow" in batch.structures
        workflow_count = batch.structures.count("workflow") if batch.structures else 0
        
        # 构建操作表达方式
        expressions = operation_config.get("expressions_zh", [])
        operation_expressions = "\n".join([f"- {expr}" for expr in expressions[:5]])
        
        # 填充模板
        prompt = self.prompt_template
        
        # 替换变量
        replacements = {
            "{count}": str(batch.count),
            "{operation}": batch.operation,
            "{operation_name}": operation_config.get("name", batch.operation),
            "{operation_description}": operation_config.get("description", ""),
            "{operation_expressions}": operation_expressions,
            "{scenario}": scenario_config.get("name", batch.scenario),
            "{scenario_description}": scenario_config.get("description", ""),
            "{lang}": batch.lang,
            "{min_context_length}": str(self.plan.min_context_length),
            "{max_context_length}": str(self.plan.max_context_length),
            "{context_length_range}": f"{self.plan.min_context_length}-{self.plan.max_context_length}",
        }
        
        for key, value in replacements.items():
            prompt = prompt.replace(key, value)
        
        # 添加workflow特殊说明
        if is_workflow and workflow_count > 0:
            prompt += f"\n\n⚠️ **特别要求**: 本批次需要生成 {workflow_count} 个workflow类型的样本（明确包含3+步骤的流程指令）。"
        
        return prompt
    
    def _parse_response(self, content: str, batch: TaskBatch) -> List[NLInstruction]:
        """解析LLM响应"""
        # 提取JSON内容
        content = content.strip()
        
        # 尝试查找JSON数组
        start = content.find('[')
        end = content.rfind(']')
        
        if start == -1 or end == -1:
            print(f"      ⚠️  未找到JSON数组")
            return []
        
        json_str = content[start:end+1]
        
        try:
            data = json.loads(json_str)
            
            if not isinstance(data, list):
                print(f"      ⚠️  响应不是数组")
                return []
            
            # 转换为NLInstruction对象
            instructions = []
            for item in data:
                try:
                    instruction = NLInstruction(
                        instruction=item.get("instruction", ""),
                        context=item.get("context", ""),
                        classification=item.get("classification", {}),
                        scenario_info=item.get("scenario_info", {}),
                    )
                    instructions.append(instruction)
                except Exception as e:
                    print(f"      ⚠️  解析指令失败: {e}")
                    continue
            
            return instructions
            
        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON解析失败: {e}")
            return []
    
    def validate_instructions(
        self,
        instructions: List[NLInstruction],
        batch: TaskBatch,
    ) -> List[str]:
        """
        验证生成的指令
        
        Returns:
            错误列表，如果为空则验证通过
        """
        errors = []
        
        for idx, instruction in enumerate(instructions):
            # 验证必填字段
            if not instruction.instruction:
                errors.append(f"样本{idx}: instruction为空")
            
            if not instruction.context:
                errors.append(f"样本{idx}: context为空")
            
            # 验证context长度
            context_len = len(instruction.context)
            if context_len < self.plan.min_context_length:
                errors.append(f"样本{idx}: context长度{context_len}小于最小值{self.plan.min_context_length}")
            
            # 验证classification
            if not instruction.classification:
                errors.append(f"样本{idx}: classification为空")
            else:
                required_fields = ["instruction_type", "structure", "lang"]
                for field in required_fields:
                    if field not in instruction.classification:
                        errors.append(f"样本{idx}: classification缺少{field}")
            
            # 验证scenario_info
            if not instruction.scenario_info:
                errors.append(f"样本{idx}: scenario_info为空")
            else:
                # 验证operation字段
                if instruction.scenario_info.get("operation") != batch.operation:
                    errors.append(
                        f"样本{idx}: operation不匹配，期望{batch.operation}，"
                        f"实际{instruction.scenario_info.get('operation')}"
                    )
        
        # 验证数量
        if len(instructions) < batch.count * 0.8:  # 允许20%的容错
            errors.append(f"生成数量不足: 期望{batch.count}，实际{len(instructions)}")
        
        return errors

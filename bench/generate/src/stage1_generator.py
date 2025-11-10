"""
Stage 1 Generator - Natural language instruction generator
Generates realistic user instructions based on scenario and operation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from bench.generate.src.llm_client import LLMClient
from bench.generate.src.plan_loader import TaskBatch, GenerationPlan


@dataclass
class NLInstruction:
    """Natural language instruction"""
    instruction: str
    context: str
    classification: Dict[str, str]
    scenario_info: Dict[str, Any]


class Stage1Generator:
    """Stage 1: Natural language instruction generator"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        plan: GenerationPlan,
        prompts_dir: Path,
    ):
        self.llm_client = llm_client
        self.plan = plan
        self.prompts_dir = prompts_dir
        
        # Load prompt templates (supports both Chinese and English)
        self.prompt_templates = {
            'zh': self._load_prompt_template('stage1_nl_generation.md'),
            'en': self._load_prompt_template('en_stage1_nl_generation.md'),
        }
    
    def _load_prompt_template(self, filename: str) -> str:
        """Load prompt template file
        
        Args:
            filename: Template file name.
            
        Returns:
            Template content.
        """
        template_file = self.prompts_dir / filename
        
        if not template_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_file}")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def generate_batch(self, batch: TaskBatch) -> List[NLInstruction]:
        """
        Generate a batch of NL instructions with retry support.
        
        Args:
            batch: Task batch definition.
            
        Returns:
            A list of NLInstruction objects.
        """
        max_attempts = 3  # Maximum of 3 attempts
        
        for attempt in range(max_attempts):
            try:
                # Build prompt
                prompt = self._build_prompt(batch)
                
                # Call LLM
                response = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=4000,
                )
                
                # Parse response
                instructions = self._parse_response(response.content, batch)
                
                if instructions:
                    # Validate
                    errors = self.validate_instructions(instructions, batch)
                    
                    # Accept if no severe errors or enough samples generated
                    if not errors or len(instructions) >= batch.count * 0.8:
                        if attempt > 0:
                            print(f"      ✅ Attempt {attempt + 1} succeeded")
                        return instructions
                    else:
                        # Validation failed, retry if attempts remain
                        if attempt < max_attempts - 1:
                            print(f"      ⚠️  Attempt {attempt + 1} had poor quality")
                            print(f"      🔄 Retrying...")
                            continue
                else:
                    # Failed to parse, retry
                    if attempt < max_attempts - 1:
                        print(f"      ⚠️  Attempt {attempt + 1} failed to parse response")
                        print(f"      🔄 Retrying...")
                        continue
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"      ⚠️  Attempt {attempt + 1} encountered an error: {e}")
                    print(f"      🔄 Retrying...")
                    import time
                    time.sleep(2)
                    continue
                else:
                    raise
        
        # If all attempts failed, return an empty list instead of raising an exception
        return []
    
    def _build_prompt(self, batch: TaskBatch) -> str:
        """
        Build the generation prompt.
        
        Key design:
        - `batch.structures` is already assigned by TaskAllocator according to the plan configuration.
        - This method injects explicit sample counts (e.g., "7 single + 1 workflow") into the prompt.
        - Avoid using percentages in prompts to prevent LLM misinterpretation.
        - Select prompt language (Chinese or English) based on `batch.lang`.
        """
        # Count structure types in this batch
        workflow_count = batch.structures.count("workflow") if batch.structures else 0
        single_count = batch.structures.count("single") if batch.structures else batch.count
        
        # Choose prompt template based on language
        lang = batch.lang if batch.lang in ['zh', 'en'] else 'zh'
        prompt_template = self.prompt_templates.get(lang, self.prompt_templates['zh'])
        
        # Fill in placeholders
        prompt = prompt_template
        
        replacements = {
            "{count}": str(batch.count),
            "{operation}": batch.operation,
            "{operation_name}": batch.operation,
            "{operation_description}": "",
            "{operation_expressions}": "",
            "{scenario}": batch.scenario,
            "{scenario_description}": "",
            "{lang}": batch.lang,
            "{min_context_length}": str(self.plan.min_context_length),
            "{max_context_length}": str(self.plan.max_context_length),
            "{context_length_range}": f"{self.plan.min_context_length}-{self.plan.max_context_length}",
        }
        
        for key, value in replacements.items():
            prompt = prompt.replace(key, value)
        
        # Add explicit structure requirements (in quantities, not percentages)
        if workflow_count > 0 or single_count > 0:
            structure_requirement = []
            
            if lang == 'zh':
                if single_count > 0:
                    structure_requirement.append(f"**{single_count} 个 single type**（单一操作）")
                if workflow_count > 0:
                    structure_requirement.append(f"**{workflow_count} 个 workflow type**（3步以上流程）")
                
                prompt += f"\n\n## ⚠️ 本批次结构要求\n\n请生成：{' 和 '.join(structure_requirement)}\n\n"
                prompt += "**重要**：\n"
                prompt += f"- 必须生成 **恰好 {batch.count} 个样本**\n"
                if single_count > 0:
                    prompt += f"- 其中 **{single_count} 个** 必须是 single 结构（单一操作请求）\n"
                if workflow_count > 0:
                    prompt += f"- 其中 **{workflow_count} 个** 必须是 workflow 结构（包含3步及以上的流程）\n"
                prompt += "\n请严格遵守数量要求，不能多也不能少。\n"
            else:  # English
                if single_count > 0:
                    structure_requirement.append(f"**{single_count} single type** (single operation)")
                if workflow_count > 0:
                    structure_requirement.append(f"**{workflow_count} workflow type** (3+ step process)")
                
                prompt += f"\n\n## ⚠️ Structure Requirements for This Batch\n\nPlease generate: {' and '.join(structure_requirement)}\n\n"
                prompt += "**Important**:\n"
                prompt += f"- You must generate **exactly {batch.count} samples**\n"
                if single_count > 0:
                    prompt += f"- Of which **{single_count}** must be single structure (single operation request)\n"
                if workflow_count > 0:
                    prompt += f"- Of which **{workflow_count}** must be workflow structure (3+ step process)\n"
                prompt += "\nPlease strictly follow the quantity requirements — no more, no less.\n"
        
        return prompt
    
    def _parse_response(self, content: str, batch: TaskBatch) -> List[NLInstruction]:
        """Parse LLM response content into structured instructions"""
        content = content.strip()
        
        # Attempt to extract JSON array
        start = content.find('[')
        end = content.rfind(']')
        
        if start == -1 or end == -1:
            print(f"      ⚠️  JSON array not found")
            return []
        
        json_str = content[start:end+1]
        
        try:
            data = json.loads(json_str)
            
            if not isinstance(data, list):
                print(f"      ⚠️  Response is not a JSON array")
                return []
            
            # Convert to NLInstruction objects
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
                    print(f"      ⚠️  Failed to parse instruction: {e}")
                    continue
            
            return instructions
            
        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON parsing failed: {e}")
            return []
    
    def validate_instructions(
        self,
        instructions: List[NLInstruction],
        batch: TaskBatch,
    ) -> List[str]:
        """
        Validate the generated instructions.
        
        Returns:
            A list of error messages. Empty list means validation passed.
        """
        errors = []
        
        for idx, instruction in enumerate(instructions):
            # Required field validation
            if not instruction.instruction:
                errors.append(f"sample {idx}: instruction is empty")
            
            if not instruction.context:
                errors.append(f"sample {idx}: context is empty")
            
            # Validate context length
            context_len = len(instruction.context)
            if context_len < self.plan.min_context_length:
                errors.append(f"sample {idx}: context length {context_len} below minimum {self.plan.min_context_length}")
            
            # Validate classification
            if not instruction.classification:
                errors.append(f"sample {idx}: classification is empty")
            else:
                required_fields = ["instruction_type", "structure", "lang"]
                for field in required_fields:
                    if field not in instruction.classification:
                        errors.append(f"sample {idx}: classification missing '{field}'")
            
            # Validate scenario info
            if not instruction.scenario_info:
                errors.append(f"sample {idx}: scenario_info is empty")
            else:
                if instruction.scenario_info.get("operation") != batch.operation:
                    errors.append(
                        f"sample {idx}: operation mismatch, expected '{batch.operation}', "
                        f"got '{instruction.scenario_info.get('operation')}'"
                    )
        
        # Validate total count
        if len(instructions) < batch.count * 0.8:  # Allow 20% tolerance
            errors.append(f"Insufficient generated samples: expected {batch.count}, got {len(instructions)}")
        
        return errors

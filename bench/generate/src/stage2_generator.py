"""
Stage 2 Generator - IR Schema Generator
Converts NL instructions into Text2Mem IR format.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from bench.generate.src.llm_client import LLMClient, LLMConfig
from bench.generate.src.plan_loader import GenerationPlan


@dataclass
class IRSample:
    """IR test sample (output of Stage 2)"""
    id: str
    class_info: Dict[str, str]
    nl: Dict[str, str]
    prerequisites: List[Dict[str, Any]]
    schema_list: List[Dict[str, Any]]
    init_db: Optional[Any]
    notes: str


class Stage2Generator:
    """Stage 2: IR Schema Generator"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        plan: GenerationPlan,
        prompts_dir: Path,
        llm_config: LLMConfig,
    ):
        self.llm_client = llm_client
        self.plan = plan
        self.prompts_dir = prompts_dir
        self.llm_config = llm_config
        
        # Load prompt templates (supports both Chinese and English)
        self.prompt_templates = {
            'zh': self._load_prompt_template("stage2_ir_generation.md"),
            'en': self._load_prompt_template("en_stage2_ir_generation.md"),
        }
        
        # ID counter
        self.id_counter = 0
    
    def _log(self, message: str, level: str = "INFO", verbose_only: bool = False):
        """Simple logging utility"""
        if verbose_only:
            # TODO: Add verbose mode toggle
            return
        
        prefix = {
            "INFO": "ℹ️ ",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }.get(level, "")
        print(f"   {prefix} {message}")
    
    def _load_prompt_template(self, filename: str) -> str:
        """Load Stage 2 prompt template file
        
        Args:
            filename: Template file name.
            
        Returns:
            Template content.
        """
        prompt_file = self.prompts_dir / filename
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
        
        return prompt_file.read_text(encoding="utf-8")
    
    def generate_single(self, nl_instruction: Dict[str, Any]) -> Optional[IRSample]:
        """
        Generate an IR sample from a single NL instruction.
        Supports multiple retry attempts.
        
        Args:
            nl_instruction: Single NL instruction generated from Stage 1.
        
        Returns:
            An IRSample object, or None if all attempts failed.
        """
        max_attempts = 3  # Try up to 3 times
        
        for attempt in range(max_attempts):
            try:
                # Build prompt
                prompt = self._build_single_prompt(nl_instruction)
                
                # Call LLM
                response = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.5,  # Lower temperature for structured output
                    max_tokens=4000,
                )
                
                # Parse response
                sample = self._parse_response(response.content, nl_instruction)
                
                if sample:
                    # Validate result
                    errors = self.validate_samples([sample], None)
                    if not errors:
                        if attempt > 0:
                            print(f"      ✅ Attempt {attempt + 1} succeeded")
                        return sample
                    else:
                        if attempt < max_attempts - 1:
                            print(f"      ⚠️  Attempt {attempt + 1} validation failed: {errors[0]}")
                            print(f"      🔄 Retrying...")
                            continue
                else:
                    if attempt < max_attempts - 1:
                        print(f"      ⚠️  Attempt {attempt + 1} failed to parse")
                        print(f"      🔄 Retrying...")
                        continue
                    
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"      ⚠️  Attempt {attempt + 1} encountered an error: {e}")
                    print(f"      🔄 Retrying...")
                    import time
                    time.sleep(1)
                    continue
                else:
                    print(f"      ❌ All attempts failed")
        
        # All attempts failed
        return None
    
    def _build_single_prompt(self, nl_instruction: Dict[str, Any]) -> str:
        """Build the prompt for a single NL instruction using template file"""
        classification = nl_instruction.get('classification', {})
        scenario_info = nl_instruction.get('scenario_info', {})
        structure = classification.get('structure', 'single')
        operation = scenario_info.get('operation', 'unknown')
        instruction = nl_instruction.get('instruction', '')
        context = nl_instruction.get('context', '')
        lang = classification.get('lang', 'zh')
        
        # Select prompt template by language
        prompt_template = self.prompt_templates.get(lang, self.prompt_templates['zh'])
        
        prompt = prompt_template
        prompt = prompt.replace('{instruction}', instruction)
        prompt = prompt.replace('{context}', context)
        prompt = prompt.replace('{instruction_type}', classification.get('instruction_type', 'direct'))
        prompt = prompt.replace('{structure}', structure)
        prompt = prompt.replace('{lang}', classification.get('lang', 'zh'))
        prompt = prompt.replace('{scenario}', scenario_info.get('scenario', ''))
        prompt = prompt.replace('{operation}', operation)
        prompt = prompt.replace('{style}', scenario_info.get('style', 'casual'))
        prompt = prompt.replace('{topic}', scenario_info.get('topic', ''))
        
        return prompt
    
    def _parse_response(self, content: str, nl_instruction: Dict[str, Any]) -> Optional[IRSample]:
        """Parse LLM response — attempts to extract and repair JSON"""
        original_content = content
        content = content.strip()
        
        # Step 1: Clean up markdown and wrapper artifacts
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        # Remove common descriptive prefixes (English & Chinese)
        patterns = [
            r'^[^{]*?(?:generate|输出|结果|sample|output|result)[^{]*?[:：]\s*',
            r'^[^{]*?(?:以下|following|below)[^{]*?[:：]\s*',
        ]
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        content = content.strip()
        
        # Step 2: Attempt to parse JSON
        data = None
        parse_method = None
        
        try:
            data = json.loads(content)
            parse_method = "direct"
        except json.JSONDecodeError:
            try:
                from json import JSONDecoder
                decoder = JSONDecoder()
                data, idx = decoder.raw_decode(content)
                parse_method = "raw_decode"
                
                if idx < len(content.strip()):
                    remaining = content[idx:].strip()
                    if remaining and len(remaining) > 10:
                        self._log(f"      ⚠️  Extra content detected after JSON (ignored): {remaining[:80]}...", verbose_only=True)
            except (json.JSONDecodeError, ValueError):
                data = self._extract_json_by_braces(content)
                if data:
                    parse_method = "brace_matching"
        
        if data is None:
            print(f"      ❌ JSON parsing completely failed")
            print(f"      Original content length: {len(original_content)} chars")
            print(f"      First 200 chars: {original_content[:200]}")
            self._save_failed_response(original_content, nl_instruction, "stage2")
            return None
        
        # Step 3: Validate required fields
        required_fields = ["prerequisites", "schema_list"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print(f"      ⚠️  Missing required JSON fields: {missing_fields}")
            print(f"      Available keys: {list(data.keys())}")
            return None
        
        # Step 4: Build IRSample object
        try:
            self.id_counter += 1
            
            classification = data.get("class", nl_instruction.get("classification", {}))
            
            # Normalize field names
            if "instruction" in classification and "instruction_type" not in classification:
                classification["instruction_type"] = classification.pop("instruction")
            
            lang = classification.get("lang", "zh")
            instruction_type = classification.get("instruction_type", "direct")
            structure = classification.get("structure", "single")
            
            schema_list = data.get("schema_list", [])
            op_abbr = "unk"
            if schema_list:
                op = schema_list[0].get("op", "Unknown")
                op_map = {
                    "Encode": "enc", "Retrieve": "ret", "Update": "upd",
                    "Delete": "del", "Summarize": "sum", "Label": "lbl",
                    "Promote": "pro", "Demote": "dem", "Expire": "exp",
                    "Lock": "lck", "Merge": "mrg", "Split": "spl",
                }
                op_abbr = op_map.get(op, "unk")
            
            sample_id = f"t2m-{lang}-{instruction_type}-{structure}-{op_abbr}-{self.id_counter:03d}"
            
            sample = IRSample(
                id=sample_id,
                class_info=classification,
                nl=data.get("nl", {"zh": nl_instruction.get("instruction", "")}),
                prerequisites=data.get("prerequisites", []),
                schema_list=schema_list,
                init_db=data.get("init_db"),
                notes=data.get("notes", ""),
            )
            
            self._log(f"      ✅ Successfully parsed (method: {parse_method})", verbose_only=True)
            return sample
            
        except Exception as e:
            print(f"      ❌ Failed to construct IRSample: {e}")
            return None
    
    def _extract_json_by_braces(self, content: str) -> Optional[Dict]:
        """Extract JSON object by matching braces and attempt to repair"""
        start = content.find('{')
        if start == -1:
            return None
        
        json_str = self._extract_balanced_json(content, start)
        if not json_str:
            return None
        
        for attempt in range(6):
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    json_str = re.sub(r'//.*', '', json_str)
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                elif attempt == 1:
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                elif attempt == 2:
                    if '}}],"init_db"' in json_str or '}}],"notes"' in json_str:
                        json_str = re.sub(r'(\}\})\],\s*"(init_db|notes|expected)', r'\1}],"\2', json_str)
                        print(f"      🔧 Fixed missing closing brace in schema_list")
                elif attempt == 3:
                    json_str = self._auto_complete_braces(json_str)
                elif attempt == 4:
                    json_str = re.sub(r'}\s*{', '},{', json_str)
                else:
                    print(f"      ⚠️  All JSON repair attempts failed: {e}")
                    if hasattr(e, "pos") and e.pos < len(json_str):
                        start_show = max(0, e.pos - 50)
                        end_show = min(len(json_str), e.pos + 50)
                        print(f"      Error near: ...{json_str[start_show:end_show]}...")
                    return None
        
        return None
    
    def _extract_balanced_json(self, content: str, start: int) -> Optional[str]:
        """Extract a balanced JSON substring by tracking braces/brackets"""
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(content)):
            char = content[i]
            
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                
                if brace_count == 0 and bracket_count == 0 and i > start:
                    return content[start:i+1]
        
        return content[start:]
    
    def _auto_complete_braces(self, json_str: str) -> str:
        """Automatically complete missing braces/brackets"""
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False
        
        for char in json_str:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
        
        result = json_str
        if bracket_count > 0:
            result += ']' * bracket_count
            print(f"      🔧 Auto-completed {bracket_count} closing square brackets ]")
        if brace_count > 0:
            result += '}' * brace_count
            print(f"      🔧 Auto-completed {brace_count} closing curly braces }}")
        
        return result
    
    def _save_failed_response(self, content: str, nl_instruction: Dict[str, Any], stage: str):
        """Save failed LLM response for debugging"""
        try:
            from pathlib import Path
            from datetime import datetime
            
            log_dir = Path("bench/generate/output/failed_responses")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            instruction_id = nl_instruction.get("id", "unknown")
            filename = f"failed_{stage}_{instruction_id}_{timestamp}.txt"
            
            log_file = log_dir / filename
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"Failed to parse LLM response - {stage.upper()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Instruction ID: {instruction_id}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Content length: {len(content)} characters\n\n")
                f.write("=" * 80 + "\nOriginal response:\n")
                f.write("=" * 80 + "\n")
                f.write(content)
                f.write("\n\n")
                f.write("=" * 80 + "\nInput instruction:\n")
                f.write("=" * 80 + "\n")
                f.write(json.dumps(nl_instruction, ensure_ascii=False, indent=2))
            
            print(f"      💾 Saved failed response to: {log_file}")
            
        except Exception as e:
            print(f"      ⚠️  Error while saving failed response: {e}")
    
    def validate_samples(
        self,
        samples: List[IRSample],
        batch: Any,
    ) -> List[str]:
        """Validate generated IR samples"""
        errors = []
        
        for idx, sample in enumerate(samples):
            if not sample.id:
                errors.append(f"sample {idx}: missing id")
            
            if not sample.schema_list:
                errors.append(f"sample {idx}: schema_list is empty")
            
            for ir_idx, ir in enumerate(sample.schema_list):
                if "stage" not in ir:
                    errors.append(f"sample {idx}, IR {ir_idx}: missing 'stage' field")
                if "op" not in ir:
                    errors.append(f"sample {idx}, IR {ir_idx}: missing 'op' field")
                if "args" not in ir and ir.get("op") != "Retrieve":
                    errors.append(f"sample {idx}, IR {ir_idx}: missing 'args' field")
                
                if ir.get("op") == "Encode":
                    payload = ir.get("args", {}).get("payload", {})
                    if not payload.get("text"):
                        errors.append(f"sample {idx}, IR {ir_idx}: Encode missing payload.text")
        
        return errors

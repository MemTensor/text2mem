"""
Stage 2 Generator - IR Schema生成器
将NL指令转换为Text2Mem IR格式
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
    """IR测试样本（Stage 2输出）"""
    id: str
    class_info: Dict[str, str]
    nl: Dict[str, str]
    prerequisites: List[Dict[str, Any]]
    schema_list: List[Dict[str, Any]]
    init_db: Optional[Any]
    notes: str


class Stage2Generator:
    """Stage 2: IR Schema生成器"""
    
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
        
        # 加载prompt模板（支持中英文）
        self.prompt_templates = {
            'zh': self._load_prompt_template("stage2_ir_generation.md"),
            'en': self._load_prompt_template("en_stage2_ir_generation.md"),
        }
        
        # ID计数器
        self.id_counter = 0
    
    def _log(self, message: str, level: str = "INFO", verbose_only: bool = False):
        """简单的日志方法"""
        # 如果是verbose_only消息，可以选择性显示
        if verbose_only:
            # TODO: 添加verbose控制
            pass  # 暂时不显示verbose消息
            return
        
        prefix = {
            "INFO": "ℹ️ ",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }.get(level, "")
        print(f"   {prefix} {message}")
    
    def _load_prompt_template(self, filename: str) -> str:
        """加载Stage 2的prompt模板
        
        Args:
            filename: 模板文件名
            
        Returns:
            模板内容
        """
        prompt_file = self.prompts_dir / filename
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt模板未找到: {prompt_file}")
        
        return prompt_file.read_text(encoding="utf-8")
    
    def generate_single(self, nl_instruction: Dict[str, Any]) -> Optional[IRSample]:
        """
        为单个NL指令生成IR样本
        支持多次重试
        
        Args:
            nl_instruction: Stage 1生成的单个NL指令
        
        Returns:
            IR样本，如果失败则返回None
        """
        max_attempts = 3  # 最多尝试3次
        
        for attempt in range(max_attempts):
            try:
                # 构建prompt
                prompt = self._build_single_prompt(nl_instruction)
                
                # 调用LLM
                response = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.5,  # Stage2使用更低的temperature
                    max_tokens=4000,
                )
                
                # 解析响应
                sample = self._parse_response(response.content, nl_instruction)
                
                if sample:
                    # 验证样本
                    errors = self.validate_samples([sample], None)
                    if not errors:
                        # 成功！
                        if attempt > 0:
                            print(f"      ✅ 第{attempt + 1}次尝试成功")
                        return sample
                    else:
                        # 验证失败，记录并重试
                        if attempt < max_attempts - 1:
                            print(f"      ⚠️  第{attempt + 1}次尝试验证失败: {errors[0]}")
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
                    time.sleep(1)  # 稍微等待一下
                    continue
                else:
                    print(f"      ❌ 所有尝试都失败了")
        
        # 所有尝试都失败
        return None
    
    def _build_single_prompt(self, nl_instruction: Dict[str, Any]) -> str:
        """为单个NL指令构建prompt - 使用模板文件"""
        # 获取基础信息
        classification = nl_instruction.get('classification', {})
        scenario_info = nl_instruction.get('scenario_info', {})
        structure = classification.get('structure', 'single')
        operation = scenario_info.get('operation', 'unknown')
        instruction = nl_instruction.get('instruction', '')
        context = nl_instruction.get('context', '')
        lang = classification.get('lang', 'zh')
        
        # 根据语言选择prompt模板
        prompt_template = self.prompt_templates.get(lang, self.prompt_templates['zh'])
        
        # 使用加载的模板并替换变量
        prompt = prompt_template
        
        # 替换模板中的占位符
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
        """解析LLM响应 - 智能提取和修复JSON"""
        original_content = content
        content = content.strip()
        
        # 步骤1：清理markdown标记和常见包装
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        # 移除常见的说明性文字（中英文）
        patterns = [
            r'^[^{]*?(?:生成|输出|结果|sample|output|result)[^{]*?[:：]\s*',
            r'^[^{]*?(?:以下|following|below)[^{]*?[:：]\s*',
        ]
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        content = content.strip()
        
        # 步骤2：尝试解析JSON
        data = None
        parse_method = None
        
        # 方法1：直接解析（最快）
        try:
            data = json.loads(content)
            parse_method = "direct"
        except json.JSONDecodeError as e:
            # 方法2：提取第一个完整的JSON对象（处理额外内容）
            try:
                from json import JSONDecoder
                decoder = JSONDecoder()
                data, idx = decoder.raw_decode(content)
                parse_method = "raw_decode"
                
                # 检查是否有额外内容
                if idx < len(content.strip()):
                    remaining = content[idx:].strip()
                    if remaining and len(remaining) > 10:
                        self._log(f"      ⚠️  检测到JSON后有额外内容（已忽略）: {remaining[:80]}...", verbose_only=True)
            except (json.JSONDecodeError, ValueError):
                # 方法3：手动查找完整的JSON对象边界
                data = self._extract_json_by_braces(content)
                if data:
                    parse_method = "brace_matching"
        
        # 如果所有方法都失败
        if data is None:
            print(f"      ❌ JSON解析完全失败")
            print(f"      原始内容长度: {len(original_content)} 字符")
            print(f"      前200字符: {original_content[:200]}")
            self._save_failed_response(original_content, nl_instruction, "stage2")
            return None
        
        # 步骤3：验证JSON结构
        required_fields = ["prerequisites", "schema_list"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print(f"      ⚠️  JSON缺少关键字段: {missing_fields}")
            print(f"      实际字段: {list(data.keys())}")
            return None
        
        # 步骤4：构建IRSample
        try:
            self.id_counter += 1
            # 始终使用id_counter生成唯一ID，确保不重复
            # 从classification中提取信息用于ID
            classification = data.get("class", nl_instruction.get("classification", {}))
            
            # 标准化classification字段名（修复LLM可能返回的错误键名）
            if "instruction" in classification and "instruction_type" not in classification:
                classification["instruction_type"] = classification.pop("instruction")
            
            lang = classification.get("lang", "zh")
            instruction_type = classification.get("instruction_type", "direct")
            structure = classification.get("structure", "single")
            
            # 从schema_list中提取操作类型
            schema_list = data.get("schema_list", [])
            op_abbr = "unk"
            if schema_list:
                op = schema_list[0].get("op", "Unknown")
                # 操作缩写映射
                op_map = {
                    "Encode": "enc", "Retrieve": "ret", "Update": "upd",
                    "Delete": "del", "Summarize": "sum", "Label": "lbl",
                    "Promote": "pro", "Demote": "dem", "Expire": "exp",
                    "Lock": "lck", "Merge": "mrg", "Split": "spl",
                }
                op_abbr = op_map.get(op, "unk")
            
            # 生成格式: t2m-{lang}-{type}-{structure}-{op}-{counter}
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
            
            self._log(f"      ✅ 解析成功 (方法: {parse_method})", verbose_only=True)
            return sample
            
        except Exception as e:
            print(f"      ❌ 构建IRSample失败: {e}")
            return None
    
    def _extract_json_by_braces(self, content: str) -> Optional[Dict]:
        """通过括号匹配提取JSON对象并尝试修复"""
        start = content.find('{')
        if start == -1:
            return None
        
        # 首先尝试提取完整的JSON
        json_str = self._extract_balanced_json(content, start)
        if not json_str:
            return None
        
        # 尝试多种修复策略
        for attempt in range(6):
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    # 策略1：移除注释
                    json_str = re.sub(r'//.*', '', json_str)
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                elif attempt == 1:
                    # 策略2：修复常见格式问题（尾随逗号）
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                elif attempt == 2:
                    # 策略3：修复LLM常见错误 - schema_list中缺少关闭括号
                    # 模式: }}],"其他字段" 应该是 }}}],"其他字段"
                    # 这是因为LLM忘记关闭数组中的对象
                    if '}}],"init_db"' in json_str or '}}],"notes"' in json_str:
                        json_str = re.sub(r'(\}\})\],\s*"(init_db|notes|expected)', r'\1}],"\2', json_str)
                        print(f"      🔧 修复schema_list缺少关闭括号")
                elif attempt == 3:
                    # 策略4：尝试补全缺失的括号
                    json_str = self._auto_complete_braces(json_str)
                elif attempt == 4:
                    # 策略5：修复LLM常见错误（如}{应该是},{）
                    json_str = re.sub(r'}\s*{', '},{', json_str)
                else:
                    # 最后一次失败
                    print(f"      ⚠️  所有JSON修复尝试都失败: {e}")
                    if e.pos and e.pos < len(json_str):
                        start_show = max(0, e.pos - 50)
                        end_show = min(len(json_str), e.pos + 50)
                        print(f"      错误位置附近: ...{json_str[start_show:end_show]}...")
                    return None
        
        return None
    
    def _extract_balanced_json(self, content: str, start: int) -> Optional[str]:
        """提取括号平衡的JSON字符串"""
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(content)):
            char = content[i]
            
            # 处理字符串和转义
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            
            # 只在非字符串中计数括号
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                
                # 找到平衡点
                if brace_count == 0 and bracket_count == 0 and i > start:
                    return content[start:i+1]
        
        # 如果没有找到完全平衡的，返回到末尾的内容
        return content[start:]
    
    def _auto_complete_braces(self, json_str: str) -> str:
        """自动补全缺失的括号"""
        # 计算需要补全的括号
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
        
        # 补全缺失的括号
        result = json_str
        if bracket_count > 0:
            result += ']' * bracket_count
            print(f"      🔧 自动补全了 {bracket_count} 个方括号 ]")
        if brace_count > 0:
            result += '}' * brace_count
            print(f"      🔧 自动补全了 {brace_count} 个大括号 }}")
        
        return result
    
    def _save_failed_response(self, content: str, nl_instruction: Dict[str, Any], stage: str):
        """保存解析失败的响应用于调试"""
        try:
            from pathlib import Path
            from datetime import datetime
            
            # 创建失败日志目录
            log_dir = Path("bench/generate/output/failed_responses")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            instruction_id = nl_instruction.get("id", "unknown")
            filename = f"failed_{stage}_{instruction_id}_{timestamp}.txt"
            
            # 保存内容
            log_file = log_dir / filename
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"解析失败的LLM响应 - {stage.upper()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"指令ID: {instruction_id}\n")
                f.write(f"时间: {timestamp}\n")
                f.write(f"内容长度: {len(content)} 字符\n\n")
                f.write("=" * 80 + "\n")
                f.write("原始响应:\n")
                f.write("=" * 80 + "\n")
                f.write(content)
                f.write("\n\n")
                f.write("=" * 80 + "\n")
                f.write("输入指令:\n")
                f.write("=" * 80 + "\n")
                f.write(json.dumps(nl_instruction, ensure_ascii=False, indent=2))
            
            print(f"      💾 已保存失败响应到: {log_file}")
            
        except Exception as e:
            print(f"      ⚠️  保存失败响应时出错: {e}")
    
    def validate_samples(
        self,
        samples: List[IRSample],
        batch: Any,
    ) -> List[str]:
        """验证生成的IR样本"""
        errors = []
        
        for idx, sample in enumerate(samples):
            # 验证基本字段
            if not sample.id:
                errors.append(f"样本{idx}: id为空")
            
            if not sample.schema_list:
                errors.append(f"样本{idx}: schema_list为空")
            
            # 验证schema_list中的IR
            for ir_idx, ir in enumerate(sample.schema_list):
                if "stage" not in ir:
                    errors.append(f"样本{idx}, IR{ir_idx}: 缺少stage字段")
                if "op" not in ir:
                    errors.append(f"样本{idx}, IR{ir_idx}: 缺少op字段")
                if "args" not in ir and ir.get("op") != "Retrieve":
                    errors.append(f"样本{idx}, IR{ir_idx}: 缺少args字段")
                
                # 检查Encode的payload
                if ir.get("op") == "Encode":
                    payload = ir.get("args", {}).get("payload", {})
                    if not payload.get("text"):
                        errors.append(f"样本{idx}, IR{ir_idx}: Encode缺少payload.text")
        
        return errors

"""
Stage 3 Generator - Expected结果生成器
为IR样本添加expected字段（assertions, ranking, triggers）
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from bench.generate.src.llm_client import LLMClient, LLMConfig
from bench.generate.src.plan_loader import GenerationPlan
from bench.generate.src.stage2_generator import IRSample


@dataclass
class CompleteSample:
    """完整的测试样本（Stage 3输出）"""
    id: str
    class_info: Dict[str, str]
    nl: Dict[str, str]
    prerequisites: List[Dict[str, Any]]
    schema_list: List[Dict[str, Any]]
    init_db: Optional[Any]
    expected: Dict[str, Any]
    notes: str


class Stage3Generator:
    """Stage 3: Expected结果生成器"""
    
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
        
        # 加载prompt模板
        self.prompt_template = self._load_prompt_template()
    
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
    
    def _load_prompt_template(self) -> str:
        """加载Stage 3的prompt模板"""
        prompt_file = self.prompts_dir / "stage3_expected_generation.md"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt模板未找到: {prompt_file}")
        
        return prompt_file.read_text(encoding="utf-8")
    
    def generate_single(self, ir_sample: IRSample) -> Optional[CompleteSample]:
        """
        为单个IR样本生成expected字段
        支持多次重试
        
        Args:
            ir_sample: Stage 2生成的IR样本
        
        Returns:
            完整的测试样本，如果失败则返回None
        """
        max_attempts = 3  # 最多尝试3次
        
        for attempt in range(max_attempts):
            try:
                # 构建prompt
                prompt = self._build_single_prompt(ir_sample)
                
                # 调用LLM
                response = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.3,  # Stage3使用更低的temperature，确保一致性
                    max_tokens=3000,
                )
                
                # 解析响应
                sample = self._parse_response(response.content, ir_sample)
                
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
    
    def _build_single_prompt(self, ir_sample: IRSample) -> str:
        """为单个IR样本构建prompt - 使用模板文件"""
        # 构建IR样本的JSON表示（单行JSONL格式）
        ir_json = json.dumps({
            "id": ir_sample.id,
            "class": ir_sample.class_info,
            "nl": ir_sample.nl,
            "prerequisites": ir_sample.prerequisites,
            "schema_list": ir_sample.schema_list,
            "init_db": ir_sample.init_db,
            "notes": ir_sample.notes,
        }, ensure_ascii=False)
        
        # 确定主要操作
        main_op = "unknown"
        if ir_sample.schema_list:
            main_op = ir_sample.schema_list[0].get("op", "unknown")
        
        # 使用加载的模板并替换变量
        prompt = self.prompt_template
        prompt = prompt.replace('{test_samples_jsonl}', ir_json)
        prompt = prompt.replace('{ir_json}', ir_json)
        prompt = prompt.replace('{main_op}', main_op)
        
        return prompt
    
    def _parse_response(self, content: str, ir_sample: IRSample) -> Optional[CompleteSample]:
        """解析LLM响应 - 智能提取和修复JSON"""
        original_content = content
        content = content.strip()
        
        # 步骤1：清理markdown标记和常见包装
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        # 移除常见的说明性文字
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
        
        # 方法1：直接解析
        try:
            data = json.loads(content)
            parse_method = "direct"
        except json.JSONDecodeError as e:
            # 方法2：提取第一个完整的JSON对象
            try:
                from json import JSONDecoder
                decoder = JSONDecoder()
                data, idx = decoder.raw_decode(content)
                parse_method = "raw_decode"
                
                if idx < len(content.strip()):
                    remaining = content[idx:].strip()
                    if remaining and len(remaining) > 10:
                        self._log(f"      ⚠️  检测到JSON后有额外内容（已忽略）: {remaining[:80]}...", verbose_only=True)
            except (json.JSONDecodeError, ValueError):
                # 方法3：手动查找JSON边界
                data = self._extract_json_by_braces(content)
                if data:
                    parse_method = "brace_matching"
        
        # 如果所有方法都失败
        if data is None:
            print(f"      ❌ JSON解析完全失败")
            print(f"      原始内容长度: {len(original_content)} 字符")
            print(f"      前200字符: {original_content[:200]}")
            self._save_failed_response(original_content, ir_sample, "stage3")
            return None
        
        # 步骤3：验证expected字段
        if "expected" not in data:
            print(f"      ⚠️  JSON缺少expected字段")
            print(f"      实际字段: {list(data.keys())}")
            return None
        
        # 步骤4：构建CompleteSample
        try:
            sample = CompleteSample(
                id=data.get("id", ir_sample.id),
                class_info=data.get("class", ir_sample.class_info),
                nl=data.get("nl", ir_sample.nl),
                prerequisites=data.get("prerequisites", ir_sample.prerequisites),
                schema_list=data.get("schema_list", ir_sample.schema_list),
                init_db=data.get("init_db", ir_sample.init_db),
                expected=data.get("expected", {}),
                notes=data.get("notes", ir_sample.notes),
            )
            
            self._log(f"      ✅ 解析成功 (方法: {parse_method})", verbose_only=True)
            return sample
            
        except Exception as e:
            print(f"      ❌ 构建CompleteSample失败: {e}")
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
                    # 策略3：修复LLM常见错误 - expected数组中缺少关闭括号
                    if '}}]' in json_str:
                        # 检查是否需要修复
                        if '"expected":[{' in json_str:
                            json_str = re.sub(r'(\}\})\]\s*$', r'\1}]', json_str)
                            print(f"      🔧 修复expected缺少关闭括号")
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
    
    def _save_failed_response(self, content: str, ir_sample: IRSample, stage: str):
        """保存解析失败的响应用于调试"""
        try:
            from pathlib import Path
            from datetime import datetime
            
            log_dir = Path("bench/generate/output/failed_responses")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            sample_id = ir_sample.id
            filename = f"failed_{stage}_{sample_id}_{timestamp}.txt"
            
            log_file = log_dir / filename
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"解析失败的LLM响应 - {stage.upper()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"样本ID: {sample_id}\n")
                f.write(f"时间: {timestamp}\n")
                f.write(f"内容长度: {len(content)} 字符\n\n")
                f.write("=" * 80 + "\n")
                f.write("原始响应:\n")
                f.write("=" * 80 + "\n")
                f.write(content)
                f.write("\n\n")
                f.write("=" * 80 + "\n")
                f.write("输入IR样本:\n")
                f.write("=" * 80 + "\n")
                f.write(json.dumps({
                    "id": ir_sample.id,
                    "class": ir_sample.class_info,
                    "nl": ir_sample.nl,
                    "prerequisites": ir_sample.prerequisites,
                    "schema_list": ir_sample.schema_list,
                }, ensure_ascii=False, indent=2))
            
            print(f"      💾 已保存失败响应到: {log_file}")
            
        except Exception as e:
            print(f"      ⚠️  保存失败响应时出错: {e}")
    
    def validate_samples(
        self,
        samples: List[CompleteSample],
        batch: Any,
    ) -> List[str]:
        """验证完整样本"""
        errors = []
        
        for idx, sample in enumerate(samples):
            # 验证expected字段存在
            if not sample.expected:
                errors.append(f"样本{idx}: expected字段为空")
                continue
            
            # 验证expected结构
            if "assertions" not in sample.expected:
                errors.append(f"样本{idx}: expected缺少assertions字段")
            
            if "ranking" not in sample.expected:
                errors.append(f"样本{idx}: expected缺少ranking字段")
            
            if "triggers" not in sample.expected:
                errors.append(f"样本{idx}: expected缺少triggers字段")
            
            # 验证assertions格式
            assertions = sample.expected.get("assertions", [])
            if not isinstance(assertions, list):
                errors.append(f"样本{idx}: assertions应该是数组")
            
            for ass_idx, assertion in enumerate(assertions):
                if not isinstance(assertion, dict):
                    errors.append(f"样本{idx}, assertion{ass_idx}: 应该是对象")
                    continue
                
                required = ["name", "select", "expect"]
                for field in required:
                    if field not in assertion:
                        errors.append(f"样本{idx}, assertion{ass_idx}: 缺少{field}字段")
        
        return errors

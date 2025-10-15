#!/usr/bin/env python3
"""
清洗 Benchmark 数据

过滤规则:
1. 删除所有包含 'unknown' 的样本
2. 指令类型：只保留 'direct' 和 'indirect'
3. 结构：只保留 'single' 和 'workflow'
4. 操作：只保留 12 种核心操作

用法:
    python clean_benchmark.py
    python clean_benchmark.py --input my_input.jsonl --output my_output.jsonl
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Set

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkCleaner:
    """Benchmark 数据清洗器"""
    
    # 允许的值
    ALLOWED_INSTRUCTION_TYPES = {'direct', 'indirect'}
    ALLOWED_STRUCTURES = {'single', 'workflow'}
    ALLOWED_OPERATIONS = {
        'Encode',      # 编码/保存
        'Retrieve',    # 检索
        'Update',      # 更新
        'Delete',      # 删除
        'Summarize',   # 总结
        'Label',       # 标签
        'Promote',     # 提升
        'Demote',      # 降级
        'Expire',      # 过期
        'Lock',        # 锁定
        'Merge',       # 合并
        'Split',       # 拆分
    }
    
    def __init__(self):
        self.samples = []
        self.stats = {
            'total': 0,
            'filtered': 0,
            'reasons': {
                'unknown_in_fields': 0,
                'invalid_instruction_type': 0,
                'invalid_structure': 0,
                'invalid_operation': 0,
            }
        }
    
    def load_samples(self, input_file: Path) -> int:
        """加载样本"""
        logger.info(f"📂 加载样本: {input_file}")
        
        count = 0
        with input_file.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    self.samples.append(sample)
                    count += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️  行 {line_num} 解析失败: {e}")
        
        self.stats['total'] = count
        logger.info(f"✅ 加载 {count} 个样本")
        return count
    
    def check_sample(self, sample: Dict[str, Any]) -> tuple[bool, str]:
        """检查样本是否符合要求
        
        Returns:
            (是否保留, 原因)
        """
        class_info = sample.get('class', {})
        
        # 提取字段
        lang = class_info.get('lang', 'unknown')
        instruction_type = class_info.get('instruction_type', 'unknown')
        structure = class_info.get('structure', 'unknown')
        
        # 提取操作
        schema_list = sample.get('schema_list', [])
        if not schema_list:
            return False, 'invalid_operation'
        
        operation = schema_list[0].get('op', 'unknown')
        
        # 检查 1: 是否包含 unknown
        if 'unknown' in [lang, instruction_type, structure, operation]:
            return False, 'unknown_in_fields'
        
        # 检查 2: 指令类型
        if instruction_type not in self.ALLOWED_INSTRUCTION_TYPES:
            return False, 'invalid_instruction_type'
        
        # 检查 3: 结构
        if structure not in self.ALLOWED_STRUCTURES:
            return False, 'invalid_structure'
        
        # 检查 4: 操作
        if operation not in self.ALLOWED_OPERATIONS:
            return False, 'invalid_operation'
        
        return True, 'valid'
    
    def clean(self):
        """清洗数据"""
        logger.info("🧹 开始清洗数据...")
        
        cleaned_samples = []
        
        for sample in self.samples:
            keep, reason = self.check_sample(sample)
            
            if keep:
                cleaned_samples.append(sample)
            else:
                self.stats['filtered'] += 1
                self.stats['reasons'][reason] += 1
        
        self.samples = cleaned_samples
        
        logger.info(f"✅ 清洗完成")
        logger.info(f"   保留: {len(self.samples)} 个样本")
        logger.info(f"   过滤: {self.stats['filtered']} 个样本")
    
    def rebuild_ids(self):
        """重新分配 ID（清洗后）"""
        logger.info("🔧 重新分配 ID...")
        
        # 按分类分组
        groups = {}
        for sample in self.samples:
            class_info = sample.get('class', {})
            
            # 保存原始 ID
            original_id = sample.get('id', '')
            
            # 提取分类信息
            lang = class_info.get('lang', 'unknown')
            instruction_type = class_info.get('instruction_type', 'unknown')
            structure = class_info.get('structure', 'unknown')
            
            # 提取操作类型
            schema_list = sample.get('schema_list', [])
            if schema_list:
                op = schema_list[0].get('op', 'unknown').lower()
            else:
                op = 'unknown'
            
            # 构建分组键
            group_key = f"{lang}-{instruction_type}-{structure}-{op}"
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(sample)
        
        logger.info(f"   发现 {len(groups)} 个分组")
        
        # 为每个分组重新编号
        new_samples = []
        
        for group_key, samples_list in sorted(groups.items()):
            for idx, sample in enumerate(samples_list, 1):
                # 生成新 ID
                new_id = f"t2m-{group_key}-{idx:03d}"
                
                # 保存旧的新 ID 到 _previous_id
                if sample.get('id') != sample.get('_original_id'):
                    sample['_previous_id'] = sample.get('id')
                
                # 更新 ID
                sample['id'] = new_id
                
                new_samples.append(sample)
            
            logger.info(f"   {group_key}: {len(samples_list)} 个样本")
        
        self.samples = new_samples
        logger.info(f"✅ 重新分配了 {len(self.samples)} 个样本的 ID")
    
    def save(self, output_file: Path):
        """保存清洗后的数据"""
        logger.info(f"💾 保存到: {output_file}")
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with output_file.open('w', encoding='utf-8') as f:
            for sample in self.samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ 已保存 {len(self.samples)} 个样本")
    
    def print_stats(self):
        """打印统计信息"""
        from collections import Counter
        
        print("\n" + "="*60)
        print("📊 清洗统计")
        print("="*60)
        print(f"原始样本数: {self.stats['total']}")
        print(f"保留样本数: {len(self.samples)}")
        print(f"过滤样本数: {self.stats['filtered']}")
        print(f"保留比例: {len(self.samples)/self.stats['total']*100:.1f}%")
        
        print(f"\n过滤原因:")
        for reason, count in self.stats['reasons'].items():
            if count > 0:
                print(f"  {reason}: {count} 个")
        
        # 统计保留的样本
        langs = Counter()
        types = Counter()
        structures = Counter()
        operations = Counter()
        
        for sample in self.samples:
            class_info = sample.get('class', {})
            langs[class_info.get('lang', 'unknown')] += 1
            types[class_info.get('instruction_type', 'unknown')] += 1
            structures[class_info.get('structure', 'unknown')] += 1
            
            schema_list = sample.get('schema_list', [])
            if schema_list:
                op = schema_list[0].get('op', 'unknown')
                operations[op] += 1
        
        print(f"\n保留的样本统计:")
        print(f"  语言: {dict(langs)}")
        print(f"  指令类型: {dict(types)}")
        print(f"  结构: {dict(structures)}")
        print(f"  操作: {dict(operations)}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="清洗 Benchmark 数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
过滤规则:
  1. 删除所有包含 'unknown' 的样本
  2. 指令类型：只保留 'direct' 和 'indirect'
  3. 结构：只保留 'single' 和 'workflow'
  4. 操作：只保留 12 种核心操作
     (Encode, Retrieve, Update, Delete, Summarize, Label,
      Promote, Demote, Expire, Lock, Merge, Split)

示例:
  # 基础用法
  python clean_benchmark.py
  
  # 指定输入输出
  python clean_benchmark.py --input my_input.jsonl --output my_output.jsonl
        """
    )
    
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('bench/data/test_data/test_data.jsonl'),
        help='输入文件路径（默认：bench/data/test_data/test_data.jsonl）'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('bench/data/benchmark/v1/benchmark.jsonl'),
        help='输出文件路径（默认：bench/data/benchmark/v1/benchmark.jsonl）'
    )
    parser.add_argument(
        '--no-rebuild-id',
        action='store_true',
        help='不重新分配 ID'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not args.input.exists():
        logger.error(f"❌ 输入文件不存在: {args.input}")
        return 1
    
    # 创建清洗器
    cleaner = BenchmarkCleaner()
    
    # 1. 加载
    cleaner.load_samples(args.input)
    
    # 2. 清洗
    cleaner.clean()
    
    # 3. 重新分配 ID（可选）
    if not args.no_rebuild_id:
        cleaner.rebuild_ids()
    
    # 4. 保存
    cleaner.save(args.output)
    
    # 5. 统计
    cleaner.print_stats()
    
    print(f"\n📄 输出文件: {args.output}")
    print(f"✅ Benchmark 清洗完成！")
    
    return 0


if __name__ == '__main__':
    exit(main())

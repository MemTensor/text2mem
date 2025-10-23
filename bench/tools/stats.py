#!/usr/bin/env python3
"""
Benchmark数据统计分析工具

功能：
1. 统计样本分布（语言、场景、操作、指令类型、结构等）
2. 分析数据质量指标
3. 生成统计报告
4. 检测异常样本

用法：
    # 统计最新run
    python -m bench.tools.stats --run latest
    
    # 统计指定run
    python -m bench.tools.stats --run 20251015_131147
    
    # 统计指定文件（向后兼容）
    python -m bench.tools.stats --input stage3.jsonl
    
    # 生成详细报告
    python -m bench.tools.stats --run latest --verbose
"""

import argparse
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from bench.tools.run_manager import RunManager

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkStats:
    """Benchmark数据统计分析器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.samples: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}
        
    def load_samples(self, input_file: Path) -> int:
        """加载样本数据"""
        logger.info(f"📂 加载样本: {input_file}")
        
        if not input_file.exists():
            raise FileNotFoundError(f"文件不存在: {input_file}")
        
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
        
        logger.info(f"✅ 加载 {count} 个样本")
        return count
    
    def analyze(self) -> Dict[str, Any]:
        """分析样本数据"""
        logger.info("📊 开始统计分析...")
        
        # 基本统计
        total = len(self.samples)
        
        # 分类统计
        langs = Counter()
        operations = Counter()
        instruction_types = Counter()
        structures = Counter()
        
        # 组合统计
        lang_op_combos = Counter()
        
        # 质量指标
        has_nl = 0
        has_schema = 0
        has_expected = 0
        has_prerequisites = 0
        
        # 异常检测
        unknown_fields = []
        missing_fields = []
        
        # 操作分布统计
        op_details = defaultdict(lambda: {
            'count': 0,
            'langs': Counter(),
            'instruction_types': Counter(),
            'structures': Counter(),
        })
        
        for idx, sample in enumerate(self.samples, 1):
            sample_id = sample.get('id', f'sample-{idx}')
            class_info = sample.get('class', {})
            
            # 提取分类信息
            lang = class_info.get('lang', 'unknown')
            instruction_type = class_info.get('instruction_type', 'unknown')
            structure = class_info.get('structure', 'unknown')
            
            # 统计分类
            langs[lang] += 1
            instruction_types[instruction_type] += 1
            structures[structure] += 1
            
            # 检测unknown
            if 'unknown' in [lang, instruction_type, structure]:
                unknown_fields.append({
                    'sample_id': sample_id,
                    'fields': {
                        'lang': lang,
                        'instruction_type': instruction_type,
                        'structure': structure,
                    }
                })
            
            # 提取操作
            schema_list = sample.get('schema_list', [])
            if schema_list:
                # 主操作（第一个）
                main_op = schema_list[0].get('op', 'unknown')
                operations[main_op] += 1
                
                # 组合统计
                lang_op_combos[f"{lang}-{main_op}"] += 1
                
                # 操作详细统计
                op_details[main_op]['count'] += 1
                op_details[main_op]['langs'][lang] += 1
                op_details[main_op]['instruction_types'][instruction_type] += 1
                op_details[main_op]['structures'][structure] += 1
                
                # 工作流中的所有操作
                if len(schema_list) > 1:
                    workflow_ops = [s.get('op') for s in schema_list]
                    # 记录工作流模式
                    # operations[f"workflow:{'+'.join(workflow_ops)}"] += 1
            
            # 质量检查
            if sample.get('nl'):
                has_nl += 1
            if schema_list:
                has_schema += 1
            if sample.get('expected'):
                has_expected += 1
            if sample.get('prerequisites'):
                has_prerequisites += 1
            
            # 检查必填字段
            required_fields = ['id', 'class', 'nl', 'schema_list']
            for field in required_fields:
                if field not in sample or not sample[field]:
                    missing_fields.append({
                        'sample_id': sample_id,
                        'missing_field': field
                    })
        
        # 构建统计结果
        self.stats = {
            'metadata': {
                'analyzed_at': datetime.now().isoformat(),
                'total_samples': total,
        # 构建统计结果
        self.stats = {
            'metadata': {
                'analyzed_at': datetime.now().isoformat(),
                'total_samples': total,
            },
            'distribution': {
                'languages': dict(langs.most_common()),
                'operations': dict(operations.most_common()),
                'instruction_types': dict(instruction_types.most_common()),
                'structures': dict(structures.most_common()),
            },
            'combinations': {
                'lang_operation': dict(lang_op_combos.most_common(20)),  # Top 20
            },
            'operation_details': {
                op: {
                    'count': details['count'],
                    'percentage': details['count'] / total * 100,
                    'langs': dict(details['langs'].most_common()),
                    'instruction_types': dict(details['instruction_types'].most_common()),
                    'structures': dict(details['structures'].most_common()),
                }
                for op, details in sorted(op_details.items(), key=lambda x: x[1]['count'], reverse=True)
            },
            'quality': {
                'has_nl': has_nl,
                'has_nl_percentage': has_nl / total * 100 if total > 0 else 0,
                'has_schema': has_schema,
                'has_schema_percentage': has_schema / total * 100 if total > 0 else 0,
                'has_expected': has_expected,
                'has_expected_percentage': has_expected / total * 100 if total > 0 else 0,
                'has_prerequisites': has_prerequisites,
                'has_prerequisites_percentage': has_prerequisites / total * 100 if total > 0 else 0,
            },
            'issues': {
                'unknown_fields_count': len(unknown_fields),
                'unknown_fields': unknown_fields[:10] if not self.verbose else unknown_fields,  # 只显示前10个
                'missing_fields_count': len(missing_fields),
                'missing_fields': missing_fields[:10] if not self.verbose else missing_fields,
            }
        }
        
        logger.info("✅ 统计分析完成")
        return self.stats
    
    def print_report(self):
        """打印统计报告"""
        if not self.stats:
            logger.error("❌ 请先运行 analyze()")
            return
        
        stats = self.stats
        
        print("\n" + "="*80)
        print("📊 Benchmark 数据统计报告")
        print("="*80)
        
        # 基本信息
        print(f"\n📝 基本信息:")
        print(f"  总样本数: {stats['metadata']['total_samples']}")
        print(f"  分析时间: {stats['metadata']['analyzed_at']}")
        
        # 分布统计
        print(f"\n📈 分布统计:")
        
        print(f"\n  语言分布:")
        for lang, count in stats['distribution']['languages'].items():
            pct = count / stats['metadata']['total_samples'] * 100
            print(f"    {lang}: {count} ({pct:.1f}%)")
        
        print(f"\n  操作分布:")
        for op, count in stats['distribution']['operations'].items():
            pct = count / stats['metadata']['total_samples'] * 100
            print(f"    {op}: {count} ({pct:.1f}%)")
        
        print(f"\n  指令类型分布:")
        for itype, count in stats['distribution']['instruction_types'].items():
            pct = count / stats['metadata']['total_samples'] * 100
            print(f"    {itype}: {count} ({pct:.1f}%)")
        
        print(f"\n  结构分布:")
        for struct, count in stats['distribution']['structures'].items():
            pct = count / stats['metadata']['total_samples'] * 100
            print(f"    {struct}: {count} ({pct:.1f}%)")
        
        # 质量指标
        print(f"\n✅ 质量指标:")
        quality = stats['quality']
        print(f"  完整NL: {quality['has_nl']} ({quality['has_nl_percentage']:.1f}%)")
        print(f"  完整Schema: {quality['has_schema']} ({quality['has_schema_percentage']:.1f}%)")
        print(f"  完整Expected: {quality['has_expected']} ({quality['has_expected_percentage']:.1f}%)")
        print(f"  有Prerequisites: {quality['has_prerequisites']} ({quality['has_prerequisites_percentage']:.1f}%)")
        
        # 问题检测
        print(f"\n⚠️  问题检测:")
        issues = stats['issues']
        print(f"  包含unknown的样本: {issues['unknown_fields_count']}")
        print(f"  缺少必填字段的样本: {issues['missing_fields_count']}")
        
        if issues['unknown_fields_count'] > 0 and self.verbose:
            print(f"\n  包含unknown的样本详情:")
            for item in issues['unknown_fields'][:5]:  # 只显示前5个
                print(f"    {item['sample_id']}: {item['fields']}")
        
        if issues['missing_fields_count'] > 0 and self.verbose:
            print(f"\n  缺少字段的样本详情:")
            for item in issues['missing_fields'][:5]:
                print(f"    {item['sample_id']}: missing {item['missing_field']}")
        
        # Top组合
        print(f"\n🔝 Top 10 语言-操作组合:")
        for combo, count in list(stats['combinations']['lang_operation'].items())[:10]:
            pct = count / stats['metadata']['total_samples'] * 100
            print(f"    {combo}: {count} ({pct:.1f}%)")
        
        print("\n" + "="*80)
    
    def save_report(self, output_file: Path):
        """保存统计报告到JSON文件"""
        if not self.stats:
            logger.error("❌ 请先运行 analyze()")
            return
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 统计报告已保存: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Benchmark数据统计分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 统计最新run
  python -m bench.tools.stats --run latest
  
  # 统计指定run
  python -m bench.tools.stats --run 20251015_131147
  
  # 统计指定文件（向后兼容）
  python -m bench.tools.stats --input stage3.jsonl
  
  # 生成详细报告并保存
  python -m bench.tools.stats --run latest --verbose
        """
    )
    
    parser.add_argument(
        '--run', '-r',
        help='Run ID (如 "20251015_131147" 或 "latest")'
    )
    parser.add_argument(
        '--input', '-i',
        type=Path,
        help='输入文件路径（向后兼容，直接指定文件）'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='输出统计报告文件路径（JSON格式），默认保存到run目录'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细信息'
    )
    
    args = parser.parse_args()
    
    # 确定输入文件
    if args.run:
        # 使用run ID
        run_manager = RunManager()
        try:
            input_file = run_manager.get_stage_file(args.run, 3)
            if not input_file.exists():
                logger.error(f"❌ Run {args.run} 没有stage3数据")
                logger.info(f"   文件不存在: {input_file}")
                return 1
            logger.info(f"📂 使用run: {args.run}")
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return 1
    elif args.input:
        # 直接指定文件（向后兼容）
        input_file = args.input
    else:
        # 默认使用latest
        run_manager = RunManager()
        latest_run = run_manager.get_latest_run()
        if not latest_run:
            logger.error("❌ 没有找到任何run")
            logger.info("💡 提示：请先运行生成工具")
            logger.info("   python bench/generate/generate.py")
            return 1
        
        try:
            input_file = run_manager.get_stage_file('latest', 3)
            logger.info(f"🔍 自动使用最新run: {latest_run}")
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return 1
    
    # 检查输入文件
    if not input_file.exists():
        logger.error(f"❌ 输入文件不存在: {input_file}")
        return 1
    
    # 创建统计器
    analyzer = BenchmarkStats(verbose=args.verbose)
    
    try:
        # 加载样本
        analyzer.load_samples(input_file)
        
        # 分析
        analyzer.analyze()
        
        # 打印报告
        analyzer.print_report()
        
        # 保存报告
        if args.output:
            analyzer.save_report(args.output)
        else:
            # 默认保存到输入文件同目录
            default_output = input_file.parent / 'stats.json'
            analyzer.save_report(default_output)
        
        print(f"\n✅ 统计完成！")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 统计失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

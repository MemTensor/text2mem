#!/usr/bin/env python3
"""
Benchmarkdata统计分析工具

Features:
1. 统计sample分布（语言、场景、操作、指令type、结构等）
2. 分析data质量指标
3. generate统计report
4. 检测异常sample

Usage:
    # 统计latestrun
    python -m bench.tools.stats --run latest
    
    # 统计specifiedrun
    python -m bench.tools.stats --run 20251015_131147
    
    # 统计specifiedfile（向后兼容）
    python -m bench.tools.stats --input stage3.jsonl
    
    # generate详细report
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
    """Benchmarkdata统计分析器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.samples: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}
        
    def load_samples(self, input_file: Path) -> int:
        """loadsample count据"""
        logger.info(f"📂 loadsample: {input_file}")
        
        if not input_file.exists():
            raise FileNotFoundError(f"filedoes not exist: {input_file}")
        
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
                    logger.warning(f"⚠️  行 {line_num} 解析failed: {e}")
        
        logger.info(f"✅ load {count} 个sample")
        return count
    
    def analyze(self) -> Dict[str, Any]:
        """分析sample count据"""
        logger.info("📊 start统计分析...")
        
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
                
                # 工作流中的all操作
                if len(schema_list) > 1:
                    workflow_ops = [s.get('op') for s in schema_list]
                    # record工作流mode
                    # operations[f"workflow:{'+'.join(workflow_ops)}"] += 1
            
            # 质量check
            if sample.get('nl'):
                has_nl += 1
            if schema_list:
                has_schema += 1
            if sample.get('expected'):
                has_expected += 1
            if sample.get('prerequisites'):
                has_prerequisites += 1
            
            # check必填字段
            required_fields = ['id', 'class', 'nl', 'schema_list']
            for field in required_fields:
                if field not in sample or not sample[field]:
                    missing_fields.append({
                        'sample_id': sample_id,
                        'missing_field': field
                    })
        
        # Build statistics result
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
        
        logger.info("✅ 统计分析complete")
        return self.stats
    
    def print_report(self):
        """打印统计report"""
        if not self.stats:
            logger.error("❌ 请先run analyze()")
            return
        
        stats = self.stats
        
        print("\n" + "="*80)
        print("📊 Benchmark data统计report")
        print("="*80)
        
        # 基本信息
        print(f"\n📝 基本信息:")
        print(f"  总sample count: {stats['metadata']['total_samples']}")
        print(f"  分析time: {stats['metadata']['analyzed_at']}")
        
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
        
        print(f"\n  指令type分布:")
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
        print(f"  includeunknown的sample: {issues['unknown_fields_count']}")
        print(f"  缺少必填字段的sample: {issues['missing_fields_count']}")
        
        if issues['unknown_fields_count'] > 0 and self.verbose:
            print(f"\n  includeunknown的sample详情:")
            for item in issues['unknown_fields'][:5]:  # 只显示前5个
                print(f"    {item['sample_id']}: {item['fields']}")
        
        if issues['missing_fields_count'] > 0 and self.verbose:
            print(f"\n  缺少字段的sample详情:")
            for item in issues['missing_fields'][:5]:
                print(f"    {item['sample_id']}: missing {item['missing_field']}")
        
        # Top组合
        print(f"\n🔝 Top 10 语言-操作组合:")
        for combo, count in list(stats['combinations']['lang_operation'].items())[:10]:
            pct = count / stats['metadata']['total_samples'] * 100
            print(f"    {combo}: {count} ({pct:.1f}%)")
        
        print("\n" + "="*80)
    
    def save_report(self, output_file: Path):
        """save统计reporttoJSONfile"""
        if not self.stats:
            logger.error("❌ 请先run analyze()")
            return
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 统计reportalreadysave: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Benchmarkdata统计分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
example:
  # 统计latestrun
  python -m bench.tools.stats --run latest
  
  # 统计specifiedrun
  python -m bench.tools.stats --run 20251015_131147
  
  # 统计specifiedfile（向后兼容）
  python -m bench.tools.stats --input stage3.jsonl
  
  # generate详细report并save
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
        help='输入filepath（向后兼容，直接specifiedfile）'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='输出统计reportfilepath（JSONformat），defaultsavetorundirectory'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细信息'
    )
    
    args = parser.parse_args()
    
    # 确定输入file
    if args.run:
        # userun ID
        run_manager = RunManager()
        try:
            input_file = run_manager.get_stage_file(args.run, 3)
            if not input_file.exists():
                logger.error(f"❌ Run {args.run} 没有stage3data")
                logger.info(f"   filedoes not exist: {input_file}")
                return 1
            logger.info(f"📂 userun: {args.run}")
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return 1
    elif args.input:
        # 直接specifiedfile（向后兼容）
        input_file = args.input
    else:
        # defaultuselatest
        run_manager = RunManager()
        latest_run = run_manager.get_latest_run()
        if not latest_run:
            logger.error("❌ 没有found任何run")
            logger.info("💡 提示：请先rungenerate工具")
            logger.info("   python bench/generate/generate.py")
            return 1
        
        try:
            input_file = run_manager.get_stage_file('latest', 3)
            logger.info(f"🔍 自动uselatestrun: {latest_run}")
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return 1
    
    # check输入file
    if not input_file.exists():
        logger.error(f"❌ 输入filedoes not exist: {input_file}")
        return 1
    
    # create统计器
    analyzer = BenchmarkStats(verbose=args.verbose)
    
    try:
        # loadsample
        analyzer.load_samples(input_file)
        
        # 分析
        analyzer.analyze()
        
        # 打印report
        analyzer.print_report()
        
        # savereport
        if args.output:
            analyzer.save_report(args.output)
        else:
            # defaultsaveto输入file同directory
            default_output = input_file.parent / 'stats.json'
            analyzer.save_report(default_output)
        
        print(f"\n✅ 统计complete！")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 统计failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

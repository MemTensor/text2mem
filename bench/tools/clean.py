#!/usr/bin/env python3
"""
数据清洗工具

功能：
1. 从stage3和测试结果中筛选样本
2. 应用过滤规则
3. 生成清洗后的数据

用法：
    # 清洗最新run
    python -m bench.tools.clean --run latest
    
    # 清洗指定run
    python -m bench.tools.clean --run 20251015_131147
    
    # 不过滤unknown
    python -m bench.tools.clean --run latest --no-filter-unknown
"""

import argparse
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from bench.tools.run_manager import RunManager

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗器"""
    
    # 默认过滤规则
    ALLOWED_INSTRUCTION_TYPES = {'direct', 'indirect'}
    ALLOWED_STRUCTURES = {'single', 'workflow'}
    ALLOWED_OPERATIONS = {
        'Encode', 'Retrieve', 'Update', 'Delete', 'Summarize', 'Label',
        'Promote', 'Demote', 'Expire', 'Lock', 'Merge', 'Split',
    }
    
    def __init__(
        self,
        run_id: str,
        filter_unknown: bool = True,
        filter_failed: bool = True,
    ):
        """
        Args:
            run_id: Run ID
            filter_unknown: 是否过滤包含unknown的样本
            filter_failed: 是否过滤测试失败的样本
        """
        self.run_id = run_id
        self.filter_unknown = filter_unknown
        self.filter_failed = filter_failed
        
        self.run_manager = RunManager()
        self.run_dir = self.run_manager.get_run_dir(run_id)
        self.cleaned_dir = self.run_manager.get_cleaned_dir(run_id)
        
        self.samples: List[Dict[str, Any]] = []
        self.passed_sample_ids: Set[str] = set()
        
        self.stats = {
            'total_loaded': 0,
            'total_passed_tests': 0,
            'total_filtered': 0,
            'total_final': 0,
            'filter_reasons': {
                'failed_test': 0,
                'unknown_fields': 0,
                'invalid_instruction_type': 0,
                'invalid_structure': 0,
                'invalid_operation': 0,
            }
        }
        
        logger.info(f"📂 Run目录: {self.run_dir}")
        logger.info(f"📂 清洗输出: {self.cleaned_dir}")
    
    def load_test_results(self):
        """加载测试结果"""
        if not self.filter_failed:
            logger.info("⚠️  不过滤测试失败的样本")
            return
        
        has_tests = self.run_manager.has_tests(self.run_id)
        if not has_tests:
            logger.warning("⚠️  没有测试结果，将不过滤失败样本")
            self.filter_failed = False
            return
        
        tests_dir = self.run_manager.get_tests_dir(self.run_id)
        
        # 优先使用passed.jsonl，如果不存在则使用details.jsonl
        passed_file = tests_dir / 'passed.jsonl'
        details_file = tests_dir / 'details.jsonl'
        
        passed_count = 0
        if passed_file.exists():
            logger.info(f"📂 加载测试结果: {passed_file}")
            with passed_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    result = json.loads(line)
                    self.passed_sample_ids.add(result['sample_id'])
                    passed_count += 1
        elif details_file.exists():
            logger.info(f"📂 从详细结果中加载通过的样本: {details_file}")
            with details_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    result = json.loads(line)
                    # 只添加passed=True的样本
                    if result.get('passed', False):
                        self.passed_sample_ids.add(result['sample_id'])
                        passed_count += 1
        else:
            logger.warning(f"⚠️  未找到测试结果文件")
            self.filter_failed = False
            return
        
        # 如果有重复ID，输出警告
        unique_ids = len(self.passed_sample_ids)
        if passed_count > unique_ids:
            logger.warning(f"⚠️  发现 {passed_count - unique_ids} 个重复的sample_id在测试结果中")
            logger.warning(f"   这可能是因为生成的数据有重复ID，建议检查生成逻辑")
        
        logger.info(f"✅ 加载 {unique_ids} 个唯一的通过测试的样本ID (总计 {passed_count} 条通过记录)")
        self.stats['total_passed_tests'] = unique_ids
        self.stats['total_passed_records'] = passed_count
    
    def load_samples(self):
        """加载原始样本数据"""
        # 获取来源raw
        raw_id = self.run_manager.get_source_raw(self.run_id)
        if not raw_id:
            raise FileNotFoundError(f"无法确定run {self.run_id} 的来源raw")
        
        stage3_file = self.run_manager.get_stage_file_from_raw(raw_id, 3)
        
        if not stage3_file.exists():
            raise FileNotFoundError(f"Stage3文件不存在: {stage3_file}")
        
        logger.info(f"📂 加载样本数据: {stage3_file}")
        
        count = 0
        with stage3_file.open('r', encoding='utf-8') as f:
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
        self.stats['total_loaded'] = count
    
    def filter_samples(self) -> List[Dict[str, Any]]:
        """过滤样本"""
        logger.info("🧹 开始过滤样本...")
        logger.info(f"   filter_failed={self.filter_failed}, passed_ids count={len(self.passed_sample_ids)}")
        
        filtered_samples = []
        
        for sample in self.samples:
            sample_id = sample.get('id', '')
            class_info = sample.get('class', {})
            
            # 规则1: 过滤测试失败的样本
            if self.filter_failed and sample_id not in self.passed_sample_ids:
                self.stats['filter_reasons']['failed_test'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 提取字段
            lang = class_info.get('lang', 'unknown')
            instruction_type = class_info.get('instruction_type', 'unknown')
            structure = class_info.get('structure', 'unknown')
            
            # 提取操作
            schema_list = sample.get('schema_list', [])
            if not schema_list:
                self.stats['filter_reasons']['invalid_operation'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            operation = schema_list[0].get('op', 'unknown')
            
            # 规则2: 过滤包含unknown的样本
            if self.filter_unknown and 'unknown' in [lang, instruction_type, structure, operation]:
                self.stats['filter_reasons']['unknown_fields'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 规则3: 检查指令类型
            if instruction_type not in self.ALLOWED_INSTRUCTION_TYPES:
                self.stats['filter_reasons']['invalid_instruction_type'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 规则4: 检查结构
            if structure not in self.ALLOWED_STRUCTURES:
                self.stats['filter_reasons']['invalid_structure'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 规则5: 检查操作
            if operation not in self.ALLOWED_OPERATIONS:
                self.stats['filter_reasons']['invalid_operation'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 通过所有过滤
            filtered_samples.append(sample)
        
        self.stats['total_final'] = len(filtered_samples)
        logger.info(f"✅ 过滤完成: {len(filtered_samples)} 个样本保留")
        logger.info(f"   过滤掉: {self.stats['total_filtered']} 个样本")
        
        return filtered_samples
    
    def save_cleaned_data(self, samples: List[Dict[str, Any]]):
        """保存清洗后的数据"""
        logger.info("💾 保存清洗后的数据...")
        
        # 1. 保存清洗后的样本
        cleaned_file = self.cleaned_dir / 'cleaned.jsonl'
        with cleaned_file.open('w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        logger.info(f"  ✅ 清洗数据: {cleaned_file}")
        
        # 2. 生成元数据
        # 获取来源raw
        raw_id = self.run_manager.get_source_raw(self.run_id)
        
        metadata = {
            'run_id': self.run_id,
            'created_at': datetime.now().isoformat(),
            'source_raw': raw_id,
            'source_stage3': str(self.run_manager.get_stage_file_from_raw(raw_id, 3)) if raw_id else None,
            'total_samples': len(samples),
            'filtering': {
                'filter_unknown': self.filter_unknown,
                'filter_failed': self.filter_failed,
            },
            'stats': self.stats,
        }
        
        metadata_file = self.cleaned_dir / 'metadata.json'
        with metadata_file.open('w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 元数据: {metadata_file}")
        
        # 3. 生成统计信息
        stats = self._generate_stats(samples)
        stats_file = self.cleaned_dir / 'stats.json'
        with stats_file.open('w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 统计信息: {stats_file}")
        
        # 4. 生成过滤报告
        filter_report = {
            'created_at': datetime.now().isoformat(),
            'total_loaded': self.stats['total_loaded'],
            'total_passed_tests': self.stats['total_passed_tests'],
            'total_passed_records': self.stats.get('total_passed_records', self.stats['total_passed_tests']),
            'total_filtered': self.stats['total_filtered'],
            'total_final': self.stats['total_final'],
            'retention_rate': self.stats['total_final'] / self.stats['total_loaded'] * 100 if self.stats['total_loaded'] > 0 else 0,
            'filter_reasons': self.stats['filter_reasons'],
        }
        
        report_file = self.cleaned_dir / 'filter_report.json'
        with report_file.open('w', encoding='utf-8') as f:
            json.dump(filter_report, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 过滤报告: {report_file}")
        
        logger.info(f"💾 所有文件已保存到: {self.cleaned_dir}")
    
    def _generate_stats(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成统计信息"""
        langs = Counter()
        operations = Counter()
        instruction_types = Counter()
        structures = Counter()
        
        for sample in samples:
            class_info = sample.get('class', {})
            
            langs[class_info.get('lang', 'unknown')] += 1
            instruction_types[class_info.get('instruction_type', 'unknown')] += 1
            structures[class_info.get('structure', 'unknown')] += 1
            
            schema_list = sample.get('schema_list', [])
            if schema_list:
                operations[schema_list[0].get('op', 'unknown')] += 1
        
        return {
            'total': len(samples),
            'distribution': {
                'languages': dict(langs.most_common()),
                'operations': dict(operations.most_common()),
                'instruction_types': dict(instruction_types.most_common()),
                'structures': dict(structures.most_common()),
            }
        }
    
    def print_summary(self):
        """打印清洗摘要"""
        print("\n" + "="*80)
        print("📊 清洗摘要")
        print("="*80)
        
        print(f"\n处理统计:")
        print(f"  加载样本数: {self.stats['total_loaded']}")
        if self.stats['total_passed_tests'] > 0:
            print(f"  通过测试: {self.stats['total_passed_tests']}")
        print(f"  过滤样本数: {self.stats['total_filtered']}")
        print(f"  最终样本数: {self.stats['total_final']}")
        print(f"  保留比例: {self.stats['total_final']/self.stats['total_loaded']*100:.1f}%")
        
        if self.stats['total_filtered'] > 0:
            print(f"\n过滤原因:")
            for reason, count in self.stats['filter_reasons'].items():
                if count > 0:
                    print(f"  {reason}: {count} 个")
        
        print("\n" + "="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据清洗工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
过滤规则:
  1. 过滤测试失败的样本（如果有测试结果）
  2. 过滤包含'unknown'的样本
  3. 只保留'direct'和'indirect'指令类型
  4. 只保留'single'和'workflow'结构
  5. 只保留12种核心操作

示例:
  # 清洗最新run
  python -m bench.tools.clean --run latest
  
  # 清洗指定run
  python -m bench.tools.clean --run 20251015_131147
  
  # 不过滤unknown字段
  python -m bench.tools.clean --run latest --no-filter-unknown
  
  # 不过滤失败样本
  python -m bench.tools.clean --run latest --no-filter-failed
        """
    )
    
    parser.add_argument(
        '--run', '-r',
        default='latest',
        help='Run ID (如 "20251015_131147" 或 "latest"，默认: latest)'
    )
    parser.add_argument(
        '--no-filter-unknown',
        action='store_true',
        help='不过滤包含unknown的样本'
    )
    parser.add_argument(
        '--no-filter-failed',
        action='store_true',
        help='不过滤测试失败的样本'
    )
    
    args = parser.parse_args()
    
    # 创建清洗器
    try:
        cleaner = DataCleaner(
            run_id=args.run,
            filter_unknown=not args.no_filter_unknown,
            filter_failed=not args.no_filter_failed,
        )
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return 1
    
    try:
        # 1. 加载测试结果
        cleaner.load_test_results()
        
        # 2. 加载样本
        cleaner.load_samples()
        
        # 3. 过滤样本
        filtered_samples = cleaner.filter_samples()
        
        if not filtered_samples:
            logger.error("❌ 没有样本通过过滤")
            return 1
        
        # 4. 保存清洗后的数据
        cleaner.save_cleaned_data(filtered_samples)
        
        # 5. 打印摘要
        cleaner.print_summary()
        
        print(f"\n✅ 清洗完成！")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 清洗失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

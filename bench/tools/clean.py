#!/usr/bin/env python3
"""
data清洗工具

Features:
1. fromstage3和testresult中筛选sample
2. 应用过滤规则
3. generate清洗后的data

Usage:
    # 清洗latestrun
    python -m bench.tools.clean --run latest
    
    # 清洗specifiedrun
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
    """data清洗器"""
    
    # default过滤规则
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
            filter_unknown: whether过滤includeunknown的sample
            filter_failed: whether过滤testfailed的sample
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
        
        logger.info(f"📂 Rundirectory: {self.run_dir}")
        logger.info(f"📂 清洗输出: {self.cleaned_dir}")
    
    def load_test_results(self):
        """loadtestresult"""
        if not self.filter_failed:
            logger.info("⚠️  不过滤testfailed的sample")
            return
        
        has_tests = self.run_manager.has_tests(self.run_id)
        if not has_tests:
            logger.warning("⚠️  没有testresult，will不过滤failedsample")
            self.filter_failed = False
            return
        
        tests_dir = self.run_manager.get_tests_dir(self.run_id)
        
        # 优先Usepassed.jsonl，if不exist则Usedetails.jsonl
        passed_file = tests_dir / 'passed.jsonl'
        details_file = tests_dir / 'details.jsonl'
        
        passed_count = 0
        if passed_file.exists():
            logger.info(f"📂 loadtestresult: {passed_file}")
            with passed_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    result = json.loads(line)
                    self.passed_sample_ids.add(result['sample_id'])
                    passed_count += 1
        elif details_file.exists():
            logger.info(f"📂 from详细result中loadvia的sample: {details_file}")
            with details_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    result = json.loads(line)
                    # 只添加passed=True的sample
                    if result.get('passed', False):
                        self.passed_sample_ids.add(result['sample_id'])
                        passed_count += 1
        else:
            logger.warning(f"⚠️  notfoundtestresultfile")
            self.filter_failed = False
            return
        
        # if有重复ID，输出警告
        unique_ids = len(self.passed_sample_ids)
        if passed_count > unique_ids:
            logger.warning(f"⚠️  发现 {passed_count - unique_ids} 个重复的sample_id在testresult中")
            logger.warning(f"   这may是becausegenerate的data有重复ID，建议checkgenerate逻辑")
        
        logger.info(f"✅ load {unique_ids} 个唯一的viatest的sampleID (total {passed_count} 条viarecord)")
        self.stats['total_passed_tests'] = unique_ids
        self.stats['total_passed_records'] = passed_count
    
    def load_samples(self):
        """load原始sample count据"""
        # getto源raw
        raw_id = self.run_manager.get_source_raw(self.run_id)
        if not raw_id:
            raise FileNotFoundError(f"unable to确定run {self.run_id} 的to源raw")
        
        stage3_file = self.run_manager.get_stage_file_from_raw(raw_id, 3)
        
        if not stage3_file.exists():
            raise FileNotFoundError(f"Stage3file不exist: {stage3_file}")
        
        logger.info(f"📂 loadsample count据: {stage3_file}")
        
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
                    logger.warning(f"⚠️  行 {line_num} 解析failed: {e}")
        
        logger.info(f"✅ load {count} 个sample")
        self.stats['total_loaded'] = count
    
    def filter_samples(self) -> List[Dict[str, Any]]:
        """过滤sample"""
        logger.info("🧹 start过滤sample...")
        logger.info(f"   filter_failed={self.filter_failed}, passed_ids count={len(self.passed_sample_ids)}")
        
        filtered_samples = []
        
        for sample in self.samples:
            sample_id = sample.get('id', '')
            class_info = sample.get('class', {})
            
            # 规则1: 过滤testfailed的sample
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
            
            # 规则2: 过滤includeunknown的sample
            if self.filter_unknown and 'unknown' in [lang, instruction_type, structure, operation]:
                self.stats['filter_reasons']['unknown_fields'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 规则3: check指令type
            if instruction_type not in self.ALLOWED_INSTRUCTION_TYPES:
                self.stats['filter_reasons']['invalid_instruction_type'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 规则4: check结构
            if structure not in self.ALLOWED_STRUCTURES:
                self.stats['filter_reasons']['invalid_structure'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # 规则5: check操作
            if operation not in self.ALLOWED_OPERATIONS:
                self.stats['filter_reasons']['invalid_operation'] += 1
                self.stats['total_filtered'] += 1
                continue
            
            # viaall过滤
            filtered_samples.append(sample)
        
        self.stats['total_final'] = len(filtered_samples)
        logger.info(f"✅ 过滤complete: {len(filtered_samples)} 个sample保留")
        logger.info(f"   过滤掉: {self.stats['total_filtered']} 个sample")
        
        return filtered_samples
    
    def save_cleaned_data(self, samples: List[Dict[str, Any]]):
        """save清洗后的data"""
        logger.info("💾 save清洗后的data...")
        
        # 1. save清洗后的sample
        cleaned_file = self.cleaned_dir / 'cleaned.jsonl'
        with cleaned_file.open('w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        logger.info(f"  ✅ 清洗data: {cleaned_file}")
        
        # 2. generatemetadata
        # getto源raw
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
        logger.info(f"  ✅ metadata: {metadata_file}")
        
        # 3. generatestatistics
        stats = self._generate_stats(samples)
        stats_file = self.cleaned_dir / 'stats.json'
        with stats_file.open('w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ statistics: {stats_file}")
        
        # 4. generate过滤report
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
        logger.info(f"  ✅ 过滤report: {report_file}")
        
        logger.info(f"💾 allfilealreadysaveto: {self.cleaned_dir}")
    
    def _generate_stats(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """generatestatistics"""
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
        print(f"  loadsample count: {self.stats['total_loaded']}")
        if self.stats['total_passed_tests'] > 0:
            print(f"  viatest: {self.stats['total_passed_tests']}")
        print(f"  过滤sample count: {self.stats['total_filtered']}")
        print(f"  最终sample count: {self.stats['total_final']}")
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
        description="data清洗工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
过滤规则:
  1. 过滤testfailed的sample（if有testresult）
  2. 过滤include'unknown'的sample
  3. 只保留'direct'和'indirect'指令type
  4. 只保留'single'和'workflow'结构
  5. 只保留12种核心操作

example:
  # 清洗latestrun
  python -m bench.tools.clean --run latest
  
  # 清洗specifiedrun
  python -m bench.tools.clean --run 20251015_131147
  
  # 不过滤unknown字段
  python -m bench.tools.clean --run latest --no-filter-unknown
  
  # 不过滤failedsample
  python -m bench.tools.clean --run latest --no-filter-failed
        """
    )
    
    parser.add_argument(
        '--run', '-r',
        default='latest',
        help='Run ID (如 "20251015_131147" or "latest"，default: latest)'
    )
    parser.add_argument(
        '--no-filter-unknown',
        action='store_true',
        help='不过滤includeunknown的sample'
    )
    parser.add_argument(
        '--no-filter-failed',
        action='store_true',
        help='不过滤testfailed的sample'
    )
    
    args = parser.parse_args()
    
    # create清洗器
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
        # 1. loadtestresult
        cleaner.load_test_results()
        
        # 2. loadsample
        cleaner.load_samples()
        
        # 3. 过滤sample
        filtered_samples = cleaner.filter_samples()
        
        if not filtered_samples:
            logger.error("❌ 没有samplevia过滤")
            return 1
        
        # 4. save清洗后的data
        cleaner.save_cleaned_data(filtered_samples)
        
        # 5. 打印摘要
        cleaner.print_summary()
        
        print(f"\n✅ 清洗complete！")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 清洗failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

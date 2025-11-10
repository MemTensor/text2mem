#!/usr/bin/env python3
"""
Benchmarktest工具 v3.0

Features:
1. fromrawcreaterun并runtest
2. 收集success/failedsample
3. generate详细的testreport

Usage:
    # fromlatestrawcreaterun并test
    python -m bench.tools.test --raw latest
    
    # fromspecifiedrawcreaterun并test
    python -m bench.tools.test --raw 20251015_131147
    
    # testalreadyexist的run
    python -m bench.tools.test --run 20251015_131147
    
    # 只test前N个sample
    python -m bench.tools.test --raw latest --limit 10
"""

import argparse
import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bench.tools.run_manager import RunManager

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """testrun器"""
    
    def __init__(self, raw_id: Optional[str] = None, run_id: Optional[str] = None, verbose: bool = False):
        """
        Args:
            raw_id: Raw ID（用于create新run）
            run_id: Run ID（用于testalreadyexist的run）
            verbose: whether显示详细输出
        """
        self.verbose = verbose
        self.run_manager = RunManager()
        
        if raw_id:
            # fromrawcreaterun
            logger.info(f"📦 fromrawcreaterun: {raw_id}")
            self.raw_id = raw_id if raw_id != 'latest' else self.run_manager.get_latest_raw()
            
            if not self.raw_id:
                raise ValueError("没有foundrawdata")
            
            # createrundirectory
            self.run_dir = self.run_manager.create_run_from_raw(self.raw_id)
            self.run_id = self.raw_id  # run_iddefault与raw_id相同
            
            # getstage3filepath（fromraw）
            self.stage3_file = self.run_manager.get_stage_file_from_raw(self.raw_id, 3)
            
        elif run_id:
            # Usealreadyexist的run
            self.run_id = run_id
            self.run_dir = self.run_manager.get_run_dir(run_id)
            
            # getto源raw
            self.raw_id = self.run_manager.get_source_raw(run_id)
            if self.raw_id:
                self.stage3_file = self.run_manager.get_stage_file_from_raw(self.raw_id, 3)
            else:
                raise ValueError(f"unable to确定run {run_id} 的to源raw")
        else:
            raise ValueError("mustspecified raw_id or run_id")
        
        # gettestdirectory
        self.tests_dir = self.run_manager.get_tests_dir(self.run_id)
        
        # loaddata
        self.samples: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []
        
        # test统计
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'by_operation': defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0}),
            'by_language': defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0}),
        }
        
        logger.info(f"📂 Rawdirectory: {self.run_manager.get_raw_dir(self.raw_id)}")
        logger.info(f"📂 Rundirectory: {self.run_dir}")
        logger.info(f"📂 testresult: {self.tests_dir}")
    
    def load_samples(self) -> int:
        """loadsample count据"""
        if not self.stage3_file.exists():
            raise FileNotFoundError(f"Stage3file不exist: {self.stage3_file}")
        
        logger.info(f"📂 loadsample: {self.stage3_file}")
        
        count = 0
        with self.stage3_file.open('r', encoding='utf-8') as f:
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
    
    def run_tests(self, limit: Optional[int] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        """runtest
        
        Args:
            limit: 限制testsample count量（用于快速test）
            timeout: eachsample的超时time（秒）
        """
        # 导入testrunner
        try:
            from bench.core.runner import BenchRunner, BenchConfig
        except ImportError:
            logger.error("❌ unable to导入 bench.core.runner，请ensure在正确的环境中run")
            raise
        
        samples_to_test = self.samples[:limit] if limit else self.samples
        total = len(samples_to_test)
        
        logger.info(f"🧪 starttest {total} 个sample...")
        
        # configurationrunner
        config = BenchConfig(
            db_root=Path('bench/data/db'),
            output_dir=Path('bench/output'),
            timeout=timeout,
        )
        runner = BenchRunner(config)
        
        start_time = time.time()
        
        for idx, sample in enumerate(samples_to_test, 1):
            sample_id = sample.get('id', f'sample-{idx}')
            class_info = sample.get('class', {})
            
            # 提取分类信息
            lang = class_info.get('lang', 'unknown')
            
            # 提取操作
            schema_list = sample.get('schema_list', [])
            operation = schema_list[0].get('op', 'unknown') if schema_list else 'unknown'
            
            # 显示进度 - eachsample都显示（Uselogger让format统一）
            progress_pct = (idx / total) * 100
            logger.info(f"[{idx}/{total} {progress_pct:.1f}%] test: {sample_id} ({operation})")
            
            # runtest
            sample_start = time.time()
            try:
                result = runner.run_sample(sample, sample_id=sample_id)
                sample_duration = time.time() - sample_start
                
                # recordresult
                passed = result.passed
                error_msg = None
                
            except Exception as e:
                # 捕获run错误
                passed = False
                error_msg = str(e)
                sample_duration = time.time() - sample_start
                logger.error(f"  ❌ 错误: {sample_id} - {error_msg}")
                self.stats['errors'] += 1
            
            # update统计
            self.stats['total'] += 1
            if passed:
                self.stats['passed'] += 1
            else:
                self.stats['failed'] += 1
            
            # 按维度统计
            for dim_name, dim_value in [
                ('by_operation', operation),
                ('by_language', lang),
            ]:
                self.stats[dim_name][dim_value]['total'] += 1
                if passed:
                    self.stats[dim_name][dim_value]['passed'] += 1
                else:
                    self.stats[dim_name][dim_value]['failed'] += 1
            
            # recordresult
            test_result = {
                'sample_id': sample_id,
                'passed': passed,
                'duration': sample_duration,
                'class': class_info,
                'operation': operation,
                'error': error_msg,
            }
            
            if not passed and self.verbose:
                # recordfailed详情
                if error_msg:
                    test_result['error_details'] = error_msg
                elif 'result' in locals():
                    test_result['failed_assertions'] = [
                        {'name': a.name, 'message': a.message}
                        for a in result.assertions if not a.passed
                    ]
            
            self.results.append(test_result)
            
            # 显示result - 总是显示result
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  → {status} ({sample_duration:.2f}s) | Pass: {self.stats['passed']}/{self.stats['total']}", flush=True)
            
            # 每10个sample显示一次汇总
            if idx % 10 == 0 or idx == total:
                pass_rate = (self.stats['passed'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
                print(f"  📊 current统计: Pass={self.stats['passed']}, Fail={self.stats['failed']}, Rate={pass_rate:.1f}%", flush=True)
        
        total_time = time.time() - start_time
        
        logger.info(f"✅ testcomplete，总耗时: {total_time:.2f}s")
        
        return self.stats
    
    def save_results(self):
        """savetestresult"""
        logger.info("💾 savetestresult...")
        
        # 1. save摘要
        summary = {
            'metadata': {
                'run_id': self.run_id,
                'tested_at': datetime.now().isoformat(),
                'total_samples': self.stats['total'],
            },
            'summary': {
                'total': self.stats['total'],
                'passed': self.stats['passed'],
                'failed': self.stats['failed'],
                'errors': self.stats['errors'],
                'pass_rate': self.stats['passed'] / self.stats['total'] * 100 if self.stats['total'] > 0 else 0,
            },
            'by_operation': dict(self.stats['by_operation']),
            'by_language': dict(self.stats['by_language']),
        }
        
        summary_file = self.tests_dir / 'summary.json'
        with summary_file.open('w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 摘要: {summary_file}")
        
        # 2. 分离via和failed的sample
        passed_samples = []
        failed_samples = []
        
        for result in self.results:
            if result['passed']:
                passed_samples.append(result)
            else:
                failed_samples.append(result)
        
        # savevia的sample
        if passed_samples:
            passed_file = self.tests_dir / 'passed.jsonl'
            with passed_file.open('w', encoding='utf-8') as f:
                for result in passed_samples:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            logger.info(f"  ✅ viasample: {passed_file} ({len(passed_samples)} 个)")
        
        # savefailed的sample
        if failed_samples:
            failed_file = self.tests_dir / 'failed.jsonl'
            with failed_file.open('w', encoding='utf-8') as f:
                for result in failed_samples:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            logger.info(f"  ❌ failedsample: {failed_file} ({len(failed_samples)} 个)")
        
        # 3. save完整result
        details_file = self.tests_dir / 'details.jsonl'
        with details_file.open('w', encoding='utf-8') as f:
            for result in self.results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        logger.info(f"  📄 完整result: {details_file}")
        
        # 4. savestatistics
        stats_file = self.tests_dir / 'stats.json'
        with stats_file.open('w', encoding='utf-8') as f:
            json.dump({
                'total': self.stats['total'],
                'passed': self.stats['passed'],
                'failed': self.stats['failed'],
                'errors': self.stats['errors'],
                'pass_rate': self.stats['passed'] / self.stats['total'] * 100 if self.stats['total'] > 0 else 0,
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 allresultalreadysaveto: {self.tests_dir}")
    
    def print_summary(self):
        """打印test摘要"""
        print("\n" + "="*80)
        print("📊 test摘要")
        print("="*80)
        
        print(f"\n总体result:")
        print(f"  总sample count: {self.stats['total']}")
        print(f"  via: {self.stats['passed']} ({self.stats['passed']/self.stats['total']*100:.1f}%)")
        print(f"  failed: {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        if self.stats['errors'] > 0:
            print(f"  错误: {self.stats['errors']}")
        
        # 按操作统计
        print(f"\n按操作统计:")
        for op, stat in sorted(self.stats['by_operation'].items(), key=lambda x: x[1]['total'], reverse=True):
            total = stat['total']
            passed = stat['passed']
            rate = passed / total * 100 if total > 0 else 0
            print(f"  {op}: {passed}/{total} ({rate:.1f}%)")
        
        # 按语言统计
        print(f"\n按语言统计:")
        for lang, stat in sorted(self.stats['by_language'].items(), key=lambda x: x[1]['total'], reverse=True):
            total = stat['total']
            passed = stat['passed']
            rate = passed / total * 100 if total > 0 else 0
            print(f"  {lang}: {passed}/{total} ({rate:.1f}%)")
        
        print("\n" + "="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Benchmarktest工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
example:
  # fromlatestrawcreaterun并test
  python -m bench.tools.test --raw latest
  
  # fromspecifiedrawcreaterun并test
  python -m bench.tools.test --raw 20251015_131147
  
  # testalreadyexist的run
  python -m bench.tools.test --run 20251015_131147
  
  # 只test前10个sample
  python -m bench.tools.test --raw latest --limit 10 --verbose
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--raw',
        help='fromRaw IDcreaterun并test (如 "20251015_131147" or "latest")'
    )
    group.add_argument(
        '--run',
        help='testalreadyexist的Run ID (如 "20251015_131147" or "latest")'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='限制testsample count量（用于快速test）'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=float,
        help='eachsample的超时time（秒）'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细输出'
    )
    
    args = parser.parse_args()
    
    # createtestrun器
    try:
        runner = TestRunner(raw_id=args.raw, run_id=args.run, verbose=args.verbose)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"❌ {e}")
        return 1
    
    try:
        # loadsample
        runner.load_samples()
        
        # runtest
        runner.run_tests(limit=args.limit, timeout=args.timeout)
        
        # saveresult
        runner.save_results()
        
        # 打印摘要
        runner.print_summary()
        
        print(f"\n✅ testcomplete！")
        
        # Returns码：if有failed则Returns1
        return 1 if runner.stats['failed'] > 0 else 0
        
    except Exception as e:
        logger.error(f"❌ testfailed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

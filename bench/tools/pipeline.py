#!/usr/bin/env python3
"""
Benchmark完整流程工具 v3.0

Features:
fromrawdatato最终benchmark的完整自动化流程：
1. test（createrun）
2. 清洗并buildbenchmark（合并step）

Usage:
    # 处理latestraw
    python -m bench.tools.pipeline --raw latest --version v2
    
    # 处理specifiedraw
    python -m bench.tools.pipeline --raw 20251015_131147 --version v2
    
    # skipteststep
    python -m bench.tools.pipeline --raw latest --version v2 --skip-tests
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from bench.tools.run_manager import RunManager

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkPipeline:
    """Benchmark完整流程"""
    
    def __init__(
        self,
        raw_id: str,
        version: Optional[str] = None,
        skip_tests: bool = False,
        verbose: bool = False,
    ):
        """
        Args:
            raw_id: Raw ID
            version: Benchmarkversion号（如v2, v3等）
            skip_tests: skiptestrun
            verbose: 详细输出
        """
        self.raw_id = raw_id
        self.verbose = verbose
        self.skip_tests = skip_tests
        
        # 确定输出version
        if version:
            self.version = version
        else:
            # 自动generateversion号（based onraw_id）
            if raw_id == 'latest':
                run_manager = RunManager()
                actual_raw_id = run_manager.get_latest_raw()
            else:
                actual_raw_id = raw_id
            self.version = f"v_{actual_raw_id}"
        
        self.run_manager = RunManager()
        
        # getrawdirectory
        try:
            self.raw_dir = self.run_manager.get_raw_dir(raw_id)
            if raw_id == 'latest':
                self.raw_id = self.run_manager.get_latest_raw()
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            raise
        
        logger.info(f"📋 Pipelineconfiguration:")
        logger.info(f"  Raw ID: {self.raw_id}")
        logger.info(f"  Rawdirectory: {self.raw_dir}")
        logger.info(f"  Benchmarkversion: {self.version}")
    
    def run(self) -> bool:
        """run完整流程"""
        logger.info("\n" + "="*80)
        logger.info("🚀 startBenchmarkbuild流程")
        logger.info("="*80)
        
        try:
            # Step 1: runtest（createrun）
            if not self.skip_tests:
                if not self._step1_tests():
                    return False
            else:
                logger.info("\n⏭️  skiptestrun")
                # ifskiptest，需要ensurerunalreadyexist
                runs = self.run_manager.list_runs()
                if self.raw_id not in runs:
                    logger.error(f"❌ Run不exist: {self.raw_id}")
                    logger.info("   提示：cannotskiptest，becauserun还notcreate")
                    return False
            
            # 确定run_id
            self.run_id = self.raw_id
            
            # Step 2: 清洗并buildbenchmark（合并step）
            if not self._step2_clean_and_build():
                return False
            
            logger.info("\n" + "="*80)
            logger.info("✅ Pipelinecomplete！")
            logger.info("="*80)
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Pipelinefailed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _step1_tests(self) -> bool:
        """Step 1: runtest（createrun）"""
        logger.info("\n" + "="*80)
        logger.info("🧪 Step 1: runtest（createrun）")
        logger.info("="*80)
        
        from bench.tools.test import TestRunner
        
        runner = TestRunner(raw_id=self.raw_id, verbose=self.verbose)
        runner.load_samples()
        runner.run_tests()
        runner.save_results()
        
        if self.verbose:
            runner.print_summary()
        
        # checktestresult
        if runner.stats['failed'] > 0:
            logger.warning(f"⚠️  有 {runner.stats['failed']} 个sampletestfailed")
            logger.warning(f"   这些samplewill在清洗step中referenced by过滤掉")
        
        self.run_id = runner.run_id
        logger.info(f"✅ Step 1 complete: {runner.tests_dir}")
        return True
    
    def _step2_clean_and_build(self) -> bool:
        """Step 2: 清洗并buildbenchmark（合并step）"""
        logger.info("\n" + "="*80)
        logger.info("🧹 Step 2: 清洗data并buildBenchmark")
        logger.info("="*80)
        
        from bench.tools.clean import DataCleaner
        from bench.tools.build import BenchmarkBuilder
        
        # 2.1 清洗data
        logger.info("📍 2.1 清洗data...")
        cleaner = DataCleaner(
            run_id=self.run_id,
            filter_unknown=True,
            filter_failed=(not self.skip_tests),
        )
        
        cleaner.load_test_results()
        cleaner.load_samples()
        filtered_samples = cleaner.filter_samples()
        
        if not filtered_samples:
            logger.error("❌ 没有samplevia过滤")
            return False
        
        cleaner.save_cleaned_data(filtered_samples)
        
        if self.verbose:
            cleaner.print_summary()
        
        logger.info(f"✅ 清洗complete: {self.run_manager.get_cleaned_dir(self.run_id)}")
        
        # 2.2 buildbenchmark
        logger.info("\n📍 2.2 buildBenchmark...")
        builder = BenchmarkBuilder(
            run_id=self.run_id,
            version=self.version,
            rebuild_ids=True,
        )
        
        builder.load_cleaned_data()
        builder.rebuild_sample_ids()
        builder.build()
        
        if self.verbose:
            builder.print_summary()
        
        logger.info(f"✅ buildcomplete: {self.run_manager.get_benchmark_dir(self.version)}")
        
        return True
    
    def print_summary(self):
        """打印完整摘要"""
        print("\n" + "="*80)
        print("📋 Pipeline摘要")
        print("="*80)
        
        print(f"\n输入:")
        print(f"  Raw ID: {self.raw_id}")
        print(f"  Rawdirectory: {self.raw_dir}")
        
        print(f"\n输出:")
        print(f"  Run ID: {self.run_id}")
        print(f"  Rundirectory: {self.run_manager.get_run_dir(self.run_id)}")
        print(f"  Benchmarkversion: {self.version}")
        print(f"  Benchmarkdirectory: {self.run_manager.get_benchmark_dir(self.version)}")
        
        print(f"\nexecute的step:")
        steps = []
        if not self.skip_tests:
            steps.append("✅ runtest（createrun）")
        steps.append("✅ 清洗data并buildBenchmark")
        
        for step in steps:
            print(f"  {step}")
        
        print(f"\n下一步:")
        print(f"  # verifybenchmark")
        print(f"  python -m bench run --split benchmark --verbose")
        
        print("\n" + "="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Benchmark完整流程工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
完整流程包括:
  1. runtest - fromrawcreaterun并testallsample
  2. 清洗并build - 过滤failedsample，应用规则，重新分配ID，generate最终benchmark

example:
  # 处理latestraw
  python -m bench.tools.pipeline --raw latest --version v2
  
  # 处理specifiedraw
  python -m bench.tools.pipeline --raw 20251015_131147 --version v2
  
  # skiptest，直接清洗并build（runmustalreadyexist）
  python -m bench.tools.pipeline --raw latest --version v2 --skip-tests
        """
    )
    
    parser.add_argument(
        '--raw',
        required=True,
        help='Raw ID (如 "20251015_131147" or "latest")'
    )
    parser.add_argument(
        '--version', '-v',
        help='Benchmarkversion号 (如 "v2", "v3"，default：自动generate)'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='skiptestrun（runmustalreadyexist）'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细输出'
    )
    
    args = parser.parse_args()
    
    # createpipeline
    try:
        pipeline = BenchmarkPipeline(
            raw_id=args.raw,
            version=args.version,
            skip_tests=args.skip_tests,
            verbose=args.verbose,
        )
    except FileNotFoundError:
        return 1
    
    # run
    success = pipeline.run()
    
    if success:
        pipeline.print_summary()
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())

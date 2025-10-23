#!/usr/bin/env python3
"""
Benchmark完整流程工具 v3.0

功能：
从raw数据到最终benchmark的完整自动化流程：
1. 测试（创建run）
2. 清洗并构建benchmark（合并步骤）

用法：
    # 处理最新raw
    python -m bench.tools.pipeline --raw latest --version v2
    
    # 处理指定raw
    python -m bench.tools.pipeline --raw 20251015_131147 --version v2
    
    # 跳过测试步骤
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
            version: Benchmark版本号（如v2, v3等）
            skip_tests: 跳过测试运行
            verbose: 详细输出
        """
        self.raw_id = raw_id
        self.verbose = verbose
        self.skip_tests = skip_tests
        
        # 确定输出版本
        if version:
            self.version = version
        else:
            # 自动生成版本号（基于raw_id）
            if raw_id == 'latest':
                run_manager = RunManager()
                actual_raw_id = run_manager.get_latest_raw()
            else:
                actual_raw_id = raw_id
            self.version = f"v_{actual_raw_id}"
        
        self.run_manager = RunManager()
        
        # 获取raw目录
        try:
            self.raw_dir = self.run_manager.get_raw_dir(raw_id)
            if raw_id == 'latest':
                self.raw_id = self.run_manager.get_latest_raw()
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            raise
        
        logger.info(f"📋 Pipeline配置:")
        logger.info(f"  Raw ID: {self.raw_id}")
        logger.info(f"  Raw目录: {self.raw_dir}")
        logger.info(f"  Benchmark版本: {self.version}")
    
    def run(self) -> bool:
        """运行完整流程"""
        logger.info("\n" + "="*80)
        logger.info("🚀 开始Benchmark构建流程")
        logger.info("="*80)
        
        try:
            # Step 1: 运行测试（创建run）
            if not self.skip_tests:
                if not self._step1_tests():
                    return False
            else:
                logger.info("\n⏭️  跳过测试运行")
                # 如果跳过测试，需要确保run已存在
                runs = self.run_manager.list_runs()
                if self.raw_id not in runs:
                    logger.error(f"❌ Run不存在: {self.raw_id}")
                    logger.info("   提示：不能跳过测试，因为run还未创建")
                    return False
            
            # 确定run_id
            self.run_id = self.raw_id
            
            # Step 2: 清洗并构建benchmark（合并步骤）
            if not self._step2_clean_and_build():
                return False
            
            logger.info("\n" + "="*80)
            logger.info("✅ Pipeline完成！")
            logger.info("="*80)
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Pipeline失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _step1_tests(self) -> bool:
        """Step 1: 运行测试（创建run）"""
        logger.info("\n" + "="*80)
        logger.info("🧪 Step 1: 运行测试（创建run）")
        logger.info("="*80)
        
        from bench.tools.test import TestRunner
        
        runner = TestRunner(raw_id=self.raw_id, verbose=self.verbose)
        runner.load_samples()
        runner.run_tests()
        runner.save_results()
        
        if self.verbose:
            runner.print_summary()
        
        # 检查测试结果
        if runner.stats['failed'] > 0:
            logger.warning(f"⚠️  有 {runner.stats['failed']} 个样本测试失败")
            logger.warning(f"   这些样本将在清洗步骤中被过滤掉")
        
        self.run_id = runner.run_id
        logger.info(f"✅ Step 1 完成: {runner.tests_dir}")
        return True
    
    def _step2_clean_and_build(self) -> bool:
        """Step 2: 清洗并构建benchmark（合并步骤）"""
        logger.info("\n" + "="*80)
        logger.info("🧹 Step 2: 清洗数据并构建Benchmark")
        logger.info("="*80)
        
        from bench.tools.clean import DataCleaner
        from bench.tools.build import BenchmarkBuilder
        
        # 2.1 清洗数据
        logger.info("📍 2.1 清洗数据...")
        cleaner = DataCleaner(
            run_id=self.run_id,
            filter_unknown=True,
            filter_failed=(not self.skip_tests),
        )
        
        cleaner.load_test_results()
        cleaner.load_samples()
        filtered_samples = cleaner.filter_samples()
        
        if not filtered_samples:
            logger.error("❌ 没有样本通过过滤")
            return False
        
        cleaner.save_cleaned_data(filtered_samples)
        
        if self.verbose:
            cleaner.print_summary()
        
        logger.info(f"✅ 清洗完成: {self.run_manager.get_cleaned_dir(self.run_id)}")
        
        # 2.2 构建benchmark
        logger.info("\n📍 2.2 构建Benchmark...")
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
        
        logger.info(f"✅ 构建完成: {self.run_manager.get_benchmark_dir(self.version)}")
        
        return True
    
    def print_summary(self):
        """打印完整摘要"""
        print("\n" + "="*80)
        print("📋 Pipeline摘要")
        print("="*80)
        
        print(f"\n输入:")
        print(f"  Raw ID: {self.raw_id}")
        print(f"  Raw目录: {self.raw_dir}")
        
        print(f"\n输出:")
        print(f"  Run ID: {self.run_id}")
        print(f"  Run目录: {self.run_manager.get_run_dir(self.run_id)}")
        print(f"  Benchmark版本: {self.version}")
        print(f"  Benchmark目录: {self.run_manager.get_benchmark_dir(self.version)}")
        
        print(f"\n执行的步骤:")
        steps = []
        if not self.skip_tests:
            steps.append("✅ 运行测试（创建run）")
        steps.append("✅ 清洗数据并构建Benchmark")
        
        for step in steps:
            print(f"  {step}")
        
        print(f"\n下一步:")
        print(f"  # 验证benchmark")
        print(f"  python -m bench run --split benchmark --verbose")
        
        print("\n" + "="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Benchmark完整流程工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
完整流程包括:
  1. 运行测试 - 从raw创建run并测试所有样本
  2. 清洗并构建 - 过滤失败样本，应用规则，重新分配ID，生成最终benchmark

示例:
  # 处理最新raw
  python -m bench.tools.pipeline --raw latest --version v2
  
  # 处理指定raw
  python -m bench.tools.pipeline --raw 20251015_131147 --version v2
  
  # 跳过测试，直接清洗并构建（run必须已存在）
  python -m bench.tools.pipeline --raw latest --version v2 --skip-tests
        """
    )
    
    parser.add_argument(
        '--raw',
        required=True,
        help='Raw ID (如 "20251015_131147" 或 "latest")'
    )
    parser.add_argument(
        '--version', '-v',
        help='Benchmark版本号 (如 "v2", "v3"，默认：自动生成)'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='跳过测试运行（run必须已存在）'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细输出'
    )
    
    args = parser.parse_args()
    
    # 创建pipeline
    try:
        pipeline = BenchmarkPipeline(
            raw_id=args.raw,
            version=args.version,
            skip_tests=args.skip_tests,
            verbose=args.verbose,
        )
    except FileNotFoundError:
        return 1
    
    # 运行
    success = pipeline.run()
    
    if success:
        pipeline.print_summary()
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())

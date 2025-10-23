#!/usr/bin/env python3
"""
Benchmark构建工具

功能：
1. 从cleaned数据构建benchmark
2. 重新分配ID
3. 生成元数据
4. 支持版本管理

用法：
    # 从最新run构建benchmark
    python -m bench.tools.build --run latest --version v2
    
    # 从指定run构建
    python -m bench.tools.build --run 20251015_131147 --version v2
    
    # 不重新分配ID
    python -m bench.tools.build --run latest --version v2 --no-rebuild-ids
"""

import argparse
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bench.tools.run_manager import RunManager

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkBuilder:
    """Benchmark构建器"""
    
    def __init__(
        self,
        run_id: str,
        version: str,
        rebuild_ids: bool = True,
    ):
        """
        Args:
            run_id: Run ID
            version: Benchmark版本号 (如 "v1", "v2")
            rebuild_ids: 是否重新分配ID
        """
        self.run_id = run_id
        self.version = version
        self.rebuild_ids = rebuild_ids
        
        self.run_manager = RunManager()
        self.run_dir = self.run_manager.get_run_dir(run_id)
        self.cleaned_dir = self.run_manager.get_cleaned_dir(run_id)
        self.benchmark_dir = self.run_manager.get_benchmark_dir(version)
        
        self.samples: List[Dict[str, Any]] = []
        
        logger.info(f"📂 Run目录: {self.run_dir}")
        logger.info(f"📂 Cleaned数据: {self.cleaned_dir}")
        logger.info(f"📂 Benchmark输出: {self.benchmark_dir}")
    
    def load_cleaned_data(self):
        """加载清洗后的数据（如果不存在则先执行清洗）"""
        cleaned_file = self.cleaned_dir / 'cleaned.jsonl'
        
        # 如果cleaned数据不存在，尝试自动清洗
        if not cleaned_file.exists():
            logger.warning(f"⚠️  清洗数据不存在: {cleaned_file}")
            logger.info("🧹 开始自动清洗数据...")
            
            # 导入并执行清洗
            from bench.tools.clean import DataCleaner
            
            cleaner = DataCleaner(run_id=self.run_id)
            cleaner.load_test_results()
            cleaner.load_samples()
            filtered_samples = cleaner.filter_samples()
            cleaner.save_cleaned_data(filtered_samples)
            
            logger.info(f"✅ 自动清洗完成")
            
            # 再次检查
            if not cleaned_file.exists():
                raise FileNotFoundError(
                    f"清洗后数据仍不存在: {cleaned_file}"
                )
        
        logger.info(f"📂 加载清洗数据: {cleaned_file}")
        
        count = 0
        with cleaned_file.open('r', encoding='utf-8') as f:
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
    
    def rebuild_sample_ids(self):
        """重新分配样本ID"""
        if not self.rebuild_ids:
            logger.info("⏭️  跳过ID重新分配")
            return
        
        logger.info("🔧 重新分配样本ID...")
        
        # 按分类分组
        groups = {}
        for sample in self.samples:
            class_info = sample.get('class', {})
            
            # 提取分类信息
            lang = class_info.get('lang', 'unknown')
            instruction_type = class_info.get('instruction_type', 'unknown')
            structure = class_info.get('structure', 'unknown')
            
            # 提取操作类型
            schema_list = sample.get('schema_list', [])
            op = schema_list[0].get('op', 'unknown').lower() if schema_list else 'unknown'
            
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
                
                # 保存原始ID
                if 'id' in sample:
                    sample['_original_id'] = sample['id']
                
                # 更新 ID
                sample['id'] = new_id
                
                new_samples.append(sample)
            
            logger.info(f"   {group_key}: {len(samples_list)} 个样本")
        
        self.samples = new_samples
        logger.info(f"✅ 重新分配了 {len(self.samples)} 个样本的 ID")
    
    def build(self):
        """构建benchmark"""
        logger.info("🏗️  构建Benchmark...")
        
        # 1. 保存benchmark数据
        benchmark_file = self.benchmark_dir / 'benchmark.jsonl'
        with benchmark_file.open('w', encoding='utf-8') as f:
            for sample in self.samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        logger.info(f"  ✅ Benchmark数据: {benchmark_file}")
        
        # 2. 生成元数据
        metadata = {
            'version': self.version,
            'created_at': datetime.now().isoformat(),
            'source_run': self.run_id,
            'source_path': str(self.cleaned_dir / 'cleaned.jsonl'),
            'total_samples': len(self.samples),
            'rebuilt_ids': self.rebuild_ids,
        }
        
        metadata_file = self.benchmark_dir / 'metadata.json'
        with metadata_file.open('w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 元数据: {metadata_file}")
        
        # 3. 生成统计信息
        stats = self._generate_stats()
        stats_file = self.benchmark_dir / 'stats.json'
        with stats_file.open('w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 统计信息: {stats_file}")
        
        # 4. 更新latest链接
        self.run_manager.update_benchmark_latest(self.version)
        logger.info(f"  ✅ 更新latest链接 → {self.version}")
        
        logger.info(f"🏗️  Benchmark构建完成: {self.benchmark_dir}")
    
    def _generate_stats(self) -> Dict[str, Any]:
        """生成统计信息"""
        langs = Counter()
        operations = Counter()
        instruction_types = Counter()
        structures = Counter()
        
        for sample in self.samples:
            class_info = sample.get('class', {})
            
            langs[class_info.get('lang', 'unknown')] += 1
            instruction_types[class_info.get('instruction_type', 'unknown')] += 1
            structures[class_info.get('structure', 'unknown')] += 1
            
            schema_list = sample.get('schema_list', [])
            if schema_list:
                operations[schema_list[0].get('op', 'unknown')] += 1
        
        return {
            'total': len(self.samples),
            'distribution': {
                'languages': dict(langs.most_common()),
                'operations': dict(operations.most_common()),
                'instruction_types': dict(instruction_types.most_common()),
                'structures': dict(structures.most_common()),
            }
        }
    
    def print_summary(self):
        """打印构建摘要"""
        print("\n" + "="*80)
        print("📊 Benchmark构建摘要")
        print("="*80)
        
        print(f"\n基本信息:")
        print(f"  Run ID: {self.run_id}")
        print(f"  Benchmark版本: {self.version}")
        print(f"  样本数量: {len(self.samples)}")
        print(f"  重新分配ID: {'是' if self.rebuild_ids else '否'}")
        
        print(f"\n输出文件:")
        print(f"  数据: {self.benchmark_dir}/benchmark.jsonl")
        print(f"  元数据: {self.benchmark_dir}/metadata.json")
        print(f"  统计: {self.benchmark_dir}/stats.json")
        
        print("\n" + "="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Benchmark构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从最新run构建benchmark
  python -m bench.tools.build --run latest --version v2
  
  # 从指定run构建
  python -m bench.tools.build --run 20251015_131147 --version v2
  
  # 不重新分配ID
  python -m bench.tools.build --run latest --version v2 --no-rebuild-ids
        """
    )
    
    parser.add_argument(
        '--run', '-r',
        default='latest',
        help='Run ID (如 "20251015_131147" 或 "latest"，默认: latest)'
    )
    parser.add_argument(
        '--version', '-v',
        required=True,
        help='Benchmark版本号 (如 "v1", "v2")'
    )
    parser.add_argument(
        '--no-rebuild-ids',
        action='store_true',
        help='不重新分配ID'
    )
    
    args = parser.parse_args()
    
    # 创建构建器
    try:
        builder = BenchmarkBuilder(
            run_id=args.run,
            version=args.version,
            rebuild_ids=not args.no_rebuild_ids,
        )
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return 1
    
    try:
        # 1. 加载清洗数据
        builder.load_cleaned_data()
        
        # 2. 重新分配ID
        builder.rebuild_sample_ids()
        
        # 3. 构建benchmark
        builder.build()
        
        # 4. 打印摘要
        builder.print_summary()
        
        print(f"\n✅ Benchmark构建完成！")
        print(f"\n💡 下一步:")
        print(f"   # 验证benchmark")
        print(f"   python -m bench run --split benchmark --verbose")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ 构建失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

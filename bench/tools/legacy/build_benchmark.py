#!/usr/bin/env python3
"""
构建 Benchmark：去重 + 筛选 + 重新分配 ID

工作流程：
1. 加载所有样本
2. 先按原 ID 去重（保留每个 ID 的最后一个实例）
3. 根据测试结果筛选（可选）
4. 重新分配唯一的新 ID

用法:
    # 所有唯一样本，重新分配 ID
    python build_benchmark.py
    
    # 只保留通过测试的样本，重新分配 ID
    python build_benchmark.py --passed-only
"""

import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, Any, Set, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinalBenchmarkBuilder:
    """最终 Benchmark 构建器：去重 + 筛选 + ID 重建"""
    
    def __init__(self):
        self.samples: Dict[str, Dict[str, Any]] = {}  # 按原 ID 去重
        self.passed_ids: Optional[Set[str]] = None
    
    def find_latest_stage3(self) -> Optional[Path]:
        """查找最新的 stage3 输出文件"""
        files = list(Path('.').glob("bench/generate/output/*stage3*.jsonl"))
        if not files:
            return None
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]
    
    def find_latest_results(self) -> Optional[Path]:
        """查找最新的测试结果文件"""
        patterns = [
            "bench/output/test_results_*.json",
            "bench/output/results_*.json",
        ]
        
        all_files = []
        for pat in patterns:
            all_files.extend(Path('.').glob(pat))
        
        if not all_files:
            return None
        
        all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return all_files[0]
    
    def load_samples(self, stage3_file: Path) -> int:
        """加载所有样本（不去重！）"""
        logger.info(f"📂 加载样本: {stage3_file.name}")
        
        samples_list = []
        count = 0
        with stage3_file.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    samples_list.append(sample)
                    count += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️  行 {line_num} 解析失败")
        
        # 转换为 dict，用索引作为临时 key
        self.samples = {str(i): sample for i, sample in enumerate(samples_list)}
        
        logger.info(f"✅ 加载 {count} 个样本（保留所有，不去重）")
        return count
    
    def load_test_results(self, results_file: Path) -> tuple[int, int]:
        """加载测试结果"""
        logger.info(f"📂 加载测试结果: {results_file.name}")
        
        with results_file.open('r', encoding='utf-8') as f:
            results = json.load(f)
        
        passed_ids = set()
        failed_ids = set()
        
        for result in results.get('results', []):
            sample_id = result.get('sample_id')
            if not sample_id:
                continue
            
            if result.get('passed', False):
                passed_ids.add(sample_id)
            else:
                failed_ids.add(sample_id)
        
        self.passed_ids = passed_ids
        
        logger.info(f"✅ 通过: {len(passed_ids)} 个唯一 ID")
        logger.info(f"❌ 失败: {len(failed_ids)} 个唯一 ID")
        
        return len(passed_ids), len(failed_ids)
    
    def filter_passed_only(self):
        """只保留通过测试的样本（不去重！）"""
        if self.passed_ids is None:
            logger.warning("⚠️  没有测试结果，跳过筛选")
            return
        
        before = len(self.samples)
        
        # 保留所有通过测试的样本（即使原 ID 相同）
        filtered_samples = {}
        idx = 0
        for key, sample in self.samples.items():
            sample_id = sample.get('id')
            if sample_id in self.passed_ids:
                filtered_samples[str(idx)] = sample
                idx += 1
        
        self.samples = filtered_samples
        after = len(self.samples)
        
        logger.info(f"🔍 筛选后: {after}/{before} 个样本（保留所有通过的实例）")
    
    def rebuild_ids(self):
        """重新分配 ID"""
        logger.info(f"🔧 开始重新分配 ID...")
        
        # 按分类分组
        groups = {}
        for key, sample in self.samples.items():
            class_info = sample.get('class', {})
            
            # 保存原始 ID
            original_id = sample.get('id', key)
            
            # 提取分类信息
            lang = class_info.get('lang', 'unknown')
            instruction_type = class_info.get('instruction_type', 'unknown')
            structure = class_info.get('structure', 'unknown')
            
            # 提取操作类型
            schema_list = sample.get('schema_list', [])
            if schema_list and len(schema_list) > 0:
                op = schema_list[0].get('op', 'unknown').lower()
            else:
                op = 'unknown'
            
            # 构建分组键
            group_key = f"{lang}-{instruction_type}-{structure}-{op}"
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append((original_id, sample))
        
        logger.info(f"   发现 {len(groups)} 个分组")
        
        # 为每个分组重新编号
        new_samples = {}
        
        for group_key, samples_list in sorted(groups.items()):
            for idx, (original_id, sample) in enumerate(samples_list, 1):
                # 生成新 ID
                new_id = f"t2m-{group_key}-{idx:03d}"
                
                # 更新 ID
                sample['id'] = new_id
                sample['_original_id'] = original_id  # 保留原 ID
                
                new_samples[new_id] = sample
            
            logger.info(f"   {group_key}: {len(samples_list)} 个样本 (重新编号为 {idx:03d})")
        
        self.samples = new_samples
        logger.info(f"✅ 重新分配了 {len(self.samples)} 个样本的 ID")
    
    def save(self, output_file: Path):
        """保存到 JSONL 文件"""
        logger.info(f"💾 保存到: {output_file}")
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 按新 ID 排序
        sorted_ids = sorted(self.samples.keys())
        
        with output_file.open('w', encoding='utf-8') as f:
            for sample_id in sorted_ids:
                sample = self.samples[sample_id]
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ 已保存 {len(self.samples)} 个样本")
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("📊 构建完成")
        print("="*60)
        print(f"总样本数: {len(self.samples)}")
        
        # 统计分类
        langs = Counter()
        types = Counter()
        structures = Counter()
        operations = Counter()
        
        for sample in self.samples.values():
            class_info = sample.get('class', {})
            langs[class_info.get('lang', 'unknown')] += 1
            types[class_info.get('instruction_type', 'unknown')] += 1
            structures[class_info.get('structure', 'unknown')] += 1
            
            schema_list = sample.get('schema_list', [])
            if schema_list:
                op = schema_list[0].get('op', 'unknown')
                operations[op] += 1
        
        print(f"\n按维度统计:")
        print(f"  语言: {dict(langs)}")
        print(f"  指令类型: {dict(types)}")
        print(f"  结构: {dict(structures)}")
        print(f"  操作: {dict(operations)}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="构建 Benchmark：去重 + 筛选 + 重新分配 ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 所有唯一样本，重新分配 ID
  python build_benchmark_final.py
  
  # 只保留通过测试的样本，重新分配 ID（推荐）
  python build_benchmark_final.py --passed-only
        """
    )
    
    parser.add_argument(
        '--stage3',
        type=Path,
        default=None,
        help='Stage3 输出文件（默认：自动查找最新）'
    )
    parser.add_argument(
        '--results',
        type=Path,
        default=None,
        help='测试结果文件（默认：自动查找最新）'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('bench/data/test_data/test_data.jsonl'),
        help='输出文件路径'
    )
    parser.add_argument(
        '--passed-only',
        action='store_true',
        help='只保留通过测试的样本'
    )
    
    args = parser.parse_args()
    
    builder = FinalBenchmarkBuilder()
    
    # 1. 加载并去重
    stage3_file = args.stage3 or builder.find_latest_stage3()
    if not stage3_file or not stage3_file.exists():
        logger.error("❌ 未找到 stage3 文件")
        return 1
    
    logger.info(f"✅ 使用 stage3 文件: {stage3_file}")
    builder.load_samples(stage3_file)
    
    # 2. 筛选（可选）
    if args.passed_only:
        results_file = args.results or builder.find_latest_results()
        if not results_file or not results_file.exists():
            logger.error("❌ 未找到测试结果文件")
            return 1
        
        logger.info(f"✅ 使用测试结果: {results_file}")
        builder.load_test_results(results_file)
        builder.filter_passed_only()
    
    # 3. 重新分配 ID
    builder.rebuild_ids()
    
    # 4. 保存
    builder.save(args.output)
    
    # 5. 统计
    builder.print_stats()
    
    print(f"\n📄 输出文件: {args.output}")
    print(f"✅ Benchmark 构建完成！")
    print(f"💡 所有样本都有唯一的新 ID（原 ID 保存在 _original_id 字段）")
    
    return 0


if __name__ == '__main__':
    exit(main())

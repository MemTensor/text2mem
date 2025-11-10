"""
Benchmark Builder - 构建器

整合生成、测试、清洗流程，一键生成 benchmark
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

from bench.core.benchmark_manager import BenchmarkManager, BenchmarkVersion

logger = logging.getLogger(__name__)


class BenchmarkBuilder:
    """Benchmark 构建器"""
    
    def __init__(
        self,
        config_file: Optional[Path] = None,
        version_id: Optional[str] = None,
        keep_raw: bool = True,
        manager: Optional[BenchmarkManager] = None,
    ):
        """
        Args:
            config_file: 生成配置文件路径
            version_id: 版本 ID（默认使用时间戳）
            keep_raw: 是否保留原始生成数据
            manager: BenchmarkManager 实例
        """
        self.config_file = Path(config_file) if config_file else Path('bench/generate/config/generation_plan.yaml')
        self.version_id = version_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.keep_raw = keep_raw
        self.manager = manager or BenchmarkManager()
        
        # 创建版本目录
        self.version = self.manager.create_version(self.version_id)
        
        # 临时目录（用于生成）
        self.temp_dir = Path(f'bench/data/.tmp_{self.version_id}')
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Benchmark Builder initialized: {self.version_id}")
        logger.info(f"Output directory: {self.version.version_dir}")
    
    def build(
        self,
        skip_generate: bool = False,
        from_raw: Optional[Path] = None,
        samples_override: Optional[int] = None,
    ) -> BenchmarkVersion:
        """
        完整构建流程
        
        Args:
            skip_generate: 跳过生成步骤
            from_raw: 从现有 raw 数据构建
            samples_override: 覆盖配置中的样本数量（用于快速测试）
        
        Returns:
            构建完成的 BenchmarkVersion
        """
        start_time = time.time()
        
        try:
            # 阶段 1: 生成数据
            if from_raw:
                logger.info("📦 使用现有 raw 数据")
                raw_dir = Path(from_raw)
                if not raw_dir.exists():
                    raise FileNotFoundError(f"Raw directory not found: {raw_dir}")
                stage3_file = raw_dir / "stage3.jsonl"
            elif skip_generate:
                logger.info("⏩ 跳过生成步骤")
                stage3_file = self.temp_dir / "stage3.jsonl"
            else:
                logger.info("🔄 阶段 1/4: 生成测试数据...")
                stage3_file = self._run_generation(samples_override)
            
            # 阶段 2: 运行测试
            logger.info("🔄 阶段 2/4: 运行测试...")
            test_results = self._run_tests(stage3_file)
            
            # 阶段 3: 清洗数据
            logger.info("🔄 阶段 3/4: 清洗数据...")
            cleaned_data, cleaning_report = self._clean_data(stage3_file, test_results)
            
            # 阶段 4: 构建 benchmark
            logger.info("🔄 阶段 4/4: 构建 benchmark...")
            self._build_benchmark(cleaned_data)
            
            # 保存元数据
            metadata = self._generate_metadata(test_results, cleaning_report)
            self.version.save_metadata(metadata)
            
            # 生成统计信息
            stats = self._generate_stats(cleaned_data)
            self.version.save_stats(stats)
            
            # 保存测试报告
            self._save_test_report(test_results)
            
            # 可选：保留 raw 数据
            if self.keep_raw and not from_raw:
                self._copy_raw_data(stage3_file.parent)
            
            # 更新 latest 符号链接
            self.manager.create_link(self.version_id, 'latest')
            
            # 清理临时文件
            self._cleanup()
            
            duration = time.time() - start_time
            
            # 打印摘要
            self._print_summary(metadata, duration)
            
            return self.version
            
        except Exception as e:
            logger.error(f"❌ 构建失败: {e}")
            # 清理失败的版本
            if self.version.version_dir.exists():
                shutil.rmtree(self.version.version_dir)
            self._cleanup()
            raise
    
    def _run_generation(self, samples_override: Optional[int] = None) -> Path:
        """运行生成流程"""
        # 导入生成器
        sys.path.insert(0, str(Path('bench/generate').resolve()))
        
        from bench.generate.src.generation_controller import main as generate_main
        
        # 临时修改配置（如果需要）
        config_backup = None
        if samples_override:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 备份原配置
            config_backup = config.copy()
            
            # 修改样本数
            config['plan']['total_samples'] = samples_override
            
            # 写入临时配置
            temp_config = self.temp_dir / 'generation_plan.yaml'
            with open(temp_config, 'w', encoding='utf-8') as f:
                yaml.dump(config, f)
            
            config_file_to_use = temp_config
        else:
            config_file_to_use = self.config_file
        
        # 运行生成（输出到临时目录）
        output_dir = self.temp_dir
        
        # 调用生成器（这里需要根据实际实现调整）
        # 暂时使用 subprocess 调用
        cmd = [
            sys.executable,
            'bench/generate/generate.py',
            '--config', str(config_file_to_use),
            '--output', str(output_dir),
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
        
        # 查找生成的 stage3.jsonl
        # 生成器应该输出到 output_dir/YYYYMMDD_HHMMSS/stage3.jsonl
        # 我们需要找到最新的输出目录
        stage3_file = output_dir / 'stage3.jsonl'
        
        if not stage3_file.exists():
            # 尝试在子目录中查找
            raw_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.replace('_', '').isdigit()]
            if raw_dirs:
                latest_raw = max(raw_dirs, key=lambda d: d.name)
                stage3_file = latest_raw / 'stage3.jsonl'
        
        if not stage3_file.exists():
            raise FileNotFoundError(f"Generated stage3.jsonl not found in {output_dir}")
        
        # 统计生成的样本数
        sample_count = sum(1 for _ in open(stage3_file, 'r', encoding='utf-8'))
        logger.info(f"✓ 生成完成: {sample_count} samples")
        
        return stage3_file
    
    def _run_tests(self, stage3_file: Path) -> Dict[str, Any]:
        """运行测试"""
        from bench.core.runner import BenchRunner, BenchConfig
        
        # 读取样本
        samples = []
        with open(stage3_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        
        # 创建测试配置
        config = BenchConfig(
            db_root=self.temp_dir / 'db',
            output_dir=self.temp_dir / 'output',
            mode='auto',
        )
        
        # 运行测试
        runner = BenchRunner(config)
        
        passed = []
        failed = []
        
        start_time = time.time()
        
        for i, sample in enumerate(samples, 1):
            sample_id = sample.get('id', f'sample_{i}')
            
            try:
                result = runner.run_sample(sample, sample_id)
                
                if result.passed:
                    passed.append({
                        'sample_id': sample_id,
                        'passed': True,
                    })
                else:
                    failed.append({
                        'sample_id': sample_id,
                        'passed': False,
                        'errors': result.errors,
                    })
                
                # 进度显示
                if i % 10 == 0 or i == len(samples):
                    logger.info(f"  进度: {i}/{len(samples)} ({i/len(samples)*100:.1f}%)")
            
            except Exception as e:
                logger.warning(f"  样本 {sample_id} 测试异常: {e}")
                failed.append({
                    'sample_id': sample_id,
                    'passed': False,
                    'errors': [str(e)],
                })
        
        duration = time.time() - start_time
        
        test_results = {
            'total_samples': len(samples),
            'passed': len(passed),
            'failed': len(failed),
            'pass_rate': len(passed) / len(samples) if samples else 0.0,
            'test_duration': duration,
            'passed_list': passed,
            'failed_list': failed,
        }
        
        logger.info(f"✓ 测试完成: {len(passed)}/{len(samples)} passed ({test_results['pass_rate']*100:.1f}%)")
        
        return test_results
    
    def _clean_data(
        self,
        stage3_file: Path,
        test_results: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """清洗数据"""
        # 读取所有样本
        samples = []
        with open(stage3_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        
        # 获取通过测试的样本 ID
        passed_ids = {item['sample_id'] for item in test_results['passed_list']}
        
        # 过滤规则
        ALLOWED_OPERATIONS = {
            'Encode', 'Retrieve', 'Update', 'Delete', 'Summarize', 'Label',
            'Promote', 'Demote', 'Expire', 'Lock', 'Merge', 'Split',
        }
        
        cleaned_samples = []
        filter_stats = {
            'total': len(samples),
            'passed_test': 0,
            'has_unknown': 0,
            'invalid_operation': 0,
            'final': 0,
        }
        
        for sample in samples:
            sample_id = sample.get('id', '')
            
            # 规则 1: 必须通过测试
            if sample_id not in passed_ids:
                continue
            filter_stats['passed_test'] += 1
            
            # 规则 2: 不包含 'unknown'
            sample_str = json.dumps(sample)
            if 'unknown' in sample_str.lower():
                filter_stats['has_unknown'] += 1
                continue
            
            # 规则 3: 操作必须在允许列表中
            schema_list = sample.get('schema_list', [])
            invalid_op = False
            for schema in schema_list:
                if schema.get('op') not in ALLOWED_OPERATIONS:
                    invalid_op = True
                    break
            
            if invalid_op:
                filter_stats['invalid_operation'] += 1
                continue
            
            # 通过所有过滤规则
            cleaned_samples.append(sample)
        
        filter_stats['final'] = len(cleaned_samples)
        
        cleaning_report = {
            'rules_applied': ['filter_failed', 'filter_unknown', 'filter_invalid_ops'],
            'samples_before': len(samples),
            'samples_after': len(cleaned_samples),
            'filter_stats': filter_stats,
        }
        
        logger.info(f"✓ 清洗完成: {len(cleaned_samples)} samples retained")
        
        return cleaned_samples, cleaning_report
    
    def _build_benchmark(self, cleaned_samples: List[Dict[str, Any]]) -> None:
        """构建最终 benchmark"""
        # 重新分配 ID
        id_counter = {}
        reassigned_samples = []
        
        for sample in cleaned_samples:
            # 提取分类信息
            class_info = sample.get('class', {})
            lang = class_info.get('lang', 'en')
            instruction = class_info.get('instruction', 'direct')
            structure = class_info.get('structure', 'single')
            
            # 获取操作类型
            schema_list = sample.get('schema_list', [])
            if schema_list:
                op = schema_list[0].get('op', 'unknown').lower()
            else:
                op = 'unknown'
            
            # 生成新 ID
            key = f"{lang}-{instruction}-{structure}-{op}"
            if key not in id_counter:
                id_counter[key] = 1
            else:
                id_counter[key] += 1
            
            new_id = f"t2m-{key}-{id_counter[key]:03d}"
            
            # 保存原 ID
            sample['_original_id'] = sample.get('id')
            sample['id'] = new_id
            
            reassigned_samples.append(sample)
        
        # 保存到 benchmark.jsonl
        with open(self.version.benchmark_file, 'w', encoding='utf-8') as f:
            for sample in reassigned_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"✓ Benchmark 已保存: {self.version.benchmark_file}")
    
    def _generate_metadata(
        self,
        test_results: Dict[str, Any],
        cleaning_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成元数据"""
        # 计算配置文件哈希
        config_hash = self._hash_file(self.config_file)
        
        # 读取配置信息
        import yaml
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        llm_config = config.get('llm', {})
        plan_config = config.get('plan', {})
        
        metadata = {
            'id': self.version_id,
            'created_at': datetime.now().isoformat(),
            'status': 'draft',  # 初始状态为 draft
            
            'generation': {
                'config_file': str(self.config_file),
                'config_hash': config_hash,
                'total_samples': plan_config.get('total_samples', 0),
                'llm_provider': llm_config.get('provider', 'unknown'),
                'llm_model': llm_config.get('model', 'unknown'),
            },
            
            'test_results': test_results,
            'cleaning': cleaning_report,
            
            'tags': [],
            'notes': '',
        }
        
        return metadata
    
    def _generate_stats(self, cleaned_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成统计信息"""
        from collections import Counter
        
        stats = {
            'total': len(cleaned_samples),
            'distribution': {
                'languages': {},
                'operations': {},
                'instruction_types': {},
                'structures': {},
            }
        }
        
        lang_counter = Counter()
        op_counter = Counter()
        instruction_counter = Counter()
        structure_counter = Counter()
        
        for sample in cleaned_samples:
            class_info = sample.get('class', {})
            lang_counter[class_info.get('lang', 'unknown')] += 1
            instruction_counter[class_info.get('instruction', 'unknown')] += 1
            structure_counter[class_info.get('structure', 'unknown')] += 1
            
            schema_list = sample.get('schema_list', [])
            for schema in schema_list:
                op_counter[schema.get('op', 'unknown')] += 1
        
        stats['distribution']['languages'] = dict(lang_counter)
        stats['distribution']['operations'] = dict(op_counter)
        stats['distribution']['instruction_types'] = dict(instruction_counter)
        stats['distribution']['structures'] = dict(structure_counter)
        
        return stats
    
    def _save_test_report(self, test_results: Dict[str, Any]) -> None:
        """保存测试报告"""
        with open(self.version.test_report_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    def _copy_raw_data(self, raw_dir: Path) -> None:
        """复制原始数据"""
        if raw_dir.exists():
            dest_raw_dir = self.version.raw_dir
            dest_raw_dir.mkdir(parents=True, exist_ok=True)
            
            for file in ['stage1.jsonl', 'stage2.jsonl', 'stage3.jsonl']:
                src = raw_dir / file
                if src.exists():
                    shutil.copy(src, dest_raw_dir / file)
            
            logger.info(f"✓ Raw 数据已保存到: {dest_raw_dir}")
    
    def _cleanup(self) -> None:
        """清理临时文件"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
    
    def _print_summary(self, metadata: Dict[str, Any], duration: float) -> None:
        """打印构建摘要"""
        test_results = metadata['test_results']
        
        print("\n" + "=" * 80)
        print("✅ Benchmark 构建完成！")
        print("=" * 80)
        print(f"\n📊 统计信息:")
        print(f"  生成: {metadata['generation']['total_samples']} samples")
        print(f"  测试: {test_results['passed']}/{test_results['total_samples']} passed "
              f"({test_results['pass_rate']*100:.1f}%)")
        print(f"  清洗: {metadata['cleaning']['samples_after']} samples retained")
        print(f"  耗时: {duration:.1f}s")
        
        print(f"\n📂 输出位置:")
        print(f"  Benchmark ID: {self.version_id}")
        print(f"  目录: {self.version.version_dir}")
        print(f"  文件: benchmark.jsonl ({metadata['cleaning']['samples_after']} samples)")
        
        print(f"\n🔗 符号链接:")
        print(f"  latest -> {self.version_id}")
        
        print(f"\n💡 下一步:")
        print(f"  # 验证 benchmark")
        print(f"  bench-cli test {self.version_id} --verbose")
        print(f"  ")
        print(f"  # 标记为稳定版本")
        print(f"  bench-cli link {self.version_id} stable")
        print()
    
    @staticmethod
    def _hash_file(file_path: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()[:16]

"""
Benchmark Builder

Integrates generation, testing, and cleaning processes to build benchmarks with one command
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
    """Benchmark Builder"""
    
    def __init__(
        self,
        config_file: Optional[Path] = None,
        version_id: Optional[str] = None,
        keep_raw: bool = True,
        manager: Optional[BenchmarkManager] = None,
    ):
        """
        Args:
            config_file: Generation configuration file path
            version_id: Version ID (defaults to timestamp)
            keep_raw: Whether to keep raw generation data
            manager: BenchmarkManager instance
        """
        self.config_file = Path(config_file) if config_file else Path('bench/generate/config/generation_plan.yaml')
        self.version_id = version_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.keep_raw = keep_raw
        self.manager = manager or BenchmarkManager()
        
        # Create version directory
        self.version = self.manager.create_version(self.version_id)
        
        # Temporary directory (for generation)
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
        Complete build process
        
        Args:
            skip_generate: Skip generation step
            from_raw: Build from existing raw data
            samples_override: Override sample count in configuration (for quick testing)
        
        Returns:
            Built BenchmarkVersion
        """
        start_time = time.time()
        
        try:
            # Stage 1: Generate data
            if from_raw:
                logger.info("📦 Using existing raw data")
                raw_dir = Path(from_raw)
                if not raw_dir.exists():
                    raise FileNotFoundError(f"Raw directory not found: {raw_dir}")
                stage3_file = raw_dir / "stage3.jsonl"
            elif skip_generate:
                logger.info("⏩ Skipping generation step")
                stage3_file = self.temp_dir / "stage3.jsonl"
            else:
                logger.info("🔄 Stage 1/4: Generating test data...")
                stage3_file = self._run_generation(samples_override)
            
            # Stage 2: Run tests
            logger.info("🔄 Stage 2/4: Running tests...")
            test_results = self._run_tests(stage3_file)
            
            # Stage 3: Clean data
            logger.info("🔄 Stage 3/4: Cleaning data...")
            cleaned_data, cleaning_report = self._clean_data(stage3_file, test_results)
            
            # Stage 4: Build benchmark
            logger.info("🔄 Stage 4/4: Building benchmark...")
            self._build_benchmark(cleaned_data)
            
            # Save metadata
            metadata = self._generate_metadata(test_results, cleaning_report)
            self.version.save_metadata(metadata)
            
            # Generate statistics
            stats = self._generate_stats(cleaned_data)
            self.version.save_stats(stats)
            
            # Save test report
            self._save_test_report(test_results)
            
            # Optional: Keep raw data
            if self.keep_raw and not from_raw:
                self._copy_raw_data(stage3_file.parent)
            
            # Update latest symbolic link
            self.manager.create_link(self.version_id, 'latest')
            
            # Clean temporary files
            self._cleanup()
            
            duration = time.time() - start_time
            
            # Print summary
            self._print_summary(metadata, duration)
            
            return self.version
            
        except Exception as e:
            logger.error(f"❌ Build failed: {e}")
            # Clean failed version
            if self.version.version_dir.exists():
                shutil.rmtree(self.version.version_dir)
            self._cleanup()
            raise
    
    def _run_generation(self, samples_override: Optional[int] = None) -> Path:
        """Run generation process"""
        # Import generator
        sys.path.insert(0, str(Path('bench/generate').resolve()))
        
        from bench.generate.src.generation_controller import main as generate_main
        
        # Temporarily modify configuration (if needed)
        config_backup = None
        if samples_override:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Backup original configuration
            config_backup = config.copy()
            
            # Modify sample count
            config['plan']['total_samples'] = samples_override
            
            # Write temporary configuration
            temp_config = self.temp_dir / 'generation_plan.yaml'
            with open(temp_config, 'w', encoding='utf-8') as f:
                yaml.dump(config, f)
            
            config_file_to_use = temp_config
        else:
            config_file_to_use = self.config_file
        
        # Run generation (output to temporary directory)
        output_dir = self.temp_dir
        
        # Call generator (adjust according to actual implementation)
        # Currently using subprocess
        cmd = [
            sys.executable,
            'bench/generate/generate.py',
            '--config', str(config_file_to_use),
            '--output', str(output_dir),
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
        
        # Find generated stage3.jsonl
        # Generator should output to output_dir/YYYYMMDD_HHMMSS/stage3.jsonl
        # We need to find the latest output directory
        stage3_file = output_dir / 'stage3.jsonl'
        
        if not stage3_file.exists():
            # Try to find in subdirectories
            raw_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.replace('_', '').isdigit()]
            if raw_dirs:
                latest_raw = max(raw_dirs, key=lambda d: d.name)
                stage3_file = latest_raw / 'stage3.jsonl'
        
        if not stage3_file.exists():
            raise FileNotFoundError(f"Generated stage3.jsonl not found in {output_dir}")
        
        # Count generated samples
        sample_count = sum(1 for _ in open(stage3_file, 'r', encoding='utf-8'))
        logger.info(f"✓ Generation complete: {sample_count} samples")
        
        return stage3_file
    
    def _run_tests(self, stage3_file: Path) -> Dict[str, Any]:
        """Run tests"""
        from bench.core.runner import BenchRunner, BenchConfig
        
        # Read samples
        samples = []
        with open(stage3_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        
        # Create test configuration
        config = BenchConfig(
            db_root=self.temp_dir / 'db',
            output_dir=self.temp_dir / 'output',
            mode='auto',
        )
        
        # Run tests
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
                
                # Progress display
                if i % 10 == 0 or i == len(samples):
                    logger.info(f"  Progress: {i}/{len(samples)} ({i/len(samples)*100:.1f}%)")
            
            except Exception as e:
                logger.warning(f"  Sample {sample_id} test exception: {e}")
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
        
        logger.info(f"✓ Testing complete: {len(passed)}/{len(samples)} passed ({test_results['pass_rate']*100:.1f}%)")
        
        return test_results
    
    def _clean_data(
        self,
        stage3_file: Path,
        test_results: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Clean data"""
        # Read all samples
        samples = []
        with open(stage3_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        
        # Get passed sample IDs
        passed_ids = {item['sample_id'] for item in test_results['passed_list']}
        
        # Filter rules
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
            
            # Rule 1: Must pass test
            if sample_id not in passed_ids:
                continue
            filter_stats['passed_test'] += 1
            
            # Rule 2: Should not contain 'unknown'
            sample_str = json.dumps(sample)
            if 'unknown' in sample_str.lower():
                filter_stats['has_unknown'] += 1
                continue
            
            # Rule 3: Operations must be in allowed list
            schema_list = sample.get('schema_list', [])
            invalid_op = False
            for schema in schema_list:
                if schema.get('op') not in ALLOWED_OPERATIONS:
                    invalid_op = True
                    break
            
            if invalid_op:
                filter_stats['invalid_operation'] += 1
                continue
            
            # Passed all filter rules
            cleaned_samples.append(sample)
        
        filter_stats['final'] = len(cleaned_samples)
        
        cleaning_report = {
            'rules_applied': ['filter_failed', 'filter_unknown', 'filter_invalid_ops'],
            'samples_before': len(samples),
            'samples_after': len(cleaned_samples),
            'filter_stats': filter_stats,
        }
        
        logger.info(f"✓ Cleaning complete: {len(cleaned_samples)} samples retained")
        
        return cleaned_samples, cleaning_report
    
    def _build_benchmark(self, cleaned_samples: List[Dict[str, Any]]) -> None:
        """Build final benchmark"""
        # Reassign IDs
        id_counter = {}
        reassigned_samples = []
        
        for sample in cleaned_samples:
            # Extract classification info
            class_info = sample.get('class', {})
            lang = class_info.get('lang', 'en')
            instruction = class_info.get('instruction', 'direct')
            structure = class_info.get('structure', 'single')
            
            # Get operation type
            schema_list = sample.get('schema_list', [])
            if schema_list:
                op = schema_list[0].get('op', 'unknown').lower()
            else:
                op = 'unknown'
            
            # Generate new ID
            key = f"{lang}-{instruction}-{structure}-{op}"
            if key not in id_counter:
                id_counter[key] = 1
            else:
                id_counter[key] += 1
            
            new_id = f"t2m-{key}-{id_counter[key]:03d}"
            
            # Save original ID
            sample['_original_id'] = sample.get('id')
            sample['id'] = new_id
            
            reassigned_samples.append(sample)
        
        # Save to benchmark.jsonl
        with open(self.version.benchmark_file, 'w', encoding='utf-8') as f:
            for sample in reassigned_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"✓ Benchmark saved: {self.version.benchmark_file}")
    
    def _generate_metadata(
        self,
        test_results: Dict[str, Any],
        cleaning_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate metadata"""
        # Calculate configuration file hash
        config_hash = self._hash_file(self.config_file)
        
        # Read configuration info
        import yaml
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        llm_config = config.get('llm', {})
        plan_config = config.get('plan', {})
        
        metadata = {
            'id': self.version_id,
            'created_at': datetime.now().isoformat(),
            'status': 'draft',  # Initial status is draft
            
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
        """Generate statistics"""
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
        """Save test report"""
        with open(self.version.test_report_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    def _copy_raw_data(self, raw_dir: Path) -> None:
        """Copy raw data"""
        if raw_dir.exists():
            dest_raw_dir = self.version.raw_dir
            dest_raw_dir.mkdir(parents=True, exist_ok=True)
            
            for file in ['stage1.jsonl', 'stage2.jsonl', 'stage3.jsonl']:
                src = raw_dir / file
                if src.exists():
                    shutil.copy(src, dest_raw_dir / file)
            
            logger.info(f"✓ Raw data saved to: {dest_raw_dir}")
    
    def _cleanup(self) -> None:
        """Clean temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
    
    def _print_summary(self, metadata: Dict[str, Any], duration: float) -> None:
        """Print build summary"""
        test_results = metadata['test_results']
        
        print("\n" + "=" * 80)
        print("✅ Benchmark build complete!")
        print("=" * 80)
        print(f"\n📊 Statistics:")
        print(f"  Generated: {metadata['generation']['total_samples']} samples")
        print(f"  Tested: {test_results['passed']}/{test_results['total_samples']} passed "
              f"({test_results['pass_rate']*100:.1f}%)")
        print(f"  Cleaned: {metadata['cleaning']['samples_after']} samples retained")
        print(f"  Duration: {duration:.1f}s")
        
        print(f"\n📂 Output location:")
        print(f"  Benchmark ID: {self.version_id}")
        print(f"  Directory: {self.version.version_dir}")
        print(f"  File: benchmark.jsonl ({metadata['cleaning']['samples_after']} samples)")
        
        print(f"\n🔗 Symbolic links:")
        print(f"  latest -> {self.version_id}")
        
        print(f"\n💡 Next steps:")
        print(f"  # Verify benchmark")
        print(f"  bench-cli test {self.version_id} --verbose")
        print(f"  ")
        print(f"  # Mark as stable version")
        print(f"  bench-cli link {self.version_id} stable")
        print()
    
    @staticmethod
    def _hash_file(file_path: Path) -> str:
        """Calculate file hash"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()[:16]

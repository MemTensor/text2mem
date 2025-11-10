"""
Simplified Test Runner

Runs benchmark tests and saves results
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from bench.core.simple_manager import Benchmark, ResultsManager, TestResult
from bench.core.runner import BenchRunner, BenchConfig

logger = logging.getLogger(__name__)


class SimpleTestRunner:
    """Simplified test runner for single benchmark"""
    
    def __init__(
        self,
        mode: str = 'auto',
        filter_expr: Optional[str] = None,
        schema_filter: Optional[List[str]] = None,
        schema_indices: Optional[List[int]] = None,
        timeout: Optional[float] = None,
    ):
        self.mode = mode
        self.filter_expr = filter_expr
        self.schema_filter = schema_filter
        self.schema_indices = schema_indices
        self.timeout = timeout
        
        self.benchmark = Benchmark()
        self.results_manager = ResultsManager()
    
    def run(self, result_id: Optional[str] = None, verbose: bool = False) -> TestResult:
        """
        Run benchmark tests
        
        Args:
            result_id: Result ID (default: timestamp)
            verbose: Print progress
        
        Returns:
            TestResult object
        """
        if verbose:
            print("=" * 80)
            print("🧪 Running Benchmark Tests")
            print("=" * 80)
            print()
        
        # Create result
        result = self.results_manager.create_result(result_id)
        
        if verbose:
            print(f"📂 Result ID: {result.result_id}")
            print(f"📊 Benchmark: {self.benchmark.sample_count} samples")
            print(f"🔧 Mode: {self.mode}")
            if self.filter_expr:
                print(f"🔍 Filter: {self.filter_expr}")
            if self.schema_filter:
                print(f"📋 Schema Filter: {', '.join(self.schema_filter)}")
            print()
        
        # Save config
        config = self._generate_config(result.result_id)
        result.save_config(config)
        
        # Load samples
        if verbose:
            print("📥 Loading benchmark samples...")
        
        samples = self.benchmark.load_samples()
        
        # Apply filters
        if self.filter_expr:
            samples = self._apply_filter(samples, self.filter_expr)
            if verbose:
                print(f"   Filtered to {len(samples)} samples")
        
        # Run tests
        if verbose:
            print(f"🏃 Running tests on {len(samples)} samples...")
            print()
        
        start_time = time.time()
        test_results = self._run_tests(samples, verbose)
        duration = time.time() - start_time
        
        # Generate report
        report = self._generate_report(test_results, samples, duration)
        result.save_report(report)
        
        # Save passed/failed lists
        passed_ids = [item['sample_id'] for item in test_results if item['passed']]
        failed_items = [item for item in test_results if not item['passed']]
        
        result.save_passed(passed_ids)
        result.save_failed(failed_items)
        
        # Update latest
        self.results_manager.update_latest(result.result_id)
        
        # Print summary
        if verbose:
            self._print_summary(report, result.result_id)
        
        return result
    
    def _generate_config(self, result_id: str) -> Dict[str, Any]:
        """Generate test configuration"""
        import sys
        import socket
        
        config = {
            'result_id': result_id,
            'benchmark_samples': self.benchmark.sample_count,
            'timestamp': datetime.now().isoformat(),
            
            'test_config': {
                'mode': self.mode,
                'filters': {
                    'filter_expr': self.filter_expr,
                    'schema_filter': self.schema_filter,
                    'schema_indices': self.schema_indices,
                },
                'timeout': self.timeout,
            },
            
            'environment': {
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'hostname': socket.gethostname(),
            }
        }
        
        return config
    
    def _apply_filter(self, samples: List[Dict], filter_expr: str) -> List[Dict]:
        """Apply filter expression to samples"""
        # Simple filter: lang:zh, op:Encode, etc.
        filtered = []
        
        for sample in samples:
            match = True
            
            # Parse filter (e.g., "lang:zh")
            if ':' in filter_expr:
                key, value = filter_expr.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'lang':
                    sample_lang = sample.get('class', {}).get('lang', '')
                    if sample_lang != value:
                        match = False
                
                elif key == 'op':
                    schema_list = sample.get('schema_list', [])
                    has_op = any(s.get('op') == value for s in schema_list)
                    if not has_op:
                        match = False
            
            if match:
                filtered.append(sample)
        
        return filtered
    
    def _run_tests(self, samples: List[Dict], verbose: bool) -> List[Dict]:
        """Run tests on samples"""
        from bench.core.runner import BenchConfig, BenchRunner
        
        # Create temp dir for test
        temp_dir = Path(f'bench/data/.tmp_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create test config
            config = BenchConfig(
                db_root=temp_dir / 'db',
                output_dir=temp_dir / 'output',
                mode=self.mode,
                timeout=self.timeout,
                schema_filter=self.schema_filter,
                schema_indices=self.schema_indices,
            )
            
            # Run tests
            runner = BenchRunner(config)
            
            results = []
            for i, sample in enumerate(samples, 1):
                sample_id = sample.get('id', f'sample_{i}')
                
                try:
                    result = runner.run_sample(sample, sample_id)
                    
                    results.append({
                        'sample_id': sample_id,
                        'passed': result.passed,
                        'errors': result.errors if not result.passed else [],
                    })
                    
                    if verbose and i % 10 == 0:
                        passed_count = sum(1 for r in results if r['passed'])
                        print(f"  Progress: {i}/{len(samples)} ({passed_count} passed)")
                
                except Exception as e:
                    logger.warning(f"Sample {sample_id} failed: {e}")
                    results.append({
                        'sample_id': sample_id,
                        'passed': False,
                        'errors': [str(e)],
                    })
            
            return results
        
        finally:
            # Cleanup
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _generate_report(
        self,
        test_results: List[Dict],
        samples: List[Dict],
        duration: float
    ) -> Dict[str, Any]:
        """Generate test report"""
        total = len(test_results)
        passed = sum(1 for r in test_results if r['passed'])
        failed = total - passed
        
        report = {
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': passed / total if total > 0 else 0.0,
                'duration_seconds': duration,
            }
        }
        
        # By operation
        op_stats = Counter()
        op_passed = Counter()
        
        for i, result in enumerate(test_results):
            if i < len(samples):
                sample = samples[i]
                schema_list = sample.get('schema_list', [])
                for schema in schema_list:
                    op = schema.get('op', 'unknown')
                    op_stats[op] += 1
                    if result['passed']:
                        op_passed[op] += 1
        
        by_operation = {}
        for op in op_stats:
            total_op = op_stats[op]
            passed_op = op_passed[op]
            by_operation[op] = {
                'total': total_op,
                'passed': passed_op,
                'failed': total_op - passed_op,
                'pass_rate': passed_op / total_op if total_op > 0 else 0.0,
            }
        
        report['by_operation'] = by_operation
        
        # By language
        lang_stats = Counter()
        lang_passed = Counter()
        
        for i, result in enumerate(test_results):
            if i < len(samples):
                sample = samples[i]
                lang = sample.get('class', {}).get('lang', 'unknown')
                lang_stats[lang] += 1
                if result['passed']:
                    lang_passed[lang] += 1
        
        by_language = {}
        for lang in lang_stats:
            total_lang = lang_stats[lang]
            passed_lang = lang_passed[lang]
            by_language[lang] = {
                'total': total_lang,
                'passed': passed_lang,
                'failed': total_lang - passed_lang,
                'pass_rate': passed_lang / total_lang if total_lang > 0 else 0.0,
            }
        
        report['by_language'] = by_language
        
        return report
    
    def _print_summary(self, report: Dict[str, Any], result_id: str) -> None:
        """Print test summary"""
        summary = report['summary']
        
        print()
        print("=" * 80)
        print("✅ Test Completed")
        print("=" * 80)
        print()
        print(f"📊 Summary:")
        print(f"  Total: {summary['total']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Pass Rate: {summary['pass_rate']*100:.1f}%")
        print(f"  Duration: {summary['duration_seconds']:.1f}s")
        print()
        print(f"📂 Results saved to: bench/data/results/{result_id}/")
        print()
        print("💡 Next steps:")
        print(f"  bench-cli show-result {result_id}  # View detailed results")
        print(f"  bench-cli compare <id1> <id2>      # Compare with another run")
        print()

"""
Simplified Benchmark System

Core components:
- Single benchmark (bench/data/benchmark/)
- Multiple test results (bench/data/results/)
- Generation workspace (bench/data/generation/)
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class Benchmark:
    """Single benchmark manager"""
    
    def __init__(self, data_root: Optional[Path] = None):
        if data_root is None:
            data_root = Path('bench/data')
        
        self.data_root = Path(data_root)
        self.benchmark_dir = self.data_root / 'benchmark'
        self.benchmark_file = self.benchmark_dir / 'benchmark.jsonl'
        self.metadata_file = self.benchmark_dir / 'metadata.json'
        self.stats_file = self.benchmark_dir / 'stats.json'
        
        if not self.benchmark_dir.exists():
            raise FileNotFoundError(
                f"Benchmark not found at {self.benchmark_dir}. "
                "Please run migration first."
            )
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Load benchmark metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Load benchmark statistics"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @property
    def sample_count(self) -> int:
        """Get total sample count"""
        return self.metadata.get('total_samples', 0)
    
    def load_samples(self) -> List[Dict[str, Any]]:
        """Load all benchmark samples"""
        samples = []
        with open(self.benchmark_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        return samples
    
    def info(self) -> str:
        """Get benchmark info as formatted string"""
        meta = self.metadata
        stats = self.stats
        
        lines = [
            "=" * 80,
            "📊 Benchmark Information",
            "=" * 80,
            "",
            f"Total Samples: {meta.get('total_samples', 0)}",
            f"Created: {meta.get('created_at', 'unknown')}",
            f"Last Updated: {meta.get('last_updated', 'unknown')}",
        ]
        
        if stats:
            dist = stats.get('distribution', {})
            lines.append("")
            lines.append("📈 Distribution:")
            
            if 'languages' in dist:
                langs = ', '.join(f"{k}: {v}" for k, v in dist['languages'].items())
                lines.append(f"  Languages: {langs}")
            
            if 'operations' in dist:
                ops = dist['operations']
                top_ops = sorted(ops.items(), key=lambda x: x[1], reverse=True)[:5]
                ops_str = ', '.join(f"{k}: {v}" for k, v in top_ops)
                lines.append(f"  Operations (Top 5): {ops_str}")
            
            if 'structures' in dist:
                structs = ', '.join(f"{k}: {v}" for k, v in dist['structures'].items())
                lines.append(f"  Structures: {structs}")
        
        notes = meta.get('notes', '')
        if notes:
            lines.append("")
            lines.append(f"📝 Notes: {notes}")
        
        lines.append("")
        return '\n'.join(lines)


class TestResult:
    """Single test result"""
    
    def __init__(self, result_dir: Path):
        self.result_dir = Path(result_dir)
        self.result_id = self.result_dir.name
        self.config_file = self.result_dir / 'config.json'
        self.report_file = self.result_dir / 'report.json'
        self.passed_file = self.result_dir / 'passed.jsonl'
        self.failed_file = self.result_dir / 'failed.jsonl'
    
    @property
    def exists(self) -> bool:
        return self.result_dir.exists()
    
    @property
    def config(self) -> Dict[str, Any]:
        """Load test configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @property
    def report(self) -> Dict[str, Any]:
        """Load test report"""
        if self.report_file.exists():
            with open(self.report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @property
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return self.report.get('summary', {})
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save test configuration"""
        self.result_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def save_report(self, report: Dict[str, Any]) -> None:
        """Save test report"""
        self.result_dir.mkdir(parents=True, exist_ok=True)
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def save_passed(self, passed_ids: List[str]) -> None:
        """Save passed sample IDs"""
        with open(self.passed_file, 'w', encoding='utf-8') as f:
            for sample_id in passed_ids:
                f.write(json.dumps({"sample_id": sample_id}) + '\n')
    
    def save_failed(self, failed_items: List[Dict[str, Any]]) -> None:
        """Save failed samples with errors"""
        with open(self.failed_file, 'w', encoding='utf-8') as f:
            for item in failed_items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')


class ResultsManager:
    """Manager for test results"""
    
    def __init__(self, data_root: Optional[Path] = None):
        if data_root is None:
            data_root = Path('bench/data')
        
        self.data_root = Path(data_root)
        self.results_dir = self.data_root / 'results'
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def list_results(self, limit: Optional[int] = None) -> List[TestResult]:
        """List all test results"""
        results = []
        
        for item in self.results_dir.iterdir():
            if item.is_dir() and not item.is_symlink():
                # Check if it's a valid result ID (timestamp format)
                if self._is_valid_result_id(item.name):
                    results.append(TestResult(item))
        
        # Sort by ID (timestamp) descending
        results.sort(key=lambda r: r.result_id, reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_result(self, result_id: str) -> TestResult:
        """Get specific test result"""
        # Handle 'latest' alias
        if result_id == 'latest':
            latest_link = self.results_dir / 'latest'
            if latest_link.is_symlink():
                target = latest_link.resolve()
                return TestResult(target)
            else:
                # Return most recent result
                results = self.list_results(limit=1)
                if results:
                    return results[0]
                raise FileNotFoundError("No test results found")
        
        result_path = self.results_dir / result_id
        if not result_path.exists():
            raise FileNotFoundError(f"Test result not found: {result_id}")
        
        return TestResult(result_path)
    
    def create_result(self, result_id: Optional[str] = None) -> TestResult:
        """Create new test result"""
        if result_id is None:
            result_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        result_path = self.results_dir / result_id
        result_path.mkdir(parents=True, exist_ok=True)
        
        return TestResult(result_path)
    
    def update_latest(self, result_id: str) -> None:
        """Update 'latest' symlink"""
        latest_link = self.results_dir / 'latest'
        
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        latest_link.symlink_to(result_id)
        logger.info(f"Updated latest -> {result_id}")
    
    @staticmethod
    def _is_valid_result_id(result_id: str) -> bool:
        """Check if result ID is valid timestamp format"""
        if len(result_id) != 15:  # YYYYMMDD_HHMMSS
            return False
        parts = result_id.split('_')
        if len(parts) != 2:
            return False
        date_part, time_part = parts
        return (len(date_part) == 8 and date_part.isdigit() and
                len(time_part) == 6 and time_part.isdigit())

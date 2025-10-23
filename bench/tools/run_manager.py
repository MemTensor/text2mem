"""
Run管理模块 v3.0

支持新的数据结构：
- raw/: 原始生成输出
- runs/: 测试和清洗后的数据
- benchmarks/: 最终benchmark
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json


class RunManager:
    """Run目录管理器"""
    
    def __init__(self, data_root: Path = None):
        """
        Args:
            data_root: 数据根目录，默认为 bench/data
        """
        if data_root is None:
            data_root = Path('bench/data')
        
        self.data_root = Path(data_root)
        self.raw_dir = self.data_root / 'raw'
        self.runs_dir = self.data_root / 'runs'
        self.benchmarks_dir = self.data_root / 'benchmarks'
        
        # 确保目录存在
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== Raw 相关方法 ====================
    
    def get_raw_dir(self, raw_id: str) -> Path:
        """获取raw目录
        
        Args:
            raw_id: raw标识符，可以是:
                - 时间戳 (如 "20251022_143000")
                - "latest" (最新的raw)
        
        Returns:
            Raw目录路径
        
        Raises:
            FileNotFoundError: 如果raw不存在
        """
        if raw_id == 'latest':
            latest_raw = self.get_latest_raw()
            if not latest_raw:
                raise FileNotFoundError("没有找到任何raw数据")
            return self.raw_dir / latest_raw
        else:
            raw_path = self.raw_dir / raw_id
            if not raw_path.exists():
                raise FileNotFoundError(f"Raw不存在: {raw_id}")
            return raw_path
    
    def list_raws(self, limit: Optional[int] = None) -> List[str]:
        """列出所有raws
        
        Args:
            limit: 限制返回数量（按时间倒序）
        
        Returns:
            Raw ID列表
        """
        raws = []
        for item in self.raw_dir.iterdir():
            if item.is_dir() and item.name.replace('_', '').isdigit():
                raws.append(item.name)
        
        # 按时间戳倒序排序
        raws.sort(reverse=True)
        
        if limit:
            raws = raws[:limit]
        
        return raws
    
    def get_latest_raw(self) -> Optional[str]:
        """获取最新的raw ID"""
        raws = self.list_raws(limit=1)
        return raws[0] if raws else None
    
    def get_stage_file_from_raw(self, raw_id: str, stage: int) -> Path:
        """从raw获取stage文件
        
        Args:
            raw_id: Raw ID
            stage: Stage编号 (1, 2, 3)
        
        Returns:
            Stage文件路径
        """
        raw_path = self.get_raw_dir(raw_id)
        return raw_path / f'stage{stage}.jsonl'
    
    # ==================== Run 相关方法 ====================
    
    def get_run_dir(self, run_id: str) -> Path:
        """获取run目录
        
        Args:
            run_id: run标识符，可以是:
                - 时间戳 (如 "20251022_143000")
                - "latest" (最新的run)
        
        Returns:
            Run目录路径
        
        Raises:
            FileNotFoundError: 如果run不存在
        """
        if run_id == 'latest':
            latest_link = self.runs_dir / 'latest'
            if not latest_link.exists():
                raise FileNotFoundError("没有找到latest run")
            return latest_link.resolve()
        else:
            run_dir = self.runs_dir / run_id
            if not run_dir.exists():
                raise FileNotFoundError(f"Run不存在: {run_id}")
            return run_dir
    
    def list_runs(self, limit: Optional[int] = None) -> List[str]:
        """列出所有runs
        
        Args:
            limit: 限制返回数量（按时间倒序）
        
        Returns:
            Run ID列表
        """
        runs = []
        for item in self.runs_dir.iterdir():
            if item.is_dir() and item.name != 'latest' and item.name.replace('_', '').isdigit():
                runs.append(item.name)
        
        # 按时间戳倒序排序
        runs.sort(reverse=True)
        
        if limit:
            runs = runs[:limit]
        
        return runs
    
    def get_latest_run(self) -> Optional[str]:
        """获取最新的run ID"""
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None
    
    def create_run_from_raw(self, raw_id: str, run_id: Optional[str] = None) -> Path:
        """从raw创建run目录
        
        Args:
            raw_id: Raw ID
            run_id: Run ID，如果为None则使用raw_id
        
        Returns:
            Run目录路径
        """
        # 验证raw存在
        raw_dir = self.get_raw_dir(raw_id)
        
        if run_id is None:
            run_id = raw_id
        
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建source.json记录来源
        source_info = {
            'raw_id': raw_id,
            'raw_dir': str(raw_dir),
            'created_at': datetime.now().isoformat(),
        }
        
        with (run_dir / 'source.json').open('w', encoding='utf-8') as f:
            json.dump(source_info, f, indent=2, ensure_ascii=False)
        
        # 更新latest链接
        self.update_latest_run(run_id)
        
        return run_dir
    
    def update_latest_run(self, run_id: str):
        """更新run的latest链接"""
        latest_link = self.runs_dir / 'latest'
        
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        latest_link.symlink_to(run_id)
    
    def get_tests_dir(self, run_id: str) -> Path:
        """获取测试结果目录"""
        run_dir = self.get_run_dir(run_id)
        tests_dir = run_dir / 'tests'
        tests_dir.mkdir(exist_ok=True)
        return tests_dir
    
    def get_cleaned_dir(self, run_id: str) -> Path:
        """获取清洗数据目录"""
        run_dir = self.get_run_dir(run_id)
        cleaned_dir = run_dir / 'cleaned'
        cleaned_dir.mkdir(exist_ok=True)
        return cleaned_dir
    
    def has_tests(self, run_id: str) -> bool:
        """检查是否有测试结果"""
        try:
            run_dir = self.get_run_dir(run_id)
            tests_dir = run_dir / 'tests'
            return tests_dir.exists() and (tests_dir / 'summary.json').exists()
        except FileNotFoundError:
            return False
    
    def has_cleaned(self, run_id: str) -> bool:
        """检查是否有清洗数据"""
        try:
            run_dir = self.get_run_dir(run_id)
            cleaned_dir = run_dir / 'cleaned'
            return cleaned_dir.exists() and (cleaned_dir / 'cleaned.jsonl').exists()
        except FileNotFoundError:
            return False
    
    def get_run_status(self, run_id: str) -> dict:
        """获取run的完成状态"""
        return {
            'run_id': run_id,
            'has_tests': self.has_tests(run_id),
            'has_cleaned': self.has_cleaned(run_id),
        }
    
    def get_source_raw(self, run_id: str) -> Optional[str]:
        """获取run对应的raw ID"""
        try:
            run_dir = self.get_run_dir(run_id)
            source_file = run_dir / 'source.json'
            if source_file.exists():
                with source_file.open('r', encoding='utf-8') as f:
                    source = json.load(f)
                return source.get('raw_id')
        except:
            pass
        return None
    
    # ==================== Benchmark 相关方法 ====================
    
    def get_benchmark_dir(self, version: str) -> Path:
        """获取benchmark版本目录
        
        Args:
            version: Benchmark版本号 (如 "v1", "v2")
        
        Returns:
            Benchmark目录路径
        """
        bm_dir = self.benchmarks_dir / version
        bm_dir.mkdir(parents=True, exist_ok=True)
        return bm_dir
    
    def list_benchmarks(self) -> List[str]:
        """列出所有benchmark版本"""
        versions = []
        for item in self.benchmarks_dir.iterdir():
            if item.is_dir() and item.name != 'latest':
                versions.append(item.name)
        
        # 排序
        versions.sort()
        return versions
    
    def update_benchmark_latest(self, version: str):
        """更新benchmark的latest链接"""
        latest_link = self.benchmarks_dir / 'latest'
        
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        latest_link.symlink_to(version)


def find_latest_raw() -> Optional[str]:
    """便捷函数：查找最新的raw"""
    manager = RunManager()
    return manager.get_latest_raw()


def find_latest_run() -> Optional[str]:
    """便捷函数：查找最新的run"""
    manager = RunManager()
    return manager.get_latest_run()


def get_raw_path(raw_id: str = 'latest') -> Path:
    """便捷函数：获取raw路径"""
    manager = RunManager()
    return manager.get_raw_dir(raw_id)


def get_run_path(run_id: str = 'latest') -> Path:
    """便捷函数：获取run路径"""
    manager = RunManager()
    return manager.get_run_dir(run_id)

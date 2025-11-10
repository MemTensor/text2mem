"""
Benchmark Manager - 管理所有 benchmark 版本

功能：
- 列出、查询、创建 benchmark 版本
- 管理符号链接 (latest, stable, dev)
- 提供统一的版本访问接口
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BenchmarkVersion:
    """单个 Benchmark 版本"""
    
    def __init__(self, version_dir: Path):
        self.version_dir = Path(version_dir)
        self.id = self.version_dir.name
        self._metadata: Optional[Dict[str, Any]] = None
        self._stats: Optional[Dict[str, Any]] = None
    
    @property
    def metadata_file(self) -> Path:
        return self.version_dir / "metadata.json"
    
    @property
    def benchmark_file(self) -> Path:
        return self.version_dir / "benchmark.jsonl"
    
    @property
    def stats_file(self) -> Path:
        return self.version_dir / "stats.json"
    
    @property
    def test_report_file(self) -> Path:
        return self.version_dir / "test_report.json"
    
    @property
    def raw_dir(self) -> Path:
        return self.version_dir / "raw"
    
    @property
    def exists(self) -> bool:
        return self.version_dir.exists()
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        if self._metadata is None:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
            else:
                self._metadata = {}
        return self._metadata
    
    @property
    def stats(self) -> Dict[str, Any]:
        """加载统计信息"""
        if self._stats is None:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self._stats = json.load(f)
            else:
                self._stats = {}
        return self._stats
    
    @property
    def status(self) -> str:
        """获取状态"""
        return self.metadata.get('status', 'unknown')
    
    @property
    def created_at(self) -> Optional[str]:
        """获取创建时间"""
        return self.metadata.get('created_at')
    
    @property
    def sample_count(self) -> int:
        """获取样本数"""
        test_results = self.metadata.get('test_results', {})
        return test_results.get('passed', 0)
    
    @property
    def pass_rate(self) -> float:
        """获取通过率"""
        test_results = self.metadata.get('test_results', {})
        total = test_results.get('total_samples', 0)
        passed = test_results.get('passed', 0)
        return passed / total if total > 0 else 0.0
    
    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """保存元数据"""
        self.version_dir.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        self._metadata = metadata
    
    def save_stats(self, stats: Dict[str, Any]) -> None:
        """保存统计信息"""
        self.version_dir.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        self._stats = stats
    
    def __repr__(self) -> str:
        return f"BenchmarkVersion(id={self.id}, status={self.status}, samples={self.sample_count})"


class BenchmarkManager:
    """Benchmark 管理器"""
    
    def __init__(self, data_root: Optional[Path] = None):
        """
        Args:
            data_root: 数据根目录，默认为 bench/data
        """
        if data_root is None:
            data_root = Path('bench/data')
        
        self.data_root = Path(data_root)
        self.benchmarks_dir = self.data_root / 'benchmarks'
        self.archive_dir = self.data_root / 'archive'
        
        # 确保目录存在
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def list_versions(self, include_archived: bool = False) -> List[BenchmarkVersion]:
        """
        列出所有版本
        
        Args:
            include_archived: 是否包含归档版本
        
        Returns:
            版本列表，按时间倒序排序
        """
        versions = []
        
        # 扫描 benchmarks 目录
        for item in self.benchmarks_dir.iterdir():
            if item.is_dir() and not item.is_symlink():
                # 检查是否是有效的版本 ID (YYYYMMDD_HHMMSS)
                if self._is_valid_version_id(item.name):
                    versions.append(BenchmarkVersion(item))
        
        # 扫描 archive 目录
        if include_archived:
            for item in self.archive_dir.iterdir():
                if item.is_dir() and self._is_valid_version_id(item.name):
                    versions.append(BenchmarkVersion(item))
        
        # 按版本 ID（时间戳）倒序排序
        versions.sort(key=lambda v: v.id, reverse=True)
        
        return versions
    
    def get_version(self, version_id: str) -> BenchmarkVersion:
        """
        获取指定版本
        
        Args:
            version_id: 版本 ID，可以是：
                - 时间戳 (如 "20251110_120000")
                - 符号链接名称 (如 "latest", "stable", "dev")
        
        Returns:
            BenchmarkVersion 对象
        
        Raises:
            FileNotFoundError: 如果版本不存在
        """
        # 检查是否是符号链接
        link_path = self.benchmarks_dir / version_id
        if link_path.is_symlink():
            target = link_path.resolve()
            return BenchmarkVersion(target)
        
        # 检查 benchmarks 目录
        version_path = self.benchmarks_dir / version_id
        if version_path.exists():
            return BenchmarkVersion(version_path)
        
        # 检查 archive 目录
        archive_path = self.archive_dir / version_id
        if archive_path.exists():
            return BenchmarkVersion(archive_path)
        
        raise FileNotFoundError(f"Benchmark version not found: {version_id}")
    
    def get_latest(self) -> Optional[BenchmarkVersion]:
        """获取最新版本（通过 latest 符号链接或最新时间戳）"""
        try:
            return self.get_version('latest')
        except FileNotFoundError:
            # 如果 latest 链接不存在，返回最新的版本
            versions = self.list_versions()
            return versions[0] if versions else None
    
    def create_version(self, version_id: Optional[str] = None) -> BenchmarkVersion:
        """
        创建新版本
        
        Args:
            version_id: 版本 ID，默认使用当前时间戳
        
        Returns:
            新创建的 BenchmarkVersion 对象
        """
        if version_id is None:
            version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        version_path = self.benchmarks_dir / version_id
        version_path.mkdir(parents=True, exist_ok=True)
        
        return BenchmarkVersion(version_path)
    
    def create_link(self, version_id: str, link_name: str) -> None:
        """
        创建符号链接
        
        Args:
            version_id: 目标版本 ID
            link_name: 链接名称（如 "latest", "stable", "dev"）
        """
        # 验证目标版本存在
        version = self.get_version(version_id)
        if not version.exists:
            raise FileNotFoundError(f"Target version not found: {version_id}")
        
        link_path = self.benchmarks_dir / link_name
        
        # 删除现有链接
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        
        # 创建新链接（相对路径）
        link_path.symlink_to(version_id)
        logger.info(f"Created symlink: {link_name} -> {version_id}")
    
    def remove_link(self, link_name: str) -> None:
        """删除符号链接"""
        link_path = self.benchmarks_dir / link_name
        if link_path.is_symlink():
            link_path.unlink()
            logger.info(f"Removed symlink: {link_name}")
        else:
            logger.warning(f"Link does not exist: {link_name}")
    
    def archive_version(self, version_id: str) -> None:
        """
        归档版本（移动到 archive 目录）
        
        Args:
            version_id: 要归档的版本 ID
        """
        version = self.get_version(version_id)
        if not version.exists:
            raise FileNotFoundError(f"Version not found: {version_id}")
        
        # 不能归档符号链接指向的版本
        for link_name in ['latest', 'stable', 'dev']:
            try:
                link_version = self.get_version(link_name)
                if link_version.id == version_id:
                    raise ValueError(
                        f"Cannot archive version {version_id} because it is "
                        f"referenced by symlink '{link_name}'"
                    )
            except FileNotFoundError:
                pass
        
        # 移动到 archive
        archive_path = self.archive_dir / version_id
        shutil.move(str(version.version_dir), str(archive_path))
        
        # 更新元数据状态
        archived_version = BenchmarkVersion(archive_path)
        metadata = archived_version.metadata
        metadata['status'] = 'archived'
        metadata['archived_at'] = datetime.now().isoformat()
        archived_version.save_metadata(metadata)
        
        logger.info(f"Archived version: {version_id}")
    
    def delete_version(self, version_id: str, force: bool = False) -> None:
        """
        删除版本
        
        Args:
            version_id: 要删除的版本 ID
            force: 强制删除（即使被符号链接引用）
        """
        version = self.get_version(version_id)
        if not version.exists:
            raise FileNotFoundError(f"Version not found: {version_id}")
        
        # 检查是否被符号链接引用
        if not force:
            for link_name in ['latest', 'stable', 'dev']:
                try:
                    link_version = self.get_version(link_name)
                    if link_version.id == version_id:
                        raise ValueError(
                            f"Cannot delete version {version_id} because it is "
                            f"referenced by symlink '{link_name}'. Use --force to override."
                        )
                except FileNotFoundError:
                    pass
        
        # 删除目录
        shutil.rmtree(version.version_dir)
        logger.info(f"Deleted version: {version_id}")
    
    def get_aliases(self) -> Dict[str, str]:
        """
        获取所有符号链接别名
        
        Returns:
            {link_name: version_id} 映射
        """
        aliases = {}
        for item in self.benchmarks_dir.iterdir():
            if item.is_symlink():
                target = item.resolve()
                aliases[item.name] = target.name
        return aliases
    
    @staticmethod
    def _is_valid_version_id(version_id: str) -> bool:
        """检查是否是有效的版本 ID (YYYYMMDD_HHMMSS 格式)"""
        if len(version_id) != 15:  # YYYYMMDD_HHMMSS
            return False
        parts = version_id.split('_')
        if len(parts) != 2:
            return False
        date_part, time_part = parts
        return (len(date_part) == 8 and date_part.isdigit() and
                len(time_part) == 6 and time_part.isdigit())

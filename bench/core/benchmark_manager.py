"""
Benchmark Manager - Manage all benchmark versions

Features:
- List, query, create benchmark versions
- Manage symbolic links (latest, stable, dev)
- Provide unified version access interface
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
    """Single Benchmark version"""
    
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
        """Load metadata"""
        if self._metadata is None:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
            else:
                self._metadata = {}
        return self._metadata
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Load statistics"""
        if self._stats is None:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self._stats = json.load(f)
            else:
                self._stats = {}
        return self._stats
    
    @property
    def status(self) -> str:
        """Get status"""
        return self.metadata.get('status', 'unknown')
    
    @property
    def created_at(self) -> Optional[str]:
        """Get creation time"""
        return self.metadata.get('created_at')
    
    @property
    def sample_count(self) -> int:
        """Get sample count"""
        test_results = self.metadata.get('test_results', {})
        return test_results.get('passed', 0)
    
    @property
    def pass_rate(self) -> float:
        """Get pass rate"""
        test_results = self.metadata.get('test_results', {})
        total = test_results.get('total_samples', 0)
        passed = test_results.get('passed', 0)
        return passed / total if total > 0 else 0.0
    
    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save metadata"""
        self.version_dir.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        self._metadata = metadata
    
    def save_stats(self, stats: Dict[str, Any]) -> None:
        """Save statistics"""
        self.version_dir.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        self._stats = stats
    
    def __repr__(self) -> str:
        return f"BenchmarkVersion(id={self.id}, status={self.status}, samples={self.sample_count})"


class BenchmarkManager:
    """Benchmark Manager"""
    
    def __init__(self, data_root: Optional[Path] = None):
        """
        Args:
            data_root: Data root directory, defaults to bench/data
        """
        if data_root is None:
            data_root = Path('bench/data')
        
        self.data_root = Path(data_root)
        self.benchmarks_dir = self.data_root / 'benchmarks'
        self.archive_dir = self.data_root / 'archive'
        
        # Ensure directories exist
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def list_versions(self, include_archived: bool = False) -> List[BenchmarkVersion]:
        """
        List all versions
        
        Args:
            include_archived: Whether to include archived versions
        
        Returns:
            List of versions, sorted by time in descending order
        """
        versions = []
        
        # Scan benchmarks directory
        for item in self.benchmarks_dir.iterdir():
            if item.is_dir() and not item.is_symlink():
                # Check if it's a valid version ID (YYYYMMDD_HHMMSS)
                if self._is_valid_version_id(item.name):
                    versions.append(BenchmarkVersion(item))
        
        # Scan archive directory
        if include_archived:
            for item in self.archive_dir.iterdir():
                if item.is_dir() and self._is_valid_version_id(item.name):
                    versions.append(BenchmarkVersion(item))
        
        # Sort by version ID (timestamp) in descending order
        versions.sort(key=lambda v: v.id, reverse=True)
        
        return versions
    
    def get_version(self, version_id: str) -> BenchmarkVersion:
        """
        Get specified version
        
        Args:
            version_id: Version ID, can be:
                - Timestamp (e.g. "20251110_120000")
                - Symbolic link name (e.g. "latest", "stable", "dev")
        
        Returns:
            BenchmarkVersion object
        
        Raises:
            FileNotFoundError: If version does not exist
        """
        # Check if it's a symbolic link
        link_path = self.benchmarks_dir / version_id
        if link_path.is_symlink():
            target = link_path.resolve()
            return BenchmarkVersion(target)
        
        # Check benchmarks directory
        version_path = self.benchmarks_dir / version_id
        if version_path.exists():
            return BenchmarkVersion(version_path)
        
        # Check archive directory
        archive_path = self.archive_dir / version_id
        if archive_path.exists():
            return BenchmarkVersion(archive_path)
        
        raise FileNotFoundError(f"Benchmark version not found: {version_id}")
    
    def get_latest(self) -> Optional[BenchmarkVersion]:
        """Get latest version (via latest symbolic link or newest timestamp)"""
        try:
            return self.get_version('latest')
        except FileNotFoundError:
            # If latest link doesn't exist, return the newest version
            versions = self.list_versions()
            return versions[0] if versions else None
    
    def create_version(self, version_id: Optional[str] = None) -> BenchmarkVersion:
        """
        Create new version
        
        Args:
            version_id: Version ID, defaults to current timestamp
        
        Returns:
            Newly created BenchmarkVersion object
        """
        if version_id is None:
            version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        version_path = self.benchmarks_dir / version_id
        version_path.mkdir(parents=True, exist_ok=True)
        
        return BenchmarkVersion(version_path)
    
    def create_link(self, version_id: str, link_name: str) -> None:
        """
        Create symbolic link
        
        Args:
            version_id: Target version ID
            link_name: Link name (e.g. "latest", "stable", "dev")
        """
        # Verify target version exists
        version = self.get_version(version_id)
        if not version.exists:
            raise FileNotFoundError(f"Target version not found: {version_id}")
        
        link_path = self.benchmarks_dir / link_name
        
        # Remove existing link
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        
        # Create new link (relative path)
        link_path.symlink_to(version_id)
        logger.info(f"Created symlink: {link_name} -> {version_id}")
    
    def remove_link(self, link_name: str) -> None:
        """Remove symbolic link"""
        link_path = self.benchmarks_dir / link_name
        if link_path.is_symlink():
            link_path.unlink()
            logger.info(f"Removed symlink: {link_name}")
        else:
            logger.warning(f"Link does not exist: {link_name}")
    
    def archive_version(self, version_id: str) -> None:
        """
        Archive version (move to archive directory)
        
        Args:
            version_id: Version ID to archive
        """
        version = self.get_version(version_id)
        if not version.exists:
            raise FileNotFoundError(f"Version not found: {version_id}")
        
        # Cannot archive version referenced by symbolic link
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
        
        # Move to archive
        archive_path = self.archive_dir / version_id
        shutil.move(str(version.version_dir), str(archive_path))
        
        # Update metadata status
        archived_version = BenchmarkVersion(archive_path)
        metadata = archived_version.metadata
        metadata['status'] = 'archived'
        metadata['archived_at'] = datetime.now().isoformat()
        archived_version.save_metadata(metadata)
        
        logger.info(f"Archived version: {version_id}")
    
    def delete_version(self, version_id: str, force: bool = False) -> None:
        """
        Delete version
        
        Args:
            version_id: Version ID to delete
            force: Force delete (even if referenced by symbolic link)
        """
        version = self.get_version(version_id)
        if not version.exists:
            raise FileNotFoundError(f"Version not found: {version_id}")
        
        # Check if referenced by symbolic link
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
        
        # Delete directory
        shutil.rmtree(version.version_dir)
        logger.info(f"Deleted version: {version_id}")
    
    def get_aliases(self) -> Dict[str, str]:
        """
        Get all symbolic link aliases
        
        Returns:
            {link_name: version_id} mapping
        """
        aliases = {}
        for item in self.benchmarks_dir.iterdir():
            if item.is_symlink():
                target = item.resolve()
                aliases[item.name] = target.name
        return aliases
    
    @staticmethod
    def _is_valid_version_id(version_id: str) -> bool:
        """Check if it's a valid version ID (YYYYMMDD_HHMMSS format)"""
        if len(version_id) != 15:  # YYYYMMDD_HHMMSS
            return False
        parts = version_id.split('_')
        if len(parts) != 2:
            return False
        date_part, time_part = parts
        return (len(date_part) == 8 and date_part.isdigit() and
                len(time_part) == 6 and time_part.isdigit())

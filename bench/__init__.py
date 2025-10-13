"""Text2Mem Benchmark Suite.

End-to-end testing framework for the Text2Mem system.

Quick Start:
    >>> from bench import BenchRunner, BenchConfig
    >>> config = BenchConfig(db_root="bench/data/v1/db")
    >>> runner = BenchRunner(config)
    >>> result = runner.run_sample(sample_dict)

CLI Usage:
    $ python -m bench.cli run --split test
    $ python -m bench.cli list --split test
    $ python -m bench.cli report -i results.json
"""

from .core.metrics import BenchmarkStats, OperationMetrics, RetrievalMetrics
from .core.runner import BenchConfig, BenchRunner, SampleRunResult

__version__ = "0.1.0"

__all__ = [
    "BenchRunner",
    "BenchConfig",
    "SampleRunResult",
    "BenchmarkStats",
    "RetrievalMetrics",
    "OperationMetrics",
]

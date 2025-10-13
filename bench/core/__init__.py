"""Core benchmark modules for Text2Mem."""

from .cli import BenchCLI, main
from .metrics import (
    BenchmarkStats,
    OperationMetrics,
    RetrievalMetrics,
    average_precision,
    f1_score,
    mean_reciprocal_rank,
    ndcg,
    precision_at_k,
    recall_at_k,
)
from .runner import (
    AssertionOutcome,
    BenchConfig,
    BenchRunner,
    RankingOutcome,
    SampleRunResult,
)

__all__ = [
    # CLI
    "BenchCLI",
    "main",
    # Runner
    "BenchRunner",
    "BenchConfig",
    "SampleRunResult",
    "AssertionOutcome",
    "RankingOutcome",
    # Metrics
    "BenchmarkStats",
    "RetrievalMetrics",
    "OperationMetrics",
    "ndcg",
    "precision_at_k",
    "recall_at_k",
    "mean_reciprocal_rank",
    "average_precision",
    "f1_score",
]

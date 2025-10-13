from __future__ import annotations

import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence


def ndcg(scores: Sequence[float], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K."""
    top_scores = list(scores[:k])
    if not top_scores:
        return 0.0
    dcg = sum(score / math.log2(idx + 2) for idx, score in enumerate(top_scores))
    ideal = sorted(top_scores, reverse=True)
    idcg = sum(score / math.log2(idx + 2) for idx, score in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def precision_at_k(predicted: Sequence[str], gold: Iterable[str], k: int) -> float:
    """Precision at K: ratio of relevant items in top-K."""
    gold_set = set(gold)
    top = predicted[:k]
    if not top:
        return 0.0
    hits = sum(1 for item in top if item in gold_set)
    return hits / len(top)


def recall_at_k(predicted: Sequence[str], gold: Iterable[str], k: int) -> float:
    """Recall at K: ratio of relevant items retrieved in top-K."""
    gold_set = set(gold)
    if not gold_set:
        return 0.0
    top = predicted[:k]
    hits = sum(1 for item in top if item in gold_set)
    return hits / len(gold_set)


def mean_reciprocal_rank(predicted: Sequence[str], gold: Iterable[str]) -> float:
    """Mean Reciprocal Rank: 1/rank of first relevant item."""
    gold_set = set(gold)
    for idx, item in enumerate(predicted, start=1):
        if item in gold_set:
            return 1.0 / idx
    return 0.0


def average_precision(predicted: Sequence[str], gold: Iterable[str]) -> float:
    """Average Precision: mean of precision at each relevant position."""
    gold_set = set(gold)
    if not gold_set:
        return 0.0
    
    precisions = []
    hits = 0
    for idx, item in enumerate(predicted, start=1):
        if item in gold_set:
            hits += 1
            precisions.append(hits / idx)
    
    return sum(precisions) / len(gold_set) if precisions else 0.0


def f1_score(precision: float, recall: float) -> float:
    """F1 Score: harmonic mean of precision and recall."""
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


@dataclass
class RetrievalMetrics:
    """Aggregated retrieval metrics with support for multiple evaluation points."""
    
    ndcg_at_5: List[float] = field(default_factory=list)
    ndcg_at_10: List[float] = field(default_factory=list)
    precision_at_5: List[float] = field(default_factory=list)
    precision_at_10: List[float] = field(default_factory=list)
    recall_at_5: List[float] = field(default_factory=list)
    recall_at_10: List[float] = field(default_factory=list)
    mrr: List[float] = field(default_factory=list)
    map_scores: List[float] = field(default_factory=list)
    f1_at_5: List[float] = field(default_factory=list)
    f1_at_10: List[float] = field(default_factory=list)

    def update(self, predicted_ids: Sequence[str], relevance_scores: Sequence[float], gold_ids: Sequence[str]) -> None:
        """Update metrics with a new prediction."""
        self.ndcg_at_5.append(ndcg(relevance_scores, 5))
        self.ndcg_at_10.append(ndcg(relevance_scores, 10))
        
        p5 = precision_at_k(predicted_ids, gold_ids, 5)
        p10 = precision_at_k(predicted_ids, gold_ids, 10)
        r5 = recall_at_k(predicted_ids, gold_ids, 5)
        r10 = recall_at_k(predicted_ids, gold_ids, 10)
        
        self.precision_at_5.append(p5)
        self.precision_at_10.append(p10)
        self.recall_at_5.append(r5)
        self.recall_at_10.append(r10)
        self.f1_at_5.append(f1_score(p5, r5))
        self.f1_at_10.append(f1_score(p10, r10))
        
        self.mrr.append(mean_reciprocal_rank(predicted_ids, gold_ids))
        self.map_scores.append(average_precision(predicted_ids, gold_ids))

    def summarise(self) -> Dict[str, float]:
        """Compute mean values for all metrics."""
        def mean(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return {
            "ndcg@5": mean(self.ndcg_at_5),
            "ndcg@10": mean(self.ndcg_at_10),
            "precision@5": mean(self.precision_at_5),
            "precision@10": mean(self.precision_at_10),
            "recall@5": mean(self.recall_at_5),
            "recall@10": mean(self.recall_at_10),
            "f1@5": mean(self.f1_at_5),
            "f1@10": mean(self.f1_at_10),
            "mrr": mean(self.mrr),
            "map": mean(self.map_scores),
            "samples": len(self.mrr),
        }


@dataclass
class OperationMetrics:
    """Track operation-level performance metrics."""
    
    operation_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    operation_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    operation_successes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    operation_failures: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def record_operation(self, op: str, success: bool, duration: float) -> None:
        """Record an operation execution."""
        self.operation_counts[op] += 1
        self.operation_times[op].append(duration)
        if success:
            self.operation_successes[op] += 1
        else:
            self.operation_failures[op] += 1
    
    def summarise(self) -> Dict[str, Any]:
        """Compute summary statistics for all operations."""
        summary = {}
        for op in self.operation_counts:
            times = self.operation_times[op]
            summary[op] = {
                "count": self.operation_counts[op],
                "success": self.operation_successes[op],
                "failure": self.operation_failures[op],
                "success_rate": self.operation_successes[op] / self.operation_counts[op] if self.operation_counts[op] > 0 else 0.0,
                "avg_time_ms": sum(times) / len(times) * 1000 if times else 0.0,
                "min_time_ms": min(times) * 1000 if times else 0.0,
                "max_time_ms": max(times) * 1000 if times else 0.0,
            }
        return summary


@dataclass
class BenchmarkStats:
    """Overall benchmark execution statistics."""
    
    total_samples: int = 0
    passed_samples: int = 0
    failed_samples: int = 0
    total_assertions: int = 0
    passed_assertions: int = 0
    failed_assertions: int = 0
    total_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    retrieval_metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    operation_metrics: OperationMetrics = field(default_factory=OperationMetrics)
    
    def add_sample_result(self, passed: bool, assertions_count: int, 
                         assertions_passed: int, duration: float) -> None:
        """Add results from a sample run."""
        self.total_samples += 1
        if passed:
            self.passed_samples += 1
        else:
            self.failed_samples += 1
        
        self.total_assertions += assertions_count
        self.passed_assertions += assertions_passed
        self.failed_assertions += assertions_count - assertions_passed
        self.total_time += duration
    
    def summarise(self) -> Dict[str, Any]:
        """Generate complete benchmark summary."""
        pass_rate = self.passed_samples / self.total_samples if self.total_samples > 0 else 0.0
        assertion_pass_rate = self.passed_assertions / self.total_assertions if self.total_assertions > 0 else 0.0
        
        return {
            "overview": {
                "total_samples": self.total_samples,
                "passed_samples": self.passed_samples,
                "failed_samples": self.failed_samples,
                "pass_rate": pass_rate,
                "total_time_sec": self.total_time,
                "avg_time_sec": self.total_time / self.total_samples if self.total_samples > 0 else 0.0,
            },
            "assertions": {
                "total": self.total_assertions,
                "passed": self.passed_assertions,
                "failed": self.failed_assertions,
                "pass_rate": assertion_pass_rate,
            },
            "retrieval": self.retrieval_metrics.summarise() if self.retrieval_metrics.mrr else {},
            "operations": self.operation_metrics.summarise() if self.operation_metrics.operation_counts else {},
            "errors": self.errors,
        }


__all__ = [
    "RetrievalMetrics",
    "OperationMetrics",
    "BenchmarkStats",
    "ndcg",
    "precision_at_k",
    "recall_at_k",
    "mean_reciprocal_rank",
    "average_precision",
    "f1_score",
]

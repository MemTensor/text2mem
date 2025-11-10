#!/usr/bin/env python3
"""Command-line interface for Text2Mem Bench.

Usage:
    python -m bench.cli run --split test
    python -m bench.cli run --filter "lang:zh op:Encode"
    python -m bench.cli report --format html
    python -m bench.cli generate --op Encode --lang zh
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .metrics import BenchmarkStats
from .runner import BenchConfig, BenchRunner, SampleRunResult


class BenchCLI:
    """Command-line interface for benchmark operations."""
    
    def __init__(self):
        self.root = Path(__file__).parent.parent.parent
        self.bench_dir = self.root / "bench"
        self.data_dir = self.bench_dir / "data"
        self.output_dir = self.bench_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_tests(
        self,
        split: Optional[str] = None,
        filter_expr: Optional[str] = None,
        verbose: Optional[bool] = None,
        output: Optional[str] = None,
        mode: Optional[str] = None,
        timeout: Optional[float] = None,
        schema_filter: Optional[List[str]] = None,
        schema_indices: Optional[List[int]] = None,
    ) -> int:
        """Run benchmark tests.
        
        Args with None values will be read from environment variables.
        """
        # Apply defaults from environment variables
        if split is None:
            split = os.getenv("TEXT2MEM_BENCH_SPLIT", "basic")
        if verbose is None:
            verbose = os.getenv("TEXT2MEM_BENCH_VERBOSE", "false").lower() in ("true", "1", "yes")
        if mode is None:
            mode = os.getenv("TEXT2MEM_BENCH_MODE")
        if timeout is None:
            env_timeout = os.getenv("TEXT2MEM_BENCH_TIMEOUT")
            if env_timeout and env_timeout.strip():
                try:
                    timeout = float(env_timeout)
                except ValueError:
                    pass  # Invalid value, keep None
        
        # Try to find split file in multiple locations
        split_file = None
        search_paths = []
        
        # If split is "benchmark", find the latest benchmark.jsonl
        if split == "benchmark":
            search_paths = [
                self.data_dir / "benchmarks" / "latest" / "benchmark.jsonl",  # benchmarks/latest/benchmark.jsonl
                self.data_dir / "benchmarks" / "v2" / "benchmark.jsonl",  # benchmarks/v2/benchmark.jsonl
                self.data_dir / "benchmarks" / "v1" / "benchmark.jsonl",  # benchmarks/v1/benchmark.jsonl
            ]
        else:
            search_paths = [
                self.data_dir / "benchmarks" / "latest" / "benchmark.jsonl",  # benchmarks/latest/benchmark.jsonl
                self.data_dir / "benchmarks" / split / "benchmark.jsonl",  # benchmarks/v1/benchmark.jsonl
                self.data_dir / "benchmarks" / f"{split}.jsonl",  # benchmarks/test.jsonl
                self.data_dir / "test_data" / f"{split}.jsonl",  # test_data/basic.jsonl (legacy)
            ]
        
        for path in search_paths:
            if path.exists():
                split_file = path
                break
        
        if split_file is None:
            print(f"❌ Split '{split}' not found. Searched in:")
            for path in search_paths:
                print(f"   - {path}")
            print(f"\n💡 Tip: To test benchmark data, use:")
            print(f"   python -m bench run --split benchmark")
            return 1
        
        print(f"📂 Using test file: {split_file.relative_to(self.root)}")
        
        # Load samples - support multi-line JSON objects
        samples = self._load_json_samples(split_file)
        
        # Apply filter
        if filter_expr:
            samples = [s for s in samples if self._matches_filter(s, filter_expr)]
        
        if not samples:
            print("⚠️  No samples matched the filter criteria")
            return 0
        
        print(f"📊 Running {len(samples)} samples from '{split}' split")
        if mode:
            print(f"🔧 Using engine mode: {mode}")
        if timeout:
            print(f"⏱️  Timeout per sample: {timeout}s")
        if schema_filter:
            print(f"🔍 Schema filter: {', '.join(schema_filter)}")
        if schema_indices:
            print(f"🔍 Schema indices: {schema_indices}")
        print("=" * 60)
        
        # Configure runner
        config = BenchConfig(
            db_root=self.data_dir / "db",
            output_dir=self.output_dir,
            mode=mode,  # Pass mode argument
            timeout=timeout,  # Pass timeout argument
            schema_filter=schema_filter,  # Pass schema_filter argument
            schema_indices=schema_indices,  # Pass schema_indices argument
        )
        runner = BenchRunner(config)
        
        # Run samples
        stats = BenchmarkStats()
        results: List[Dict[str, Any]] = []
        
        start_time = time.time()
        
        for idx, sample in enumerate(samples, start=1):
            sample_id = sample.get("id", f"sample-{idx}")
            
            if verbose:
                print(f"\n[{idx}/{len(samples)}] Running: {sample_id}")
            
            sample_start = time.time()
            result = runner.run_sample(sample, sample_id=sample_id)
            sample_duration = time.time() - sample_start
            
            # Update stats
            assertions_passed = sum(1 for a in result.assertions if a.passed)
            stats.add_sample_result(
                passed=result.passed,
                assertions_count=len(result.assertions),
                assertions_passed=assertions_passed,
                duration=sample_duration,
            )
            
            # Track operations
            for schema_result in result.schema_results:
                op = schema_result.get("op", "unknown")
                success = schema_result.get("success", False)
                stats.operation_metrics.record_operation(op, success, sample_duration / len(result.schema_results))
            
            # Track retrieval metrics
            if result.ranking:
                gold_ids = [str(g) for g in result.ranking.gold_ids]
                retrieved_ids = result.ranking.retrieved_ids
                scores = [result.ranking.scores.get(rid, 0.0) for rid in retrieved_ids]
                stats.retrieval_metrics.update(retrieved_ids, scores, gold_ids)
            
            # Display result
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {status} {sample_id} ({sample_duration:.2f}s)")
            
            # In verbose mode, show ranking details even for passed tests
            if verbose and result.ranking:
                # Check if it's a Mock mode warning
                if "⚠️ MOCK MODE" in result.ranking.message:
                    print(f"    ⚠️  {result.ranking.message}")
            
            if not result.passed:
                if result.errors:
                    for error in result.errors:
                        print(f"    ❌ Error: {error}")
                        stats.errors.append(f"{sample_id}: {error}")
                
                for assertion in result.assertions:
                    if not assertion.passed:
                        print(f"    ❌ {assertion.name}: {assertion.message}")
                
                if result.ranking and not result.ranking.passed:
                    print(f"    ❌ Ranking: {result.ranking.message}")
            
            # Store result
            results.append({
                "sample_id": sample_id,
                "passed": result.passed,
                "assertions": [
                    {
                        "name": a.name,
                        "passed": a.passed,
                        "message": a.message,
                        "value": a.value,
                    }
                    for a in result.assertions
                ],
                "ranking": {
                    "query": result.ranking.query,
                    "passed": result.ranking.passed,
                    "precision": result.ranking.precision,
                    "recall": result.ranking.recall,
                    "hits": len(result.ranking.hits),
                    "message": result.ranking.message,
                } if result.ranking else None,
                "duration": sample_duration,
            })
        
        total_time = time.time() - start_time
        stats.total_time = total_time
        
        # Print summary
        print("\n" + "=" * 60)
        print("📈 Summary")
        print("=" * 60)
        
        summary = stats.summarise()
        overview = summary["overview"]
        
        print(f"Samples:    {overview['passed_samples']}/{overview['total_samples']} passed ({overview['pass_rate']:.1%})")
        print(f"Assertions: {summary['assertions']['passed']}/{summary['assertions']['total']} passed ({summary['assertions']['pass_rate']:.1%})")
        print(f"Total time: {total_time:.2f}s (avg: {overview['avg_time_sec']:.2f}s/sample)")
        
        if summary.get("retrieval"):
            print(f"\nRetrieval metrics:")
            for metric, value in summary["retrieval"].items():
                if metric != "samples":
                    print(f"  {metric}: {value:.4f}")
        
        if summary.get("operations"):
            print(f"\nOperation success rates:")
            for op, metrics in summary["operations"].items():
                print(f"  {op}: {metrics['success_rate']:.1%} ({metrics['success']}/{metrics['count']})")
        
        # Save results
        if output:
            output_path = Path(output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"results_{split}_{timestamp}.json"
        
        report = {
            "metadata": {
                "split": split,
                "filter": filter_expr,
                "timestamp": datetime.now().isoformat(),
                "total_samples": len(samples),
            },
            "summary": summary,
            "results": results,
        }
        
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Results saved to: {output_path}")
        
        return 0 if overview["failed_samples"] == 0 else 1
    
    def _load_json_samples(self, filepath: Path) -> List[Dict[str, Any]]:
        """Load JSON samples from file, supporting multi-line JSON objects.
        
        The file can be:
        1. Standard JSONL (one JSON per line)
        2. Multi-line JSON objects separated by newlines
        """
        samples = []
        content = filepath.read_text(encoding="utf-8")
        
        # Try to parse as complete JSON array first
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
        except json.JSONDecodeError:
            pass
        
        # Parse as JSONL-style (one or more complete JSON objects)
        current_obj = ""
        brace_count = 0
        in_string = False
        escape_next = False
        
        for char in content:
            if escape_next:
                current_obj += char
                escape_next = False
                continue
            
            if char == '\\':
                current_obj += char
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
            
            current_obj += char
            
            # Complete JSON object found
            if brace_count == 0 and current_obj.strip() and not in_string:
                try:
                    sample = json.loads(current_obj.strip())
                    samples.append(sample)
                    current_obj = ""
                except json.JSONDecodeError as e:
                    # Skip invalid JSON
                    current_obj = ""
        
        return samples
    
    def _matches_filter(self, sample: Dict[str, Any], filter_expr: str) -> bool:
        """Check if sample matches filter expression."""
        # Simple filter format: "key:value key2:value2"
        # Supported keys: lang, op, instruction, structure
        filters = {}
        for part in filter_expr.split():
            if ":" in part:
                key, value = part.split(":", 1)
                filters[key.strip()] = value.strip()
        
        sample_class = sample.get("class", {})
        
        # Check language
        if "lang" in filters:
            if sample_class.get("lang") != filters["lang"]:
                return False
        
        # Check instruction type
        if "instruction" in filters:
            if sample_class.get("instruction") != filters["instruction"]:
                return False
        
        # Check structure
        if "structure" in filters:
            if sample_class.get("structure") != filters["structure"]:
                return False
        
        # Check operation
        if "op" in filters:
            ops_in_sample = [ir.get("op") for ir in sample.get("schema_list", [])]
            if filters["op"] not in ops_in_sample:
                return False
        
        return True
    
    def generate_template(
        self,
        op: str,
        lang: str = "zh",
        output: Optional[str] = None,
    ) -> int:
        """Generate a sample template."""
        from bench.tools.sample_generator import SampleBuilder
        
        # Generate sample ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        sample_id = f"t2m-{lang}-direct-single-{timestamp}"
        
        builder = SampleBuilder(sample_id)
        builder.set_metadata(lang=lang, structure="single")
        builder.set_nl(f"TODO: Add natural language description for {op} operation")
        
        # Add operation-specific template
        if op == "Encode":
            builder.add_encode(
                text="TODO: Add text to encode",
                type="note",
                tags=["tag1", "tag2"],
            )
            builder.add_assertion(
                name="verify_encode",
                from_table="memory",
                where=["deleted=0", "text LIKE :keyword"],
                expect_op=">=",
                expect_value=1,
                params={"keyword": "%TODO%"},
            )
        elif op == "Retrieve":
            builder.add_retrieve(query="TODO: Add search query")
            builder.set_ranking(
                query="TODO: Add search query",
                gold_ids=["1"],
                min_hits=1,
            )
        elif op == "Update":
            builder.add_update(ids=[1], updates={"type": "updated"})
            builder.add_assertion(
                name="verify_update",
                from_table="memory",
                where=["id=:id", "type=:type"],
                expect_op="==",
                expect_value=1,
                params={"id": 1, "type": "updated"},
            )
        else:
            print(f"⚠️  Operation '{op}' template not yet implemented")
            print(f"📝 Creating basic template...")
        
        builder.set_notes(f"TODO: Add description for {op} test case")
        
        # Save or print
        template = builder.build()
        json_str = template.to_json(indent=2)
        
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_str + "\n", encoding="utf-8")
            print(f"✅ Template saved to: {output_path}")
        else:
            print("📝 Generated template:")
            print(json_str)
        
        return 0
    
    def list_samples(self, split: str = "test") -> int:
        """List all samples in a split."""
        # Try to find split file in multiple locations
        split_file = None
        search_paths = [
            self.data_dir / "benchmarks" / "latest" / f"{split}.jsonl",
            self.data_dir / "benchmarks" / split / f"{split}.jsonl",
            self.data_dir / "benchmarks" / f"{split}.jsonl",
            self.data_dir / "test_data" / f"{split}.jsonl",
        ]
        
        for path in search_paths:
            if path.exists():
                split_file = path
                break
        
        if split_file is None:
            print(f"❌ Split '{split}' not found. Searched in:")
            for path in search_paths:
                print(f"   - {path}")
            print(f"\n💡 Tip: To list benchmark data, use:")
            print(f"   python -m bench list --split benchmark")
            return 1
        
        print(f"📂 Using test file: {split_file.relative_to(self.root)}\n")
        
        print(f"📋 Samples in '{split}' split:")
        print("=" * 80)
        
        # Use the same loader as run_tests
        samples = self._load_json_samples(split_file)
        
        for idx, sample in enumerate(samples, start=1):
            sample_id = sample.get("id", f"sample-{idx}")
            sample_class = sample.get("class", {})
            ops = [ir.get("op") for ir in sample.get("schema_list", [])]
            
            print(f"{idx}. {sample_id}")
            print(f"   Lang: {sample_class.get('lang', 'N/A')}, "
                  f"Type: {sample_class.get('instruction', 'N/A')}, "
                  f"Structure: {sample_class.get('structure', 'N/A')}")
            print(f"   Operations: {', '.join(ops)}")
            if sample.get("prerequisites"):
                print(f"   Prerequisites: {len(sample['prerequisites'])} instruction(s)")
            print()
        
        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Text2Mem Benchmark CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run benchmark tests")
    run_parser.add_argument("--split", default=None, 
                           help="Split to run (default: from TEXT2MEM_BENCH_SPLIT env or 'basic')")
    run_parser.add_argument("--filter", help="Filter expression (e.g., 'lang:zh op:Encode')")
    run_parser.add_argument("--verbose", "-v", action="store_true", default=None,
                           help="Verbose output (default: from TEXT2MEM_BENCH_VERBOSE env or false)")
    run_parser.add_argument("--output", "-o", help="Output file for results")
    run_parser.add_argument("--mode", choices=["auto", "mock", "ollama", "openai"], 
                           default=None, 
                           help="Engine mode (default: from TEXT2MEM_BENCH_MODE env or 'auto')")
    run_parser.add_argument("--timeout", type=float, default=None, 
                           help="Timeout in seconds for each sample (default: from TEXT2MEM_BENCH_TIMEOUT env or no timeout)")
    run_parser.add_argument("--schema-filter", type=str, default=None,
                           help="Filter schemas by operation names (comma-separated, e.g., 'Encode,Retrieve')")
    run_parser.add_argument("--schema-indices", type=str, default=None,
                           help="Filter schemas by indices (comma-separated, e.g., '0,2')")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate sample template")
    gen_parser.add_argument("--op", required=True, help="Operation type (e.g., Encode)")
    gen_parser.add_argument("--lang", default="zh", choices=["zh", "en"], help="Language")
    gen_parser.add_argument("--output", "-o", help="Output file")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List samples in a split")
    list_parser.add_argument("--split", default=None,
                           help="Split to list (default: from TEXT2MEM_BENCH_SPLIT env or 'basic')")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    cli = BenchCLI()
    
    try:
        if args.command == "run":
            # Parse schema_filter and schema_indices
            schema_filter = None
            if args.schema_filter:
                schema_filter = [s.strip() for s in args.schema_filter.split(',') if s.strip()]
            
            schema_indices = None
            if args.schema_indices:
                try:
                    schema_indices = [int(i.strip()) for i in args.schema_indices.split(',') if i.strip()]
                except ValueError:
                    print("❌ Error: --schema-indices must be comma-separated integers")
                    return 1
            
            return cli.run_tests(
                split=args.split,
                filter_expr=args.filter,
                verbose=args.verbose,
                output=args.output,
                mode=args.mode,
                timeout=args.timeout,
                schema_filter=schema_filter,
                schema_indices=schema_indices,
            )
        elif args.command == "generate":
            return cli.generate_template(
                op=args.op,
                lang=args.lang,
                output=args.output,
            )
        elif args.command == "list":
            return cli.list_samples(split=args.split or os.getenv("TEXT2MEM_BENCH_SPLIT", "basic"))
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Generation Controller - Main generation workflow controller
Coordinates the full three-stage generation process and supports checkpoint recovery
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bench.generate.src.llm_client import LLMClient, LLMConfig, create_llm_client
from bench.generate.src.plan_loader import PlanLoader, TaskAllocator, GenerationPlan, TaskBatch
from bench.generate.src.checkpoint_manager import CheckpointManager, Checkpoint, StageProgress
from bench.generate.src.stage1_generator import Stage1Generator
from bench.generate.src.stage2_generator import Stage2Generator, IRSample
from bench.generate.src.stage3_generator import Stage3Generator


class GenerationController:
    """Main generation controller"""
    
    def __init__(
        self,
        plan_file: Path,
        resume: bool = True,
        verbose: bool = True,
    ):
        """
        Args:
            plan_file: Path to the generation plan configuration file
            resume: Whether to resume from a checkpoint
            verbose: Whether to print detailed logs
        """
        self.verbose = verbose
        
        # Load generation plan
        self.plan = PlanLoader.load(plan_file)
        self._log(f"📋 Loaded plan: {self.plan.name}")
        
        # Validate configuration
        errors = PlanLoader.validate_plan(self.plan)
        if errors:
            raise ValueError(f"Configuration validation failed:\n  " + "\n  ".join(errors))
        
        # Create LLM client
        llm_config = LLMConfig.from_dict(self.plan.llm)
        self.llm_client = create_llm_client(llm_config)
        self._log(f"🤖 LLM: {llm_config.provider} / {llm_config.model}")
        
        # Test connection
        if not self.llm_client.test_connection():
            raise ConnectionError("Failed to connect to LLM service")
        self._log("✅ LLM connection successful")
        
        # Create task allocator
        self.allocator = TaskAllocator(self.plan)
        
        # Initialize checkpoint manager
        checkpoint_file = Path(self.plan.checkpoint_file.format(plan_name=self.plan.name))
        self.checkpoint_mgr = CheckpointManager(checkpoint_file)
        
        # Load or create checkpoint
        if resume and self.plan.resume_from_checkpoint:
            self.checkpoint = self.checkpoint_mgr.load()
            if self.checkpoint:
                self._log(f"📥 Resumed from checkpoint: {self.checkpoint.progress_percentage:.1f}% completed")
            else:
                self.checkpoint = self._create_new_checkpoint()
        else:
            self.checkpoint = self._create_new_checkpoint()
        
        # Initialize generators
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        self.stage1_generator = Stage1Generator(self.llm_client, self.plan, prompts_dir)
        self.stage2_generator = Stage2Generator(self.llm_client, self.plan, prompts_dir, llm_config)
        self.stage3_generator = Stage3Generator(self.llm_client, self.plan, prompts_dir, llm_config)
        
        # Output directory - defaults to data/raw/
        base_dir = self.plan.output.get("base_dir", "bench/data/raw")
        self.output_dir = Path(base_dir)
        
        # Create run directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_new_checkpoint(self) -> Checkpoint:
        """Create a new checkpoint"""
        self._log("🆕 Creating new checkpoint")
        checkpoint = self.checkpoint_mgr.create_new(
            self.plan.name,
            self.plan.total_samples,
        )
        
        # Initialize stage progress records
        for stage_name in ["stage1", "stage2", "stage3"]:
            if self.plan.stages.get(stage_name, {}).get("enabled", True):
                # Determine total batch count
                if stage_name == "stage1":
                    batches = self.allocator.allocate_tasks(stage_name)
                    total_batches = len(batches)
                else:
                    # Stage 2 and Stage 3 use total sample count
                    total_batches = self.plan.total_samples
                
                checkpoint.stages[stage_name] = StageProgress(
                    stage_name=stage_name,
                    status="pending",
                    total_batches=total_batches,
                    completed_batches=0,
                )
        
        self.checkpoint_mgr.save(checkpoint)
        return checkpoint
    
    def _log(self, message: str):
        """Print log message if verbose"""
        if self.verbose:
            print(message)
    
    def run(self):
        """Run the complete generation workflow"""
        self._log("\n" + "=" * 60)
        self._log(f"🚀 Starting generation: {self.plan.name}")
        self._log("=" * 60)
        
        start_time = time.time()
        
        try:
            # Stage 1: NL instruction generation
            stage1_output = None
            if self._should_run_stage("stage1"):
                self._log("\n📝 Stage 1: Generating NL instructions...")
                stage1_output = self.run_stage1()
                self._log(f"✅ Stage 1 completed: {stage1_output}")
            else:
                self._log("\n⏭️  Stage 1: Already completed")
                stage1_output = self.checkpoint.output_files.get("stage1")
            
            # Stage 2: IR Schema generation
            stage2_output = None
            if self._should_run_stage("stage2"):
                self._log("\n🏗️  Stage 2: Generating IR Schemas...")
                stage2_output = self._run_stage2(stage1_output)
                self._log(f"✅ Stage 2 completed: {stage2_output}")
            else:
                self._log("\n⏭️  Stage 2: Already completed")
                stage2_output = self.checkpoint.output_files.get("stage2")
            
            # Stage 3: Expected result generation
            stage3_output = None
            if self._should_run_stage("stage3"):
                self._log("\n🎯 Stage 3: Generating expected results...")
                stage3_output = self._run_stage3(stage2_output)
                self._log(f"✅ Stage 3 completed: {stage3_output}")
            else:
                self._log("\n⏭️  Stage 3: Already completed")
            
            # Save metadata
            self._save_metadata(stage1_output, stage2_output, stage3_output)
            
            # Finished
            elapsed = time.time() - start_time
            self._log("\n" + "=" * 60)
            self._log(f"✅ Generation completed in {elapsed:.1f} seconds")
            self._log("=" * 60)
            
            # Print summary
            self._log("\n" + self.checkpoint_mgr.get_progress_summary())
            
        except KeyboardInterrupt:
            self._log("\n\n⚠️  Interrupted by user")
            self._log("💾 Progress has been saved to checkpoint")
            raise
        
        except Exception as e:
            self._log(f"\n\n❌ Generation failed: {e}")
            raise
    def _save_metadata(self, stage1_output: Optional[str], stage2_output: Optional[str], stage3_output: Optional[str]):
        """Save run metadata to metadata.json"""
        metadata = {
            "plan_name": self.plan.name,
            "timestamp": self.run_dir.name,  # use directory name as timestamp
            "total_samples": self.plan.total_samples,
            "stages": {
                "stage1": {
                    "enabled": self.plan.stages.get("stage1", {}).get("enabled", True),
                    "output": str(Path(stage1_output).name) if stage1_output else None
                },
                "stage2": {
                    "enabled": self.plan.stages.get("stage2", {}).get("enabled", True),
                    "output": str(Path(stage2_output).name) if stage2_output else None
                },
                "stage3": {
                    "enabled": self.plan.stages.get("stage3", {}).get("enabled", True),
                    "output": str(Path(stage3_output).name) if stage3_output else None
                }
            },
            "llm": {
                "provider": self.plan.llm.get("provider"),
                "model": self.plan.llm.get("model")
            }
        }
        
        metadata_file = self.run_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self._log(f"\n   📋 Metadata saved: {metadata_file}")
    
    def _should_run_stage(self, stage_name: str) -> bool:
        """Check whether a stage should be executed"""
        stage_config = self.plan.stages.get(stage_name, {})
        
        # Check if enabled
        if not stage_config.get("enabled", True):
            return False
        
        # Check if already completed
        stage_progress = self.checkpoint.stages.get(stage_name)
        if stage_progress and stage_progress.status == "completed":
            return False
        
        return True
    
    def run_stage1(self) -> str:
        """Run Stage 1: NL instruction generation (incremental save version)"""
        stage_name = "stage1"
        stage_progress = self.checkpoint.stages[stage_name]
        
        # Update status
        self.checkpoint_mgr.update_stage_progress(stage_name, status="running")
        
        # Allocate tasks
        batches = self.allocator.allocate_tasks(stage_name)
        self._log(f"   Total batches: {len(batches)}")
        
        # Prepare output file (JSONL format for incremental writing)
        output_file = self.run_dir / "stage1.jsonl"
        
        # Resume from existing output file if checkpoint exists
        existing_output = self.checkpoint.output_files.get(stage_name)
        if existing_output and Path(existing_output).exists():
            output_file = Path(existing_output)
            self._log(f"   📥 Resuming from existing output file: {output_file}")
        else:
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        # Append mode if resuming
        mode = 'a' if output_file.exists() else 'w'
        
        # Process each batch
        for batch in batches:
            if batch.batch_id < stage_progress.completed_batches:
                self._log(f"   ⏭️  Batch {batch.batch_id + 1}/{len(batches)} already completed")
                continue
            
            self._log(f"\n   📦 Batch {batch.batch_id + 1}/{len(batches)}")
            self._log(f"      Scenario: {batch.scenario}, Operation: {batch.operation}, Count: {batch.count}")
            
            try:
                # Generate instructions
                instructions = self.stage1_generator.generate_batch(batch)
                
                # Validate
                errors = self.stage1_generator.validate_instructions(instructions, batch)
                
                if errors:
                    validation_behavior = self.plan.validation.get("on_validation_error", "warn")
                    error_msg = "; ".join(errors[:3])
                    
                    if validation_behavior == "abort":
                        self._log(f"      ❌ Validation failed: {error_msg}")
                        raise ValueError(f"Batch {batch.batch_id} validation failed: {error_msg}")
                    elif validation_behavior == "warn":
                        self._log(f"      ⚠️  Validation warning: {error_msg}")
                
                # Incremental write to file
                with open(output_file, mode, encoding='utf-8') as f:
                    for instruction in instructions:
                        sample_data = {
                            "instruction": instruction.instruction,
                            "context": instruction.context,
                            "classification": instruction.classification,
                            "scenario_info": instruction.scenario_info,
                            "batch_id": batch.batch_id,
                        }
                        f.write(json.dumps(sample_data, ensure_ascii=False) + '\n')
                
                # Update progress
                self.checkpoint_mgr.update_stage_progress(
                    stage_name,
                    completed_batches=batch.batch_id + 1,
                )
                
                self.checkpoint_mgr.add_completed_samples(
                    count=len(instructions),
                    scenario=batch.scenario,
                    operation=batch.operation,
                )
                
                self._log(f"      ✅ Generated {len(instructions)} instructions (saved)")
                
                # Switch to append mode
                mode = 'a'
                
            except Exception as e:
                self._log(f"      ❌ Failed: {e}")
                self.checkpoint_mgr.mark_batch_failed(stage_name, batch.batch_id, str(e))
                
                if self.plan.validation.get("on_validation_error") == "abort":
                    raise
                continue
        
        # Update checkpoint
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
            output_file=str(output_file),
        )
        
        self._log(f"\n   ✅ Stage 1 completed, output file: {output_file}")
        
        return str(output_file)
    
    def _run_stage2(self, stage1_output: Optional[str]) -> Optional[str]:
        """Run Stage 2: IR Schema generation (incremental save version)"""
        if not stage1_output or not Path(stage1_output).exists():
            self._log("   ❌ Stage 1 output not found")
            return None
        
        # Load Stage 1 output (supports JSON and JSONL)
        stage1_path = Path(stage1_output)
        nl_instructions = []
        
        if stage1_path.suffix == '.jsonl':
            with open(stage1_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        nl_instructions.append(json.loads(line))
        else:
            with open(stage1_path, 'r', encoding='utf-8') as f:
                nl_instructions = json.load(f)
        
        self._log(f"   📥 Loaded {len(nl_instructions)} NL instructions")
        
        stage_name = "stage2"
        stage_progress = self.checkpoint_mgr.get_stage_progress(stage_name)
        if not stage_progress:
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                status="running",
                total_batches=len(nl_instructions),
                completed_batches=0,
            )
            stage_progress = self.checkpoint_mgr.get_stage_progress(stage_name)
        
        # Prepare output file
        output_file = self.run_dir / "stage2.jsonl"
        
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 Continuing with existing file: {output_file}")
        else:
            self._log(f"   📂 Output file: {output_file}")
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        sample_count = 0
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for idx, nl_instruction in enumerate(nl_instructions):
                if idx < stage_progress.completed_batches:
                    continue
                
                self._log(f"\n   📦 Processing sample {idx + 1}/{len(nl_instructions)}")
                
                try:
                    sample = self.stage2_generator.generate_single(nl_instruction)
                    
                    if sample:
                        sample_dict = {
                            "id": sample.id,
                            "class": sample.class_info,
                            "nl": sample.nl,
                            "prerequisites": sample.prerequisites,
                            "schema_list": sample.schema_list,
                            "init_db": sample.init_db,
                            "notes": sample.notes,
                        }
                        f.write(json.dumps(sample_dict, ensure_ascii=False) + '\n')
                        f.flush()
                        
                        sample_count += 1
                        self._log(f"      ✅ Generated and saved IR sample (Total: {sample_count})")
                    
                    self.checkpoint_mgr.update_stage_progress(
                        stage_name,
                        completed_batches=idx + 1,
                    )
                    
                except Exception as e:
                    self._log(f"      ❌ Failed: {e}")
                    self.checkpoint_mgr.record_error(stage_name, idx, str(e))
                    continue
        
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        self._log(f"\n   ✅ Stage 2 completed: {sample_count} samples saved")
        
        return str(output_file)
    
    def _run_stage3(self, stage2_output: Optional[str]) -> Optional[str]:
        """Run Stage 3: Expected output generation (incremental save version)"""
        if not stage2_output or not Path(stage2_output).exists():
            self._log("   ❌ Stage 2 output not found")
            return None
        
        # Load Stage 2 output
        ir_samples_dict = []
        with open(stage2_output, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ir_samples_dict.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        self._log(f"   📥 Loaded {len(ir_samples_dict)} IR samples")
        
        stage_name = "stage3"
        stage_progress = self.checkpoint_mgr.get_stage_progress(stage_name)
        if not stage_progress:
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                status="running",
                total_batches=len(ir_samples_dict),
                completed_batches=0,
            )
            stage_progress = self.checkpoint_mgr.get_stage_progress(stage_name)
        
        output_file = self.run_dir / "stage3.jsonl"
        
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 Continuing with existing file: {output_file}")
        else:
            self._log(f"   📂 Output file: {output_file}")
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        sample_count = 0
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for idx, sample_dict in enumerate(ir_samples_dict):
                if idx < stage_progress.completed_batches:
                    continue
                
                self._log(f"\n   📦 Processing sample {idx + 1}/{len(ir_samples_dict)}")
                
                try:
                    ir_sample = IRSample(
                        id=sample_dict.get("id", ""),
                        class_info=sample_dict.get("class", {}),
                        nl=sample_dict.get("nl", {}),
                        prerequisites=sample_dict.get("prerequisites", []),
                        schema_list=sample_dict.get("schema_list", []),
                        init_db=sample_dict.get("init_db"),
                        notes=sample_dict.get("notes", ""),
                    )
                    
                    complete_sample = self.stage3_generator.generate_single(ir_sample)
                    
                    if complete_sample:
                        sample_dict = {
                            "id": complete_sample.id,
                            "class": complete_sample.class_info,
                            "nl": complete_sample.nl,
                            "prerequisites": complete_sample.prerequisites,
                            "schema_list": complete_sample.schema_list,
                            "init_db": complete_sample.init_db,
                            "expected": complete_sample.expected,
                            "notes": complete_sample.notes,
                        }
                        f.write(json.dumps(sample_dict, ensure_ascii=False) + '\n')
                        f.flush()
                        
                        sample_count += 1
                        self._log(f"      ✅ Generated and saved complete sample (Total: {sample_count})")
                    
                    self.checkpoint_mgr.update_stage_progress(
                        stage_name,
                        completed_batches=idx + 1,
                    )
                    
                except Exception as e:
                    self._log(f"      ❌ Failed: {e}")
                    self.checkpoint_mgr.record_error(stage_name, idx, str(e))
                    continue
        
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        self._log(f"\n   ✅ Stage 3 completed: {sample_count} full samples saved")
        
        return str(output_file)
    
    def get_status(self) -> str:
        """Return current generation status summary"""
        return self.checkpoint_mgr.get_progress_summary()
    
    def reset(self):
        """Reset generation progress by deleting the checkpoint"""
        self.checkpoint_mgr.delete()
        self._log("🗑️  Checkpoint deleted")


def main():
    """Command-line entry point"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Text2Mem Bench sample generator")
    parser.add_argument(
        "--plan",
        type=str,
        default="bench/generate/config/generation_plan.yaml",
        help="Path to generation plan configuration file",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh (do not resume from checkpoint)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display current status and exit",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset generation progress",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=True,
        help="Enable verbose output",
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use asynchronous generation (recommended: 5-10x faster)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        help="Maximum concurrency (default: from TEXT2MEM_BENCH_GEN_MAX_CONCURRENT or 5)",
    )
    
    args = parser.parse_args()
    
    # Determine if async mode should be used
    use_async = args.use_async or os.getenv("TEXT2MEM_BENCH_GEN_USE_ASYNC", "").lower() in ("true", "1", "yes")
    
    try:
        if use_async:
            # Use async controller
            try:
                from bench.generate.src.generation_controller_async import AsyncGenerationController
                
                controller = AsyncGenerationController(
                    plan_file=Path(args.plan),
                    resume=not args.no_resume,
                    verbose=args.verbose,
                    max_concurrent=args.max_concurrent,
                )
                
                if args.status:
                    print(controller.get_status())
                elif args.reset:
                    controller.reset()
                else:
                    controller.run_async()
            
            except ImportError as e:
                print(f"❌ Async mode requires aiohttp: pip install aiohttp")
                print(f"   Or run in synchronous mode (remove --async flag)")
                exit(1)
        else:
            # Use synchronous controller
            controller = GenerationController(
                plan_file=Path(args.plan),
                resume=not args.no_resume,
                verbose=args.verbose,
            )
            
            if args.status:
                print(controller.get_status())
            elif args.reset:
                controller.reset()
            else:
                controller.run()
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

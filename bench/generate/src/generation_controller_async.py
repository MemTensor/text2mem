"""
AsyncGenerationController
Supports concurrent generation, dynamic rate limiting, and real-time checkpoint saving
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from asyncio import Semaphore, Queue
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bench.generate.src.generation_controller import GenerationController
from bench.generate.src.llm_client_async import AsyncLLMClient, create_async_llm_client
from bench.generate.src.llm_client import LLMConfig
from bench.generate.src.stage2_generator import IRSample
from bench.generate.src.stage3_generator import CompleteSample


class AsyncGenerationController(GenerationController):
    """Asynchronous generation controller"""
    
    def __init__(self, *args, max_concurrent: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Read concurrency level from environment variable or parameter
        if max_concurrent is None:
            max_concurrent = int(os.getenv("TEXT2MEM_BENCH_GEN_MAX_CONCURRENT", "5"))
        
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        
        # Write queue (ensures sequential writing)
        self.write_queue: Queue = Queue()
        
        # Statistics information
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0,
        }
        
        self._log(f"🚀 Async mode initialized: max concurrency = {self.max_concurrent}")
    
    def run_async(self):
        """Run asynchronous generation pipeline"""
        # Create and run event loop
        try:
            asyncio.run(self._run_async_impl())
        except KeyboardInterrupt:
            self._log("\n\n⚠️  User interrupted")
            self._log("💾 Progress has been saved to checkpoint")
            raise
        except Exception as e:
            self._log(f"\n\n❌ Generation failed: {e}")
            raise
    
    async def _run_async_impl(self):
        """Async execution implementation"""
        self._log("\n" + "=" * 60)
        self._log(f"🚀 Starting async generation: {self.plan.name}")
        self._log("=" * 60)
        
        start_time = time.time()
        
        # Stage 1: NL instruction generation
        stage1_output = None
        if self._should_run_stage("stage1"):
            self._log("\n📝 Stage 1: Generating NL instructions...")
            stage1_output = self.run_stage1()  # Stage 1 remains synchronous (batch generation)
            self._log(f"✅ Stage 1 completed: {stage1_output}")
        else:
            self._log("\n⏭️  Stage 1: Already completed")
            stage1_output = self.checkpoint.output_files.get("stage1")
        
        # Stage 2: IR Schema generation (async)
        stage2_output = None
        if self._should_run_stage("stage2"):
            self._log("\n🏗️  Stage 2: Asynchronously generating IR Schemas...")
            stage2_output = await self._run_stage2_async(stage1_output)
            self._log(f"✅ Stage 2 completed: {stage2_output}")
        else:
            self._log("\n⏭️  Stage 2: Already completed")
            stage2_output = self.checkpoint.output_files.get("stage2")
        
        # Stage 3: Expected output generation (async)
        stage3_output = None
        if self._should_run_stage("stage3"):
            self._log("\n🎯 Stage 3: Asynchronously generating expected outputs...")
            stage3_output = await self._run_stage3_async(stage2_output)
            self._log(f"✅ Stage 3 completed: {stage3_output}")
        else:
            self._log("\n⏭️  Stage 3: Already completed")
        
        # Completed
        elapsed = time.time() - start_time
        self._log("\n" + "=" * 60)
        self._log(f"✅ Generation completed, total time {elapsed:.1f} sec")
        self._log(self._format_stats())
        self._log("=" * 60)
        
        # Print summary
        self._log("\n" + self.checkpoint_mgr.get_progress_summary())
    
    async def _run_stage2_async(self, stage1_output: Optional[str]) -> Optional[str]:
        """Asynchronously run Stage 2"""
        if not stage1_output or not Path(stage1_output).exists():
            self._log("   ❌ Stage 1 output not found")
            return None
        
        # Load Stage 1 output (supports both JSON and JSONL formats)
        stage1_path = Path(stage1_output)
        nl_instructions = []
        
        if stage1_path.suffix == '.jsonl':
            # JSONL format (new version)
            with open(stage1_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        nl_instructions.append(json.loads(line))
        else:
            # JSON format (backward compatible)
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
        
        # If resuming from existing output file, continue using it
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 Continuing with existing file: {output_file}")
        else:
            self._log(f"   📂 Output file: {output_file}")
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        # Create async LLM client
        llm_config = LLMConfig.from_dict(self.plan.llm)
        async with create_async_llm_client(llm_config) as async_client:
            # Start file writer coroutine
            writer_task = asyncio.create_task(
                self._file_writer_worker(output_file, stage_name)
            )
            
            # Create generation tasks
            tasks = []
            for idx, nl_instruction in enumerate(nl_instructions):
                # Skip already completed samples
                if idx < stage_progress.completed_batches:
                    continue
                
                task = self._generate_stage2_sample(
                    async_client,
                    nl_instruction,
                    idx,
                    len(nl_instructions),
                    stage_name,
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            self._log(f"   🚀 Starting concurrent generation ({self.max_concurrent} concurrent tasks)...")
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait for writer to finish
            await self.write_queue.put(None)  # Termination signal
            await writer_task
            
            # Collect results
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = len(results) - successes
            
            self._log(f"\n   ✅ Stage 2 completed: {successes} success, {failures} failed")
        
        # Mark stage as completed
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        return str(output_file)
    async def _run_stage3_async(self, stage2_output: Optional[str]) -> Optional[str]:
        """Asynchronously run Stage 3"""
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
        
        # Prepare output file
        output_file = self.run_dir / "stage3.jsonl"
        
        # If resuming, continue using the existing output file
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 Continuing with existing file: {output_file}")
        else:
            self._log(f"   📂 Output file: {output_file}")
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        # Create async LLM client
        llm_config = LLMConfig.from_dict(self.plan.llm)
        async with create_async_llm_client(llm_config) as async_client:
            # Start file writer coroutine
            writer_task = asyncio.create_task(
                self._file_writer_worker(output_file, stage_name)
            )
            
            # Create generation tasks
            tasks = []
            for idx, sample_dict in enumerate(ir_samples_dict):
                # Skip already completed samples
                if idx < stage_progress.completed_batches:
                    continue
                
                task = self._generate_stage3_sample(
                    async_client,
                    sample_dict,
                    idx,
                    len(ir_samples_dict),
                    stage_name,
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            self._log(f"   🚀 Starting concurrent generation ({self.max_concurrent} concurrent tasks)...")
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait for writer to finish
            await self.write_queue.put(None)  # Termination signal
            await writer_task
            
            # Collect results
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = len(results) - successes
            
            self._log(f"\n   ✅ Stage 3 completed: {successes} success, {failures} failed")
        
        # Mark stage as completed
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        return str(output_file)
    
    async def _generate_stage2_sample(
        self,
        async_client: AsyncLLMClient,
        nl_instruction: Dict[str, Any],
        idx: int,
        total: int,
        stage_name: str,
    ) -> Optional[IRSample]:
        """Asynchronously generate a single Stage 2 sample"""
        async with self.semaphore:  # Limit concurrency
            start_time = time.time()
            
            try:
                self._log(f"   📦 [{idx + 1}/{total}] Generating sample...")
                
                # Perform async generation
                sample = await self._call_stage2_generator_async(async_client, nl_instruction)
                
                if sample:
                    # Add to write queue
                    sample_dict = {
                        "id": sample.id,
                        "class": sample.class_info,
                        "nl": sample.nl,
                        "prerequisites": sample.prerequisites,
                        "schema_list": sample.schema_list,
                        "init_db": sample.init_db,
                        "notes": sample.notes,
                    }
                    
                    await self.write_queue.put((idx, sample_dict, None, stage_name))
                    
                    elapsed = time.time() - start_time
                    self._log(f"      ✅ [{idx + 1}/{total}] Completed ({elapsed:.1f}s)")
                    
                    # Update statistics
                    self.stats["successful_requests"] += 1
                    self.stats["total_time"] += elapsed
                    
                    return sample
                    
            except Exception as e:
                self._log(f"      ❌ [{idx + 1}/{total}] Failed: {e}")
                
                # Record error
                await self.write_queue.put((idx, None, str(e), stage_name))
                
                # Update statistics
                self.stats["failed_requests"] += 1
                
                return None
            finally:
                self.stats["total_requests"] += 1
    
    async def _generate_stage3_sample(
        self,
        async_client: AsyncLLMClient,
        sample_dict: Dict[str, Any],
        idx: int,
        total: int,
        stage_name: str,
    ) -> Optional[CompleteSample]:
        """Asynchronously generate a single Stage 3 sample"""
        async with self.semaphore:  # Limit concurrency
            start_time = time.time()
            
            try:
                self._log(f"   📦 [{idx + 1}/{total}] Generating sample...")
                
                # Convert to IRSample
                ir_sample = IRSample(
                    id=sample_dict.get("id", ""),
                    class_info=sample_dict.get("class", {}),
                    nl=sample_dict.get("nl", {}),
                    prerequisites=sample_dict.get("prerequisites", []),
                    schema_list=sample_dict.get("schema_list", []),
                    init_db=sample_dict.get("init_db"),
                    notes=sample_dict.get("notes", ""),
                )
                
                # Perform async generation
                complete_sample = await self._call_stage3_generator_async(async_client, ir_sample)
                
                if complete_sample:
                    # Add to write queue
                    complete_dict = {
                        "id": complete_sample.id,
                        "class": complete_sample.class_info,
                        "nl": complete_sample.nl,
                        "prerequisites": complete_sample.prerequisites,
                        "schema_list": complete_sample.schema_list,
                        "init_db": complete_sample.init_db,
                        "expected": complete_sample.expected,
                        "notes": complete_sample.notes,
                    }
                    
                    await self.write_queue.put((idx, complete_dict, None, stage_name))
                    
                    elapsed = time.time() - start_time
                    self._log(f"      ✅ [{idx + 1}/{total}] Completed ({elapsed:.1f}s)")
                    
                    # Update statistics
                    self.stats["successful_requests"] += 1
                    self.stats["total_time"] += elapsed
                    
                    return complete_sample
                    
            except Exception as e:
                self._log(f"      ❌ [{idx + 1}/{total}] Failed: {e}")
                
                # Record error
                await self.write_queue.put((idx, None, str(e), stage_name))
                
                # Update statistics
                self.stats["failed_requests"] += 1
                
                return None
            finally:
                self.stats["total_requests"] += 1
    
    async def _call_stage2_generator_async(
        self,
        async_client: AsyncLLMClient,
        nl_instruction: Dict[str, Any],
    ) -> Optional[IRSample]:
        """Call Stage 2 generator (async version)"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Build prompt (fixed: use correct method name)
                prompt = self.stage2_generator._build_single_prompt(nl_instruction)
                
                # Async call to LLM
                response = await async_client.generate(prompt)
                
                # Parse response (fixed: pass correct parameters)
                sample = self.stage2_generator._parse_response(response.content, nl_instruction)
                
                if sample:
                    # Validate sample (None = single-sample validation)
                    errors = self.stage2_generator.validate_samples([sample], None)
                    if not errors:
                        return sample
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(1)
                        continue
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        return None
    
    async def _call_stage3_generator_async(
        self,
        async_client: AsyncLLMClient,
        ir_sample: IRSample,
    ) -> Optional[CompleteSample]:
        """Call Stage 3 generator (async version)"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Build prompt (fixed: use correct method name)
                prompt = self.stage3_generator._build_single_prompt(ir_sample)
                
                # Async call to LLM
                response = await async_client.generate(prompt)
                
                # Parse response
                complete_sample = self.stage3_generator._parse_response(
                    response.content,
                    ir_sample,
                )
                
                if complete_sample:
                    # Validate sample (None = single-sample validation)
                    errors = self.stage3_generator.validate_samples([complete_sample], None)
                    if not errors:
                        return complete_sample
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(1)
                        continue
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        return None
    
    async def _file_writer_worker(self, output_file: Path, stage_name: str):
        """File writing coroutine (ensures sequential writes and batch checkpoint updates)"""
        checkpoint_batch_size = int(os.getenv("TEXT2MEM_BENCH_GEN_CHECKPOINT_BATCH", "10"))
        write_count = 0
        last_idx = -1
        
        with open(output_file, 'a', encoding='utf-8') as f:
            while True:
                item = await self.write_queue.get()
                
                if item is None:  # Termination signal
                    # Final checkpoint update (if unsaved progress remains)
                    if write_count > 0 and last_idx >= 0:
                        self.checkpoint_mgr.update_stage_progress(
                            stage_name,
                            completed_batches=last_idx + 1,
                        )
                    break
                
                idx, sample_dict, error, stage = item
                
                if sample_dict:
                    # Write sample
                    f.write(json.dumps(sample_dict, ensure_ascii=False) + '\n')
                    f.flush()
                    
                    write_count += 1
                    last_idx = idx
                    
                    # Periodic checkpoint updates (reduce disk I/O)
                    if write_count % checkpoint_batch_size == 0:
                        self.checkpoint_mgr.update_stage_progress(
                            stage,
                            completed_batches=idx + 1,
                        )
                elif error:
                    # Record errors immediately
                    self.checkpoint_mgr.record_error(stage, idx, error)
                
                self.write_queue.task_done()
    
    def _format_stats(self) -> str:
        """Format generation statistics"""
        if self.stats["total_requests"] == 0:
            return ""
        
        avg_time = self.stats["total_time"] / self.stats["successful_requests"] \
            if self.stats["successful_requests"] > 0 else 0
        
        success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100
        
        return f"""
📊 Statistics:
   Total requests: {self.stats["total_requests"]}
   Successful: {self.stats["successful_requests"]}
   Failed: {self.stats["failed_requests"]}
   Success rate: {success_rate:.1f}%
   Average time: {avg_time:.2f}s/sample
   Total time: {self.stats["total_time"]:.1f}s
"""

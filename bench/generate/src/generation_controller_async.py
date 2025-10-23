"""
异步生成控制器
支持并发生成、动态限流、实时保存
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
    """异步生成控制器"""
    
    def __init__(self, *args, max_concurrent: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 从环境变量或参数读取并发数
        if max_concurrent is None:
            max_concurrent = int(os.getenv("TEXT2MEM_BENCH_GEN_MAX_CONCURRENT", "5"))
        
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        
        # 写入队列（确保顺序写入）
        self.write_queue: Queue = Queue()
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0,
        }
        
        self._log(f"🚀 异步模式: 最大并发数 = {self.max_concurrent}")
    
    def run_async(self):
        """运行异步生成流程"""
        # 创建事件循环并运行
        try:
            asyncio.run(self._run_async_impl())
        except KeyboardInterrupt:
            self._log("\n\n⚠️  用户中断")
            self._log("💾 进度已保存到断点")
            raise
        except Exception as e:
            self._log(f"\n\n❌ 生成失败: {e}")
            raise
    
    async def _run_async_impl(self):
        """异步运行实现"""
        self._log("\n" + "=" * 60)
        self._log(f"🚀 开始异步生成: {self.plan.name}")
        self._log("=" * 60)
        
        start_time = time.time()
        
        # Stage 1: NL指令生成
        stage1_output = None
        if self._should_run_stage("stage1"):
            self._log("\n📝 Stage 1: 生成NL指令...")
            stage1_output = self.run_stage1()  # Stage1 仍使用同步（批量生成）
            self._log(f"✅ Stage 1 完成: {stage1_output}")
        else:
            self._log("\n⏭️  Stage 1: 已完成")
            stage1_output = self.checkpoint.output_files.get("stage1")
        
        # Stage 2: IR Schema生成（异步）
        stage2_output = None
        if self._should_run_stage("stage2"):
            self._log("\n🏗️  Stage 2: 异步生成IR Schema...")
            stage2_output = await self._run_stage2_async(stage1_output)
            self._log(f"✅ Stage 2 完成: {stage2_output}")
        else:
            self._log("\n⏭️  Stage 2: 已完成")
            stage2_output = self.checkpoint.output_files.get("stage2")
        
        # Stage 3: Expected生成（异步）
        stage3_output = None
        if self._should_run_stage("stage3"):
            self._log("\n🎯 Stage 3: 异步生成Expected...")
            stage3_output = await self._run_stage3_async(stage2_output)
            self._log(f"✅ Stage 3 完成: {stage3_output}")
        else:
            self._log("\n⏭️  Stage 3: 已完成")
        
        # 完成
        elapsed = time.time() - start_time
        self._log("\n" + "=" * 60)
        self._log(f"✅ 生成完成，耗时 {elapsed:.1f}秒")
        self._log(self._format_stats())
        self._log("=" * 60)
        
        # 打印摘要
        self._log("\n" + self.checkpoint_mgr.get_progress_summary())
    
    async def _run_stage2_async(self, stage1_output: Optional[str]) -> Optional[str]:
        """异步运行 Stage 2"""
        if not stage1_output or not Path(stage1_output).exists():
            self._log("   ❌ Stage 1输出未找到")
            return None
        
        # 加载Stage 1输出（支持 JSON 和 JSONL 格式）
        stage1_path = Path(stage1_output)
        nl_instructions = []
        
        if stage1_path.suffix == '.jsonl':
            # JSONL 格式（新版本）
            with open(stage1_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        nl_instructions.append(json.loads(line))
        else:
            # JSON 格式（旧版本兼容）
            with open(stage1_path, 'r', encoding='utf-8') as f:
                nl_instructions = json.load(f)
        
        self._log(f"   📥 加载 {len(nl_instructions)} 条NL指令")
        
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
        
        # 准备输出文件
        output_file = self.run_dir / "stage2.jsonl"
        
        # 如果有现有输出文件且正在恢复，继续使用该文件
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 继续使用现有文件: {output_file}")
        else:
            self._log(f"   📂 输出文件: {output_file}")
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        # 创建异步LLM客户端
        llm_config = LLMConfig.from_dict(self.plan.llm)
        async with create_async_llm_client(llm_config) as async_client:
            # 启动写入协程
            writer_task = asyncio.create_task(
                self._file_writer_worker(output_file, stage_name)
            )
            
            # 创建生成任务
            tasks = []
            for idx, nl_instruction in enumerate(nl_instructions):
                # 跳过已完成的样本
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
            
            # 并发执行所有任务
            self._log(f"   🚀 开始并发生成 ({self.max_concurrent} 并发)...")
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 等待写入完成
            await self.write_queue.put(None)  # 结束信号
            await writer_task
            
            # 统计结果
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = len(results) - successes
            
            self._log(f"\n   ✅ Stage 2完成: {successes} 成功, {failures} 失败")
        
        # 标记阶段完成
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        return str(output_file)
    
    async def _run_stage3_async(self, stage2_output: Optional[str]) -> Optional[str]:
        """异步运行 Stage 3"""
        if not stage2_output or not Path(stage2_output).exists():
            self._log("   ❌ Stage 2输出未找到")
            return None
        
        # 加载Stage 2输出
        ir_samples_dict = []
        with open(stage2_output, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ir_samples_dict.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        self._log(f"   📥 加载 {len(ir_samples_dict)} 个IR样本")
        
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
        
        # 准备输出文件
        output_file = self.run_dir / "stage3.jsonl"
        
        # 如果有现有输出文件且正在恢复，继续使用该文件
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 继续使用现有文件: {output_file}")
        else:
            self._log(f"   📂 输出文件: {output_file}")
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        # 创建异步LLM客户端
        llm_config = LLMConfig.from_dict(self.plan.llm)
        async with create_async_llm_client(llm_config) as async_client:
            # 启动写入协程
            writer_task = asyncio.create_task(
                self._file_writer_worker(output_file, stage_name)
            )
            
            # 创建生成任务
            tasks = []
            for idx, sample_dict in enumerate(ir_samples_dict):
                # 跳过已完成的样本
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
            
            # 并发执行所有任务
            self._log(f"   🚀 开始并发生成 ({self.max_concurrent} 并发)...")
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 等待写入完成
            await self.write_queue.put(None)  # 结束信号
            await writer_task
            
            # 统计结果
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = len(results) - successes
            
            self._log(f"\n   ✅ Stage 3完成: {successes} 成功, {failures} 失败")
        
        # 标记阶段完成
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
        """异步生成单个Stage 2样本"""
        async with self.semaphore:  # 限制并发数
            start_time = time.time()
            
            try:
                self._log(f"   📦 [{idx + 1}/{total}] 开始生成...")
                
                # 使用异步生成
                sample = await self._call_stage2_generator_async(async_client, nl_instruction)
                
                if sample:
                    # 添加到写入队列
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
                    self._log(f"      ✅ [{idx + 1}/{total}] 完成 ({elapsed:.1f}s)")
                    
                    # 更新统计
                    self.stats["successful_requests"] += 1
                    self.stats["total_time"] += elapsed
                    
                    return sample
                    
            except Exception as e:
                self._log(f"      ❌ [{idx + 1}/{total}] 失败: {e}")
                
                # 记录错误
                await self.write_queue.put((idx, None, str(e), stage_name))
                
                # 更新统计
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
        """异步生成单个Stage 3样本"""
        async with self.semaphore:  # 限制并发数
            start_time = time.time()
            
            try:
                self._log(f"   📦 [{idx + 1}/{total}] 开始生成...")
                
                # 转换为IRSample
                ir_sample = IRSample(
                    id=sample_dict.get("id", ""),
                    class_info=sample_dict.get("class", {}),
                    nl=sample_dict.get("nl", {}),
                    prerequisites=sample_dict.get("prerequisites", []),
                    schema_list=sample_dict.get("schema_list", []),
                    init_db=sample_dict.get("init_db"),
                    notes=sample_dict.get("notes", ""),
                )
                
                # 使用异步生成
                complete_sample = await self._call_stage3_generator_async(async_client, ir_sample)
                
                if complete_sample:
                    # 添加到写入队列
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
                    self._log(f"      ✅ [{idx + 1}/{total}] 完成 ({elapsed:.1f}s)")
                    
                    # 更新统计
                    self.stats["successful_requests"] += 1
                    self.stats["total_time"] += elapsed
                    
                    return complete_sample
                    
            except Exception as e:
                self._log(f"      ❌ [{idx + 1}/{total}] 失败: {e}")
                
                # 记录错误
                await self.write_queue.put((idx, None, str(e), stage_name))
                
                # 更新统计
                self.stats["failed_requests"] += 1
                
                return None
            finally:
                self.stats["total_requests"] += 1
    
    async def _call_stage2_generator_async(
        self,
        async_client: AsyncLLMClient,
        nl_instruction: Dict[str, Any],
    ) -> Optional[IRSample]:
        """调用 Stage2 生成器（异步版本）"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # 构建prompt（修复：使用正确的方法名）
                prompt = self.stage2_generator._build_single_prompt(nl_instruction)
                
                # 异步调用LLM
                response = await async_client.generate(prompt)
                
                # 解析响应（修复：传递正确的参数）
                sample = self.stage2_generator._parse_response(response.content, nl_instruction)
                
                if sample:
                    # 验证样本（修复：传递batch参数，None表示单个样本验证）
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
        """调用 Stage3 生成器（异步版本）"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # 构建prompt（修复：使用正确的方法名）
                prompt = self.stage3_generator._build_single_prompt(ir_sample)
                
                # 异步调用LLM
                response = await async_client.generate(prompt)
                
                # 解析响应
                complete_sample = self.stage3_generator._parse_response(
                    response.content,
                    ir_sample,
                )
                
                if complete_sample:
                    # 验证样本（修复：传递batch参数，None表示单个样本验证）
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
        """文件写入协程（确保顺序写入，批量更新checkpoint）"""
        checkpoint_batch_size = int(os.getenv("TEXT2MEM_BENCH_GEN_CHECKPOINT_BATCH", "10"))
        write_count = 0
        last_idx = -1
        
        with open(output_file, 'a', encoding='utf-8') as f:
            while True:
                item = await self.write_queue.get()
                
                if item is None:  # 结束信号
                    # 最后更新checkpoint（如果有未保存的进度）
                    if write_count > 0 and last_idx >= 0:
                        self.checkpoint_mgr.update_stage_progress(
                            stage_name,
                            completed_batches=last_idx + 1,
                        )
                    break
                
                idx, sample_dict, error, stage = item
                
                if sample_dict:
                    # 写入样本
                    f.write(json.dumps(sample_dict, ensure_ascii=False) + '\n')
                    f.flush()
                    
                    write_count += 1
                    last_idx = idx
                    
                    # 批量更新checkpoint（减少磁盘I/O）
                    if write_count % checkpoint_batch_size == 0:
                        self.checkpoint_mgr.update_stage_progress(
                            stage,
                            completed_batches=idx + 1,
                        )
                elif error:
                    # 错误立即记录
                    self.checkpoint_mgr.record_error(stage, idx, error)
                
                self.write_queue.task_done()
    
    def _format_stats(self) -> str:
        """格式化统计信息"""
        if self.stats["total_requests"] == 0:
            return ""
        
        avg_time = self.stats["total_time"] / self.stats["successful_requests"] \
            if self.stats["successful_requests"] > 0 else 0
        
        success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100
        
        return f"""
📊 统计信息:
   总请求数: {self.stats["total_requests"]}
   成功: {self.stats["successful_requests"]}
   失败: {self.stats["failed_requests"]}
   成功率: {success_rate:.1f}%
   平均耗时: {avg_time:.2f}s/样本
   总耗时: {self.stats["total_time"]:.1f}s
"""

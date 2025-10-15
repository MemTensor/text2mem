"""
Generation Controller - 生成流程主控制器
编排整个三阶段生成流程，支持断点恢复
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
    """生成控制器"""
    
    def __init__(
        self,
        plan_file: Path,
        resume: bool = True,
        verbose: bool = True,
    ):
        """
        Args:
            plan_file: 生成计划文件路径
            resume: 是否从断点恢复
            verbose: 是否详细输出
        """
        self.verbose = verbose
        
        # 加载计划
        self.plan = PlanLoader.load(plan_file)
        self._log(f"📋 加载计划: {self.plan.name}")
        
        # 验证计划
        errors = PlanLoader.validate_plan(self.plan)
        if errors:
            raise ValueError(f"配置验证失败:\n  " + "\n  ".join(errors))
        
        # 创建LLM客户端
        llm_config = LLMConfig.from_dict(self.plan.llm)
        self.llm_client = create_llm_client(llm_config)
        self._log(f"🤖 LLM: {llm_config.provider} / {llm_config.model}")
        
        # 测试连接
        if not self.llm_client.test_connection():
            raise ConnectionError("LLM连接测试失败")
        self._log("✅ LLM连接正常")
        
        # 创建任务分配器
        self.allocator = TaskAllocator(self.plan)
        
        # 初始化断点管理器
        checkpoint_file = Path(self.plan.checkpoint_file.format(plan_name=self.plan.name))
        self.checkpoint_mgr = CheckpointManager(checkpoint_file)
        
        # 加载或创建断点
        if resume and self.plan.resume_from_checkpoint:
            self.checkpoint = self.checkpoint_mgr.load()
            if self.checkpoint:
                self._log(f"📥 断点恢复: {self.checkpoint.progress_percentage:.1f}%")
            else:
                self.checkpoint = self._create_new_checkpoint()
        else:
            self.checkpoint = self._create_new_checkpoint()
        
        # 初始化生成器
        seeds_dir = Path(__file__).parent.parent / "seeds"
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        self.stage1_generator = Stage1Generator(self.llm_client, self.plan, seeds_dir)
        self.stage2_generator = Stage2Generator(self.llm_client, self.plan, prompts_dir, llm_config)
        self.stage3_generator = Stage3Generator(self.llm_client, self.plan, prompts_dir, llm_config)
        
        # 输出目录 - 直接输出到 data/raw/
        base_dir = self.plan.output.get("base_dir", "bench/data/raw")
        self.output_dir = Path(base_dir)
        
        # 创建带时间戳的运行目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_new_checkpoint(self) -> Checkpoint:
        """创建新断点"""
        self._log("🆕 创建新断点")
        checkpoint = self.checkpoint_mgr.create_new(
            self.plan.name,
            self.plan.total_samples,
        )
        
        # 初始化阶段进度
        for stage_name in ["stage1", "stage2", "stage3"]:
            if self.plan.stages.get(stage_name, {}).get("enabled", True):
                # 分配任务来计算批次数
                if stage_name == "stage1":
                    batches = self.allocator.allocate_tasks(stage_name)
                    total_batches = len(batches)
                else:
                    # Stage2和Stage3的批次数基于样本总数
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
        """输出日志"""
        if self.verbose:
            print(message)
    
    def run(self):
        """运行完整的生成流程"""
        self._log("\n" + "=" * 60)
        self._log(f"🚀 开始生成: {self.plan.name}")
        self._log("=" * 60)
        
        start_time = time.time()
        
        try:
            # Stage 1: NL指令生成
            stage1_output = None
            if self._should_run_stage("stage1"):
                self._log("\n📝 Stage 1: 生成NL指令...")
                stage1_output = self.run_stage1()
                self._log(f"✅ Stage 1 完成: {stage1_output}")
            else:
                self._log("\n⏭️  Stage 1: 已完成")
                stage1_output = self.checkpoint.output_files.get("stage1")
            
            # Stage 2: IR Schema生成
            stage2_output = None
            if self._should_run_stage("stage2"):
                self._log("\n🏗️  Stage 2: 生成IR Schema...")
                stage2_output = self._run_stage2(stage1_output)
                self._log(f"✅ Stage 2 完成: {stage2_output}")
            else:
                self._log("\n⏭️  Stage 2: 已完成")
                stage2_output = self.checkpoint.output_files.get("stage2")
            
            # Stage 3: Expected生成
            stage3_output = None
            if self._should_run_stage("stage3"):
                self._log("\n🎯 Stage 3: 生成Expected...")
                stage3_output = self._run_stage3(stage2_output)
                self._log(f"✅ Stage 3 完成: {stage3_output}")
            else:
                self._log("\n⏭️  Stage 3: 已完成")
            
            # 保存运行元数据
            self._save_metadata(stage1_output, stage2_output, stage3_output)
            
            # 完成
            elapsed = time.time() - start_time
            self._log("\n" + "=" * 60)
            self._log(f"✅ 生成完成，耗时 {elapsed:.1f}秒")
            self._log("=" * 60)
            
            # 打印摘要
            self._log("\n" + self.checkpoint_mgr.get_progress_summary())
            
        except KeyboardInterrupt:
            self._log("\n\n⚠️  用户中断")
            self._log("💾 进度已保存到断点")
            raise
        
        except Exception as e:
            self._log(f"\n\n❌ 生成失败: {e}")
            raise
    
    def _save_metadata(self, stage1_output: Optional[str], stage2_output: Optional[str], stage3_output: Optional[str]):
        """保存运行元数据到 metadata.json"""
        metadata = {
            "plan_name": self.plan.name,
            "timestamp": self.run_dir.name,  # 使用目录名作为时间戳
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
        
        self._log(f"\n   📋 元数据已保存: {metadata_file}")
    
    def _should_run_stage(self, stage_name: str) -> bool:
        """判断是否应该运行某个阶段"""
        stage_config = self.plan.stages.get(stage_name, {})
        
        # 检查是否启用
        if not stage_config.get("enabled", True):
            return False
        
        # 检查是否已完成
        stage_progress = self.checkpoint.stages.get(stage_name)
        if stage_progress and stage_progress.status == "completed":
            return False
        
        return True
    
    def run_stage1(self) -> str:
        """运行Stage 1: NL指令生成（增量保存版本）"""
        stage_name = "stage1"
        stage_progress = self.checkpoint.stages[stage_name]
        
        # 更新状态
        self.checkpoint_mgr.update_stage_progress(stage_name, status="running")
        
        # 分配任务
        batches = self.allocator.allocate_tasks(stage_name)
        self._log(f"   总批次: {len(batches)}")
        
        # 准备输出文件（使用 JSONL 格式以支持增量写入）
        # 输出到 run_dir/stage1.jsonl
        output_file = self.run_dir / "stage1.jsonl"
        
        # 如果从断点恢复，检查是否已有输出文件
        existing_output = self.checkpoint.output_files.get(stage_name)
        if existing_output and Path(existing_output).exists():
            output_file = Path(existing_output)
            self._log(f"   📥 恢复输出文件: {output_file}")
        else:
            # 更新checkpoint中的输出文件路径
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        # 打开文件用于追加
        mode = 'a' if output_file.exists() else 'w'
        
        # 处理每个批次
        for batch in batches:
            # 检查是否已完成
            if batch.batch_id < stage_progress.completed_batches:
                self._log(f"   ⏭️  批次 {batch.batch_id + 1}/{len(batches)}: 已完成")
                continue
            
            self._log(f"\n   📦 批次 {batch.batch_id + 1}/{len(batches)}")
            self._log(f"      场景: {batch.scenario}, 操作: {batch.operation}, 数量: {batch.count}")
            
            try:
                # 生成
                instructions = self.stage1_generator.generate_batch(batch)
                
                # 验证
                errors = self.stage1_generator.validate_instructions(instructions, batch)
                
                if errors:
                    validation_behavior = self.plan.validation.get("on_validation_error", "warn")
                    error_msg = "; ".join(errors[:3])
                    
                    if validation_behavior == "abort":
                        self._log(f"      ❌ 验证失败: {error_msg}")
                        raise ValueError(f"批次{batch.batch_id}验证失败: {error_msg}")
                    elif validation_behavior == "warn":
                        self._log(f"      ⚠️  验证警告: {error_msg}")
                
                # 实时写入到文件（每个批次完成后立即保存）
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
                
                # 更新进度
                self.checkpoint_mgr.update_stage_progress(
                    stage_name,
                    completed_batches=batch.batch_id + 1,
                )
                
                self.checkpoint_mgr.add_completed_samples(
                    count=len(instructions),
                    scenario=batch.scenario,
                    operation=batch.operation,
                )
                
                self._log(f"      ✅ 生成 {len(instructions)} 条指令（已保存到文件）")
                
                # 后续批次使用追加模式
                mode = 'a'
                
            except Exception as e:
                self._log(f"      ❌ 失败: {e}")
                self.checkpoint_mgr.mark_batch_failed(stage_name, batch.batch_id, str(e))
                
                if self.plan.validation.get("on_validation_error") == "abort":
                    raise
                continue
        
        # 更新checkpoint
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
            output_file=str(output_file),
        )
        
        self._log(f"\n   ✅ Stage 1 完成，输出文件: {output_file}")
        
        return str(output_file)
    
    def _run_stage2(self, stage1_output: Optional[str]) -> Optional[str]:
        """运行Stage 2: IR Schema生成（增量保存版本）"""
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
        
        # 准备输出文件 - 输出到 run_dir/stage2.jsonl
        output_file = self.run_dir / "stage2.jsonl"
        
        # 如果有现有输出文件且正在恢复，继续使用该文件
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 继续使用现有文件: {output_file}")
        else:
            self._log(f"   📂 输出文件: {output_file}")
            # 更新输出文件路径
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        sample_count = 0
        
        # 打开文件用于追加写入（增量保存）
        with open(output_file, 'a', encoding='utf-8') as f:
            for idx, nl_instruction in enumerate(nl_instructions):
                # 跳过已完成的样本
                if idx < stage_progress.completed_batches:
                    continue
                
                self._log(f"\n   📦 处理样本 {idx + 1}/{len(nl_instructions)}")
                
                try:
                    sample = self.stage2_generator.generate_single(nl_instruction)
                    
                    if sample:
                        # 立即写入文件（防止数据丢失）
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
                        f.flush()  # 强制写入磁盘
                        
                        sample_count += 1
                        self._log(f"      ✅ 生成并保存IR样本 (总计: {sample_count})")
                    
                    # 更新checkpoint进度
                    self.checkpoint_mgr.update_stage_progress(
                        stage_name,
                        completed_batches=idx + 1,
                    )
                    
                except Exception as e:
                    self._log(f"      ❌ 失败: {e}")
                    self.checkpoint_mgr.record_error(stage_name, idx, str(e))
                    continue
        
        # 标记阶段完成
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        self._log(f"\n   ✅ Stage 2完成: {sample_count} 个样本已保存")
        
        return str(output_file)
    
    def _run_stage3(self, stage2_output: Optional[str]) -> Optional[str]:
        """运行Stage 3: Expected生成（增量保存版本）"""
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
        # 准备输出文件 - 输出到 run_dir/stage3.jsonl
        output_file = self.run_dir / "stage3.jsonl"
        
        # 如果有现有输出文件且正在恢复，继续使用该文件
        if stage_progress.output_file and Path(stage_progress.output_file).exists():
            output_file = Path(stage_progress.output_file)
            self._log(f"   📂 继续使用现有文件: {output_file}")
        else:
            self._log(f"   📂 输出文件: {output_file}")
            # 更新输出文件路径
            self.checkpoint_mgr.update_stage_progress(
                stage_name,
                output_file=str(output_file),
            )
        
        sample_count = 0
        
        # 打开文件用于追加写入（增量保存）
        with open(output_file, 'a', encoding='utf-8') as f:
            for idx, sample_dict in enumerate(ir_samples_dict):
                # 跳过已完成的样本
                if idx < stage_progress.completed_batches:
                    continue
                
                self._log(f"\n   📦 处理样本 {idx + 1}/{len(ir_samples_dict)}")
                
                try:
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
                    
                    # 生成expected
                    complete_sample = self.stage3_generator.generate_single(ir_sample)
                    
                    if complete_sample:
                        # 立即写入文件（防止数据丢失）
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
                        f.flush()  # 强制写入磁盘
                        
                        sample_count += 1
                        self._log(f"      ✅ 生成并保存完整样本 (总计: {sample_count})")
                    
                    # 更新checkpoint进度
                    self.checkpoint_mgr.update_stage_progress(
                        stage_name,
                        completed_batches=idx + 1,
                    )
                    
                except Exception as e:
                    self._log(f"      ❌ 失败: {e}")
                    self.checkpoint_mgr.record_error(stage_name, idx, str(e))
                    continue
        
        # 标记阶段完成
        self.checkpoint_mgr.update_stage_progress(
            stage_name,
            status="completed",
        )
        
        self._log(f"\n   ✅ Stage 3完成: {sample_count} 个完整样本已保存")
        
        return str(output_file)
    
    def get_status(self) -> str:
        """获取当前状态"""
        return self.checkpoint_mgr.get_progress_summary()
    
    def reset(self):
        """重置生成进度"""
        self.checkpoint_mgr.delete()
        self._log("🗑️  断点已删除")


def main():
    """命令行入口"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Text2Mem Bench测试样本生成器")
    parser.add_argument(
        "--plan",
        type=str,
        default="bench/generate/config/generation_plan.yaml",
        help="生成计划文件路径",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="不从断点恢复（重新开始）",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示当前状态并退出",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置生成进度",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=True,
        help="详细输出",
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="使用异步并行生成（推荐，速度提升5-10倍）",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        help="最大并发数（默认：从环境变量 TEXT2MEM_BENCH_GEN_MAX_CONCURRENT 读取或5）",
    )
    
    args = parser.parse_args()
    
    # 检查是否应该使用异步模式
    use_async = args.use_async or os.getenv("TEXT2MEM_BENCH_GEN_USE_ASYNC", "").lower() in ("true", "1", "yes")
    
    try:
        if use_async:
            # 使用异步控制器
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
                print(f"❌ 异步模式需要 aiohttp: pip install aiohttp")
                print(f"   或使用同步模式（移除 --async 参数）")
                exit(1)
        else:
            # 使用同步控制器
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
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
数据结构迁移脚本

将旧的数据结构迁移到新的清晰结构
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def migrate_data_structure():
    """迁移数据结构"""
    
    bench_data = Path('bench/data')
    
    print("🔄 开始迁移数据结构...")
    print("="*60)
    
    # 1. 创建新目录结构
    print("\n1️⃣  创建新目录结构...")
    (bench_data / 'runs').mkdir(exist_ok=True)
    (bench_data / 'benchmarks').mkdir(exist_ok=True)
    (bench_data / 'archive').mkdir(exist_ok=True)
    print("   ✅ 已创建 runs/, benchmarks/, archive/")
    
    # 2. 迁移 raw/ 到 runs/
    print("\n2️⃣  迁移 raw/ → runs/...")
    old_raw = bench_data / 'raw'
    if old_raw.exists():
        for run_dir in old_raw.iterdir():
            if run_dir.is_dir():
                run_id = run_dir.name
                new_run_dir = bench_data / 'runs' / run_id
                
                if new_run_dir.exists():
                    print(f"   ⚠️  跳过已存在: {run_id}")
                    continue
                
                print(f"   📦 迁移: {run_id}")
                new_run_dir.mkdir(parents=True)
                
                # 迁移 stage3.jsonl
                old_stage3 = run_dir / 'stage3.jsonl'
                if old_stage3.exists():
                    stage3_dir = new_run_dir / 'stage3'
                    stage3_dir.mkdir(exist_ok=True)
                    shutil.copy2(old_stage3, stage3_dir / 'stage3.jsonl')
                    print(f"      ✅ stage3/stage3.jsonl")
                
                # 迁移 stage1.jsonl
                old_stage1 = run_dir / 'stage1.jsonl'
                if old_stage1.exists():
                    stage1_dir = new_run_dir / 'stage1'
                    stage1_dir.mkdir(exist_ok=True)
                    shutil.copy2(old_stage1, stage1_dir / 'stage1.jsonl')
                    print(f"      ✅ stage1/stage1.jsonl")
                
                # 迁移 stage2.jsonl
                old_stage2 = run_dir / 'stage2.jsonl'
                if old_stage2.exists():
                    stage2_dir = new_run_dir / 'stage2'
                    stage2_dir.mkdir(exist_ok=True)
                    shutil.copy2(old_stage2, stage2_dir / 'stage2.jsonl')
                    print(f"      ✅ stage2/stage2.jsonl")
                
                # 迁移 metadata.json
                old_metadata = run_dir / 'metadata.json'
                if old_metadata.exists():
                    shutil.copy2(old_metadata, new_run_dir / 'metadata.json')
                    print(f"      ✅ metadata.json")
                
                # 迁移 stats.json
                old_stats = run_dir / 'stats.json'
                if old_stats.exists():
                    stage3_dir = new_run_dir / 'stage3'
                    stage3_dir.mkdir(exist_ok=True)
                    shutil.copy2(old_stats, stage3_dir / 'stats.json')
                    print(f"      ✅ stage3/stats.json")
        
        print(f"   ✅ 已迁移 raw/")
    else:
        print("   ℹ️  raw/ 不存在，跳过")
    
    # 3. 迁移 benchmark/ 到 benchmarks/
    print("\n3️⃣  迁移 benchmark/ → benchmarks/...")
    old_benchmark = bench_data / 'benchmark'
    new_benchmarks = bench_data / 'benchmarks'
    
    if old_benchmark.exists() and not new_benchmarks.exists():
        shutil.move(str(old_benchmark), str(new_benchmarks))
        print("   ✅ 已迁移 benchmark/ → benchmarks/")
    elif old_benchmark.exists() and new_benchmarks.exists():
        # 合并
        for item in old_benchmark.iterdir():
            if item.name not in ['latest']:  # 跳过符号链接
                target = new_benchmarks / item.name
                if not target.exists():
                    shutil.copytree(item, target)
                    print(f"   ✅ 已合并: {item.name}")
        print("   ✅ 已合并 benchmark/ → benchmarks/")
    else:
        print("   ℹ️  benchmark/ 不存在或已迁移")
    
    # 4. 迁移 test_results/ 到对应的 runs/
    print("\n4️⃣  迁移 test_results/ → runs/.../tests/...")
    old_test_results = bench_data / 'test_results'
    if old_test_results.exists():
        for test_dir in old_test_results.iterdir():
            if test_dir.is_dir():
                run_id = test_dir.name
                run_dir = bench_data / 'runs' / run_id
                
                if not run_dir.exists():
                    print(f"   ⚠️  找不到对应run: {run_id}，跳过")
                    continue
                
                tests_dir = run_dir / 'tests'
                if tests_dir.exists():
                    print(f"   ⚠️  已存在tests: {run_id}，跳过")
                    continue
                
                print(f"   📦 迁移测试结果: {run_id}")
                tests_dir.mkdir()
                
                # 迁移文件，统一命名
                file_mapping = {
                    'summary.json': 'summary.json',
                    'passed_samples.jsonl': 'passed.jsonl',
                    'failed_samples.jsonl': 'failed.jsonl',
                    'all_results.jsonl': 'details.jsonl',
                    'stats.json': 'stats.json',
                }
                
                for old_name, new_name in file_mapping.items():
                    old_file = test_dir / old_name
                    if old_file.exists():
                        shutil.copy2(old_file, tests_dir / new_name)
                        print(f"      ✅ {new_name}")
        
        print("   ✅ 已迁移 test_results/")
    else:
        print("   ℹ️  test_results/ 不存在，跳过")
    
    # 5. 创建 latest 符号链接
    print("\n5️⃣  创建 latest 符号链接...")
    runs_dir = bench_data / 'runs'
    if runs_dir.exists():
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], 
                         key=lambda x: x.name, reverse=True)
        if run_dirs:
            latest_run = runs_dir / 'latest'
            if latest_run.exists() or latest_run.is_symlink():
                latest_run.unlink()
            latest_run.symlink_to(run_dirs[0].name)
            print(f"   ✅ runs/latest → {run_dirs[0].name}")
    
    # 6. 生成迁移报告
    print("\n6️⃣  生成迁移报告...")
    report = {
        'migrated_at': datetime.now().isoformat(),
        'runs_migrated': [],
        'benchmarks_migrated': [],
    }
    
    runs_dir = bench_data / 'runs'
    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir()):
            if run_dir.is_dir():
                report['runs_migrated'].append({
                    'run_id': run_dir.name,
                    'has_stage1': (run_dir / 'stage1' / 'stage1.jsonl').exists(),
                    'has_stage2': (run_dir / 'stage2' / 'stage2.jsonl').exists(),
                    'has_stage3': (run_dir / 'stage3' / 'stage3.jsonl').exists(),
                    'has_tests': (run_dir / 'tests').exists(),
                })
    
    benchmarks_dir = bench_data / 'benchmarks'
    if benchmarks_dir.exists():
        for bm_dir in sorted(benchmarks_dir.iterdir()):
            if bm_dir.is_dir():
                report['benchmarks_migrated'].append(bm_dir.name)
    
    report_file = bench_data / 'migration_report.json'
    with report_file.open('w') as f:
        json.dump(report, f, indent=2)
    print(f"   ✅ 已保存: {report_file}")
    
    # 7. 总结
    print("\n" + "="*60)
    print("✅ 迁移完成！")
    print("="*60)
    print(f"📊 迁移统计:")
    print(f"   - Runs: {len(report['runs_migrated'])}")
    print(f"   - Benchmarks: {len(report['benchmarks_migrated'])}")
    
    print(f"\n📁 新目录结构:")
    print(f"   bench/data/")
    print(f"   ├── runs/          ({len(report['runs_migrated'])} runs)")
    print(f"   ├── benchmarks/    ({len(report['benchmarks_migrated'])} versions)")
    print(f"   ├── schemas/")
    print(f"   └── archive/")
    
    print(f"\n💡 下一步:")
    print(f"   1. 检查迁移结果: ls -la bench/data/runs/")
    print(f"   2. 删除旧目录: rm -rf bench/data/raw bench/data/test_data bench/data/test_results")
    print(f"   3. 更新工具使用新结构")
    
    return report


if __name__ == '__main__':
    import sys
    import os
    
    # 确保在项目根目录运行
    if not Path('bench/data').exists():
        print("❌ 请在项目根目录运行此脚本")
        print(f"   当前目录: {os.getcwd()}")
        print(f"   应该在: /home/hanyu/Text2Mem/")
        sys.exit(1)
    
    try:
        report = migrate_data_structure()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

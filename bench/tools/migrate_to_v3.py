#!/usr/bin/env python3
"""
迁移到v3数据结构

将现有数据从旧结构迁移到新的v3结构：
- runs/ → raw/ (stage数据)
- runs/ 清空，等待从raw创建

新结构：
- raw/: 原始生成输出
- runs/: 测试+清洗后的数据（从raw创建）
- benchmarks/: 最终benchmark
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def migrate_to_v3():
    """迁移到v3结构"""
    
    data_dir = Path('bench/data')
    
    print("🔄 开始迁移到v3数据结构...")
    print("="*60)
    
    # 1. 创建raw目录
    print("\n1️⃣  创建raw/目录...")
    raw_dir = data_dir / 'raw'
    raw_dir.mkdir(exist_ok=True)
    print("   ✅ 已创建 raw/")
    
    # 2. 将runs/中的stage数据迁移到raw/
    print("\n2️⃣  迁移stage数据到raw/...")
    runs_dir = data_dir / 'runs'
    
    if runs_dir.exists():
        for run_item in runs_dir.iterdir():
            if not run_item.is_dir() or run_item.name == 'latest':
                continue
            
            run_id = run_item.name
            print(f"   📦 处理run: {run_id}")
            
            # 创建raw目录
            raw_item = raw_dir / run_id
            raw_item.mkdir(exist_ok=True)
            
            # 迁移stage1/2/3数据
            for stage_num in [1, 2, 3]:
                # 旧位置：runs/RUN_ID/stageN/stageN.jsonl
                old_stage_dir = run_item / f'stage{stage_num}'
                old_stage_file = old_stage_dir / f'stage{stage_num}.jsonl'
                
                # 新位置：raw/RUN_ID/stageN.jsonl
                new_stage_file = raw_item / f'stage{stage_num}.jsonl'
                
                if old_stage_file.exists():
                    shutil.copy2(old_stage_file, new_stage_file)
                    print(f"      ✅ stage{stage_num}.jsonl")
            
            # 迁移metadata.json
            old_metadata = run_item / 'metadata.json'
            new_metadata = raw_item / 'metadata.json'
            if old_metadata.exists():
                shutil.copy2(old_metadata, new_metadata)
                print(f"      ✅ metadata.json")
    
    print("   ✅ 已迁移所有stage数据到raw/")
    
    # 3. 清空runs目录（保留目录结构以便重新创建）
    print("\n3️⃣  清理runs/目录...")
    if runs_dir.exists():
        # 删除所有内容
        for item in runs_dir.iterdir():
            if item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print("   ✅ 已清空runs/目录")
    
    # 4. 确保benchmarks目录存在
    print("\n4️⃣  确保benchmarks/目录存在...")
    benchmarks_dir = data_dir / 'benchmarks'
    benchmarks_dir.mkdir(exist_ok=True)
    print("   ✅ benchmarks/目录已就绪")
    
    # 5. 生成迁移报告
    print("\n5️⃣  生成迁移报告...")
    report = {
        'migrated_at': datetime.now().isoformat(),
        'raws_created': [],
    }
    
    if raw_dir.exists():
        for item in raw_dir.iterdir():
            if item.is_dir():
                report['raws_created'].append({
                    'raw_id': item.name,
                    'has_stage1': (item / 'stage1.jsonl').exists(),
                    'has_stage2': (item / 'stage2.jsonl').exists(),
                    'has_stage3': (item / 'stage3.jsonl').exists(),
                })
    
    report_file = data_dir / 'migration_v3_report.json'
    with report_file.open('w') as f:
        json.dump(report, f, indent=2)
    print(f"   ✅ 已保存: {report_file}")
    
    # 6. 总结
    print("\n" + "="*60)
    print("✅ 迁移到v3完成！")
    print("="*60)
    print(f"📊 迁移统计:")
    print(f"   - Raws创建: {len(report['raws_created'])}")
    
    print(f"\n📁 新目录结构:")
    print(f"   bench/data/")
    print(f"   ├── raw/          ({len(report['raws_created'])} raws)")
    print(f"   ├── runs/         (空，等待从raw创建)")
    print(f"   └── benchmarks/   (保持不变)")
    
    print(f"\n💡 下一步:")
    print(f"   1. 从raw创建run并测试:")
    print(f"      python -m bench.tools.test --raw latest")
    print(f"   2. 或使用pipeline:")
    print(f"      python -m bench.tools.pipeline --raw latest --version v2")
    
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
        report = migrate_to_v3()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

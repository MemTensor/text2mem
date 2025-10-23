#!/usr/bin/env python3
"""
验证Bench工具设置

检查所有工具是否正常工作
"""

import sys
from pathlib import Path

def test_imports():
    """测试模块导入"""
    print("1️⃣  测试模块导入...")
    
    try:
        from bench.tools import run_manager
        print("  ✅ run_manager")
    except ImportError as e:
        print(f"  ❌ run_manager: {e}")
        return False
    
    try:
        from bench.tools import stats
        print("  ✅ stats")
    except ImportError as e:
        print(f"  ❌ stats: {e}")
        return False
    
    try:
        from bench.tools import test
        print("  ✅ test")
    except ImportError as e:
        print(f"  ❌ test: {e}")
        return False
    
    try:
        from bench.tools import clean
        print("  ✅ clean")
    except ImportError as e:
        print(f"  ❌ clean: {e}")
        return False
    
    try:
        from bench.tools import build
        print("  ✅ build")
    except ImportError as e:
        print(f"  ❌ build: {e}")
        return False
    
    try:
        from bench.tools import pipeline
        print("  ✅ pipeline")
    except ImportError as e:
        print(f"  ❌ pipeline: {e}")
        return False
    
    return True

def test_data_structure():
    """测试数据结构"""
    print("\n2️⃣  测试数据结构...")
    
    base = Path('bench/data')
    
    dirs = ['runs', 'benchmarks', 'schemas', 'archive']
    for d in dirs:
        path = base / d
        if path.exists():
            print(f"  ✅ {d}/")
        else:
            print(f"  ⚠️  {d}/ (不存在，将自动创建)")
    
    return True

def test_run_manager():
    """测试RunManager"""
    print("\n3️⃣  测试RunManager...")
    
    try:
        from bench.tools.run_manager import RunManager
        
        manager = RunManager()
        print(f"  ✅ 创建RunManager")
        
        runs = manager.list_runs()
        print(f"  ✅ 找到 {len(runs)} 个runs")
        
        if runs:
            latest = manager.get_latest_run()
            print(f"  ✅ Latest run: {latest}")
            
            status = manager.get_run_status(latest)
            print(f"  ✅ Run状态: {status}")
        
        benchmarks = manager.list_benchmarks()
        print(f"  ✅ 找到 {len(benchmarks)} 个benchmark版本")
        
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False

def test_tools():
    """测试工具命令"""
    print("\n4️⃣  测试工具命令...")
    
    import subprocess
    
    tools = [
        'stats',
        'test',
        'clean',
        'build',
        'pipeline',
    ]
    
    for tool in tools:
        try:
            result = subprocess.run(
                ['python', '-m', f'bench.tools.{tool}', '--help'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ✅ bench.tools.{tool}")
            else:
                print(f"  ❌ bench.tools.{tool}: 返回码 {result.returncode}")
                return False
        except Exception as e:
            print(f"  ❌ bench.tools.{tool}: {e}")
            return False
    
    return True

def main():
    print("="*60)
    print("🔍 Bench工具验证")
    print("="*60)
    
    tests = [
        ("模块导入", test_imports),
        ("数据结构", test_data_structure),
        ("RunManager", test_run_manager),
        ("工具命令", test_tools),
    ]
    
    all_passed = True
    for name, test_func in tests:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有测试通过！")
        print("="*60)
        print("\n💡 下一步:")
        print("   # 查看使用指南")
        print("   cat bench/COMPLETE_GUIDE.md")
        return 0
    else:
        print("❌ 部分测试失败")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())

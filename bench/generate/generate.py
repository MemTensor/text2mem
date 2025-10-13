#!/usr/bin/env python3
"""
Text2Mem Bench Sample Generator CLI
测试样本生成命令行工具
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bench.generate.src.generation_controller import main

if __name__ == "__main__":
    main()

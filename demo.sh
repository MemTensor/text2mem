#!/usr/bin/env bash
# 这是一个简单的脚本，用于启动Text2Mem演示

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 进入项目目录
cd "$SCRIPT_DIR"

# 执行Python脚本
python scripts/new/run_text2mem_demo.py "$@"

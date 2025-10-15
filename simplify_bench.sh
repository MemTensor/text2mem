#!/bin/bash
#
# Bench 目录简化脚本
# 用途：简化 bench/data 目录结构，保留 schemas、raw、test_data、benchmark
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BENCH_DIR="/home/hanyu/Text2Mem/bench"
DRY_RUN=false
BACKUP=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --backup) BACKUP=true; shift ;;
        --execute) DRY_RUN=false; shift ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run|--backup|--execute]"
            exit 1
            ;;
    esac
done

if [ "$DRY_RUN" = false ] && [ "$BACKUP" = false ]; then
    echo -e "${YELLOW}Warning: No option specified, defaulting to --dry-run${NC}"
    DRY_RUN=true
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Bench 目录简化脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - 仅显示将要执行的操作${NC}"
else
    echo -e "${RED}⚠️  EXECUTE MODE - 将真实执行所有操作${NC}"
fi
echo ""

run_cmd() {
    local cmd="$1"
    local desc="$2"
    
    if [ -n "$desc" ]; then
        echo -e "  ${GREEN}→${NC} $desc"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "    ${YELLOW}[DRY RUN]${NC} $cmd"
    else
        echo -e "    ${BLUE}[EXEC]${NC} $cmd"
        eval "$cmd"
    fi
}

# ============================================================
# Step 0: 备份
# ============================================================
if [ "$BACKUP" = true ] && [ "$DRY_RUN" = false ]; then
    echo -e "${YELLOW}📦 Step 0: 创建备份${NC}"
    BACKUP_DIR="/home/hanyu/Text2Mem/bench_backup_$(date +%Y%m%d_%H%M%S)"
    run_cmd "mkdir -p $BACKUP_DIR" "创建备份目录"
    
    # 备份重要数据
    if [ -f "$BENCH_DIR/data/benchmark/v1/benchmark.jsonl" ]; then
        run_cmd "cp $BENCH_DIR/data/benchmark/v1/benchmark.jsonl $BACKUP_DIR/" "备份 benchmark.jsonl"
    fi
    
    if [ -f "$BENCH_DIR/data/test_data/test_data.jsonl" ]; then
        run_cmd "cp $BENCH_DIR/data/test_data/test_data.jsonl $BACKUP_DIR/" "备份 test_data.jsonl"
    fi
    
    echo -e "  ${GREEN}✓${NC} 备份到: $BACKUP_DIR"
    echo ""
fi

# ============================================================
# Step 1: 清理重复和无用目录
# ============================================================
echo -e "${YELLOW}🗑️  Step 1: 清理重复和无用目录${NC}"

# 删除 v1/ 目录（重复数据）
if [ -d "$BENCH_DIR/data/v1" ]; then
    run_cmd "rm -rf $BENCH_DIR/data/v1" "删除重复的 data/v1/ 目录 (~3.7MB)"
fi

# 删除 processed/ 目录（从未使用）
if [ -d "$BENCH_DIR/data/processed" ]; then
    run_cmd "rm -rf $BENCH_DIR/data/processed" "删除空的 data/processed/ 目录"
fi

# 删除 benchmark/ 下的重复文件
if [ -f "$BENCH_DIR/data/benchmark/benchmark.jsonl" ]; then
    run_cmd "rm -f $BENCH_DIR/data/benchmark/benchmark.jsonl" "删除重复的 benchmark.jsonl"
fi

echo -e "  ${GREEN}✓${NC} 重复数据清理完成"
echo ""

# ============================================================
# Step 2: 重命名目录（保持一致性）
# ============================================================
echo -e "${YELLOW}📁 Step 2: 重命名目录${NC}"

# 重命名 schema -> schemas
if [ -d "$BENCH_DIR/data/schema" ] && [ ! -d "$BENCH_DIR/data/schemas" ]; then
    run_cmd "mv $BENCH_DIR/data/schema $BENCH_DIR/data/schemas" "重命名 schema/ → schemas/"
fi

echo -e "  ${GREEN}✓${NC} 目录重命名完成"
echo ""

# ============================================================
# Step 3: 创建必要的目录结构
# ============================================================
echo -e "${YELLOW}📂 Step 3: 确保目录结构完整${NC}"

run_cmd "mkdir -p $BENCH_DIR/data/schemas" "确保 schemas/ 存在"
run_cmd "mkdir -p $BENCH_DIR/data/raw" "确保 raw/ 存在"
run_cmd "mkdir -p $BENCH_DIR/data/test_data" "确保 test_data/ 存在"
run_cmd "mkdir -p $BENCH_DIR/data/benchmark/v1" "确保 benchmark/v1/ 存在"

# 创建或更新 latest 符号链接
if [ -d "$BENCH_DIR/data/benchmark/v1" ]; then
    if [ "$DRY_RUN" = false ]; then
        cd "$BENCH_DIR/data/benchmark"
        if [ -L "latest" ]; then
            rm -f latest
        fi
        ln -sf v1 latest
        cd - > /dev/null
        echo -e "  ${GREEN}→${NC} 创建符号链接: benchmark/latest → v1"
    else
        echo -e "  ${YELLOW}[DRY RUN]${NC} 创建符号链接: benchmark/latest → v1"
    fi
fi

echo -e "  ${GREEN}✓${NC} 目录结构完成"
echo ""

# ============================================================
# Step 4: 创建 .gitignore（建议）
# ============================================================
echo -e "${YELLOW}📝 Step 4: 创建 .gitignore${NC}"

GITIGNORE_CONTENT="# 生成的原始数据（保留最近3-5次）
raw/*/

# 中间测试数据（可重新生成）
test_data/test_data.jsonl

# 临时文件
*.tmp
*.bak
.DS_Store
"

if [ "$DRY_RUN" = false ]; then
    if [ ! -f "$BENCH_DIR/data/.gitignore" ]; then
        echo "$GITIGNORE_CONTENT" > "$BENCH_DIR/data/.gitignore"
        echo -e "  ${GREEN}→${NC} 创建 data/.gitignore"
    else
        echo -e "  ${YELLOW}→${NC} data/.gitignore 已存在，跳过"
    fi
else
    echo -e "  ${YELLOW}[DRY RUN]${NC} 创建 data/.gitignore"
fi

echo -e "  ${GREEN}✓${NC} .gitignore 配置完成"
echo ""

# ============================================================
# 完成
# ============================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 简化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}这是 DRY RUN 模式，没有实际执行任何操作。${NC}"
    echo ""
    echo -e "如果确认无误，请运行："
    echo -e "  ${BLUE}$0 --execute${NC}    # 直接执行"
    echo -e "  ${BLUE}$0 --backup${NC}     # 先备份再执行（推荐）"
else
    echo -e "📝 简化后的目录结构："
    echo ""
    echo -e "data/"
    echo -e "├── schemas/          # Schema定义"
    echo -e "├── raw/              # 原始生成输出"
    echo -e "├── test_data/        # 测试数据"
    echo -e "└── benchmark/        # 最终benchmark"
    echo -e "    ├── v1/"
    echo -e "    └── latest -> v1/"
    echo ""
    echo -e "${YELLOW}下一步：${NC}"
    echo -e "1. 更新代码中的路径引用（参考 SIMPLIFIED_STRUCTURE.md）"
    echo -e "2. 测试生成工具：python bench/generate/generate.py --help"
    echo -e "3. 测试清洗工具：python bench/tools/clean_benchmark.py --help"
    echo ""
fi

echo -e "详细文档: ${BLUE}bench/SIMPLIFIED_STRUCTURE.md${NC}"
echo ""

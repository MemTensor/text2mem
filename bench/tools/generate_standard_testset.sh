#!/bin/bash
#
# 快速生成Text2Mem Bench标准测试集
#
# Usage:
#   ./bench/tools/generate_standard_testset.sh
#

set -e  # 出错时退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Text2Mem Bench 标准测试集生成器${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 设置路径
PROJECT_ROOT="/home/hanyu/Text2Mem"
TEST_DIR="$PROJECT_ROOT/bench/data/v1/test_samples"
TEMP_DIR="$TEST_DIR/temp"
BUILDER="$PROJECT_ROOT/bench/tools/test_sample_builder.py"

# 创建目录
echo -e "${YELLOW}1. 创建目录...${NC}"
mkdir -p "$TEST_DIR"
mkdir -p "$TEMP_DIR"

# 清理旧文件
echo -e "${YELLOW}2. 清理旧文件...${NC}"
rm -f "$TEMP_DIR"/*.jsonl
rm -f "$TEST_DIR"/basic.jsonl.bak

# 备份现有文件
if [ -f "$TEST_DIR/basic.jsonl" ]; then
    echo -e "${YELLOW}   备份现有 basic.jsonl...${NC}"
    cp "$TEST_DIR/basic.jsonl" "$TEST_DIR/basic.jsonl.bak"
fi

echo ""
echo -e "${YELLOW}3. 生成测试样本...${NC}"

# 定义操作和数量
declare -A operations=(
    ["encode"]=2
    ["retrieve"]=2
    ["update"]=2
    ["delete"]=2
    ["label"]=2
    ["promote"]=2
    ["demote"]=2
    ["lock"]=2
    ["summarize"]=2
)

total=0
seq=1

for op in "${!operations[@]}"; do
    count=${operations[$op]}
    echo -e "   ${GREEN}✓${NC} 生成 $op 测试 (x$count, 中英文)..."
    
    python "$BUILDER" generate \
        --template "$op" \
        --count "$count" \
        --lang both \
        --start-seq "$seq" \
        --output "$TEMP_DIR/${op}_tests.jsonl" 2>&1 | grep -v "^$" || true
    
    # 更新序号和计数
    ((seq += count * 2))  # 每个count生成2个样本（中文+英文）
    ((total += count * 2))
done

echo ""
echo -e "${YELLOW}4. 合并测试文件...${NC}"

# 合并所有测试文件
cat "$TEMP_DIR"/*.jsonl > "$TEST_DIR/basic.jsonl"

echo -e "   ${GREEN}✓${NC} 已合并 $total 个测试样本到 basic.jsonl"

echo ""
echo -e "${YELLOW}5. 验证测试样本...${NC}"

# 验证生成的文件
python "$BUILDER" validate --input "$TEST_DIR/basic.jsonl"

# 清理临时文件
echo ""
echo -e "${YELLOW}6. 清理临时文件...${NC}"
rm -rf "$TEMP_DIR"
echo -e "   ${GREEN}✓${NC} 临时文件已清理"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 测试集生成完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 统计信息:"
echo "  - 总样本数: $total"
echo "  - 文件位置: $TEST_DIR/basic.jsonl"
echo ""
echo "📝 下一步:"
echo "  1. 查看生成的测试: cat $TEST_DIR/basic.jsonl | jq ."
echo "  2. 运行测试: python -m bench run --split basic"
echo "  3. 列出测试: python -m bench list --split basic"
echo ""

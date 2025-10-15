#!/bin/bash
#
# Bench 完整流程脚本
# 从生成到测试的一键执行
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Bench 完整流程${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. 生成样本
echo ""
echo -e "${YELLOW}1️⃣  生成测试样本...${NC}"
python bench/generate/generate.py

# 2. 获取最新生成
LATEST=$(ls -t bench/data/raw | head -1)
echo ""
echo -e "${GREEN}2️⃣  最新生成: $LATEST${NC}"

# 3. 更新测试数据
echo ""
echo -e "${YELLOW}3️⃣  更新测试数据...${NC}"
cp bench/data/raw/$LATEST/stage3.jsonl bench/data/test_data/test_data.jsonl
SAMPLES=$(wc -l < bench/data/test_data/test_data.jsonl)
echo -e "   ${GREEN}✅ 测试数据已更新 ($SAMPLES 个样本)${NC}"

# 4. 清洗 benchmark
echo ""
echo -e "${YELLOW}4️⃣  清洗 benchmark...${NC}"
python bench/tools/clean_benchmark.py
BENCHMARK_SAMPLES=$(wc -l < bench/data/benchmark/v1/benchmark.jsonl)
echo -e "   ${GREEN}✅ Benchmark 已生成 ($BENCHMARK_SAMPLES 个样本)${NC}"

# 5. 运行测试
echo ""
echo -e "${YELLOW}5️⃣  运行测试...${NC}"
python -m bench run --split basic --verbose

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 流程完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "📊 统计信息:"
echo -e "   原始样本: $SAMPLES"
echo -e "   清洗后: $BENCHMARK_SAMPLES"
echo -e "   过滤率: $(echo "scale=2; (1 - $BENCHMARK_SAMPLES / $SAMPLES) * 100" | bc)%"
echo ""
echo -e "📁 输出位置:"
echo -e "   Raw 数据: bench/data/raw/$LATEST/"
echo -e "   Benchmark: bench/data/benchmark/v1/benchmark.jsonl"
echo -e "   测试结果: bench/output/test_results/ (最新)"
echo ""

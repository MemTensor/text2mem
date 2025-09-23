# Text2Mem 环境配置指南

Text2Mem 使用 Miniconda 管理依赖，项目配置使用 pyproject.toml。自 v0.2 起，模型 Provider 与 Service 分离：Provider 只负责模型接口；Service 负责编排高阶能力。建议通过 `service_factory` 统一创建模型服务。

## 方法一：使用 setup.sh 脚本（推荐，仅 Linux/macOS）

```bash
# 克隆仓库
git clone https://github.com/yourusername/Text2Mem.git
cd Text2Mem

# 运行安装脚本
bash setup.sh
```

## 方法二：手动使用 conda 命令（适用于所有平台）

```bash
# 克隆仓库
git clone https://github.com/yourusername/Text2Mem.git
cd Text2Mem

# 创建并激活环境
conda env create -f environment.yml
conda activate text2mem
```

## 方法三：不使用 conda 的安装方式（可选）

如果您不想使用 conda，可以直接使用 pip 和 pyproject.toml：

```bash
# 克隆仓库
git clone https://github.com/yourusername/Text2Mem.git
cd Text2Mem

# 创建虚拟环境（可选）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

# 安装项目及其依赖
pip install -e .
```

## 项目配置文件说明

- `pyproject.toml`: 主要的项目配置文件，包含所有项目元数据和依赖配置
- `environment.yml`: Conda 环境配置，使用 pyproject.toml 中的依赖
- `requirements.txt`: (已弃用) 仅保留用于兼容旧版工具链

## 运行示例

```bash
# 列出所有可用示例
python run_demo.py --list

# 运行所有示例
python run_demo.py --verbose

# 运行特定示例
python run_demo.py --file sample_ir_encode.json

# 运行工作流
python run_workflow.py text2mem/examples/workflow_project_management.json

## 编程式创建模型服务（可选）

```python
from text2mem.services.service_factory import create_models_service
from text2mem.adapters.sqlite_adapter import SQLiteAdapter
from text2mem.core.engine import Text2MemEngine

service = create_models_service(mode="auto")
adapter = SQLiteAdapter("./text2mem.db", models_service=service)
engine = Text2MemEngine(adapter=adapter, models_service=service)
```
```

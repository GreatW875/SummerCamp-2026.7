#!/usr/bin/env bash
# ============================================================
# 运动分析项目 - Conda 环境创建脚本
# 运行环境: Ubuntu 22.04
# ============================================================
set -euo pipefail

ENV_NAME="sport_reco"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================"
echo "  运动分析 Web 应用 - 环境初始化"
echo "============================================"
echo ""

# ---- 检查 conda 是否可用 ----
if ! command -v conda &> /dev/null; then
    echo "[ERROR] conda 未安装，请先安装 Miniconda 或 Anaconda"
    echo "  安装指引: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "[INFO] Conda 路径: $(which conda)"
echo "[INFO] Conda 版本: $(conda --version)"

# ---- 创建环境 ----
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "[WARN] 环境 '${ENV_NAME}' 已存在，将尝试更新依赖..."
    conda env update -f "${PROJECT_ROOT}/environment.yml" --prune
else
    echo "[INFO] 正在创建新环境 '${ENV_NAME}'..."
    conda env create -f "${PROJECT_ROOT}/environment.yml"
fi

# ---- 激活并验证 ----
echo ""
echo "[INFO] 验证环境..."
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

echo "[INFO] Python 版本: $(python --version)"
echo "[INFO] 核心依赖版本检查:"
python -c "
from importlib.metadata import version
print(f'  Flask          = {version(\"flask\")}')
print(f'  Flask-SocketIO = {version(\"flask-socketio\")}')
import numpy as np;     print(f'  NumPy          = {np.__version__}')
import pandas as pd;    print(f'  Pandas         = {pd.__version__}')
import scipy;           print(f'  SciPy          = {scipy.__version__}')
import sklearn;         print(f'  Scikit-learn   = {sklearn.__version__}')
import matplotlib;      print(f'  Matplotlib     = {matplotlib.__version__}')
import yaml;            print(f'  PyYAML         = {yaml.__version__}')
import gevent;          print(f'  gevent         = {gevent.__version__}')
"

echo ""
echo "============================================"
echo "  环境初始化完成！"
echo "  激活环境: conda activate ${ENV_NAME}"
echo "  启动应用: cd ${PROJECT_ROOT} && bash scripts/run_dev.sh"
echo "============================================"

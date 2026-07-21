#!/usr/bin/env bash
# ============================================================
# 运动分析项目 - 开发服务器启动脚本
# ============================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ---- 获取本机 IP ----
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "${LOCAL_IP}" ]; then
    LOCAL_IP="127.0.0.1"
fi

# ---- 生成/检查 SSL 证书（传入 LAN IP 以加入 SAN） ----
bash "${PROJECT_ROOT}/scripts/gen_ssl.sh" "${LOCAL_IP}"

# ---- 创建必要目录 ----
mkdir -p "${PROJECT_ROOT}/logs"
mkdir -p "${PROJECT_ROOT}/data/raw"
mkdir -p "${PROJECT_ROOT}/data/processed"
mkdir -p "${PROJECT_ROOT}/artifacts/models"

# ---- 启动说明 ----
echo ""
echo "============================================"
echo "  🏃 运动分析 Web 应用"
echo "============================================"
echo "  开发机 IP: ${LOCAL_IP}"
echo ""
echo "  📱 手机端 (传感器采集):"
echo "     https://${LOCAL_IP}:5000/mobile"
echo ""
echo "  🖥  电脑端 (监控 Dashboard):"
echo "     https://${LOCAL_IP}:5000/"
echo "============================================"
echo ""

# ---- 激活 conda 并启动 ----
eval "$(conda shell.bash hook)" 2>/dev/null || true
if command -v conda &> /dev/null; then
    conda activate sport_reco 2>/dev/null || echo "[WARN] 请先运行: conda activate sport_reco"
fi

# ---- 启动 Flask ----
export SPORT_RECO_ENV="dev"
cd "${PROJECT_ROOT}"
python -m src.app \
    --host 0.0.0.0 \
    --port 5000 \
    --cert "${PROJECT_ROOT}/ssl/cert.pem" \
    --key "${PROJECT_ROOT}/ssl/key.pem"

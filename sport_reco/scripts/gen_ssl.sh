#!/usr/bin/env bash
# ============================================================
# 运动分析项目 - 自签名 SSL 证书生成
# 移动端 DeviceMotion API 需要 HTTPS
# 用法: bash gen_ssl.sh [LAN_IP]
#       LAN_IP 可选，默认为 127.0.0.1
# ============================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERT_DIR="${PROJECT_ROOT}/ssl"
CERT_FILE="${CERT_DIR}/cert.pem"
KEY_FILE="${CERT_DIR}/key.pem"

# 接受的 LAN IP 参数（用于手机访问）
LAN_IP="${1:-127.0.0.1}"

mkdir -p "${CERT_DIR}"

# 检查已有证书是否包含当前 LAN IP，如果不包含则重新生成
NEED_REGENERATE=false
if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    if openssl x509 -in "${CERT_FILE}" -text -noout 2>/dev/null | grep -q "IP Address:${LAN_IP}"; then
        echo "[INFO] SSL 证书已存在且包含 IP ${LAN_IP}，跳过生成"
        echo "  证书路径: ${CERT_FILE}"
        echo "  密钥路径: ${KEY_FILE}"
        exit 0
    else
        echo "[INFO] 已有证书不含 IP ${LAN_IP}，重新生成..."
        NEED_REGENERATE=true
    fi
fi

echo "[INFO] 生成自签名 SSL 证书 (CN=${LAN_IP}, SAN=IP:${LAN_IP},IP:127.0.0.1,DNS:localhost)..."

# ── Bug 修复: CN 使用 LAN_IP 而非 localhost ──
# 原实现 CN=localhost，但用户实际通过 IP 访问。
# 在部分移动浏览器（Chrome Android, Safari iOS）中，
# 当 CN 与访问地址不匹配时，即使 SAN 包含正确 IP，
# WebSocket 升级握手也可能被拒绝。
# 修复后 CN 与访问 IP 一致，大幅提升移动端兼容性。
openssl req -x509 -newkey rsa:4096 \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -days 365 -nodes \
    -subj "/CN=${LAN_IP}/O=SportReco/C=CN" \
    -addext "subjectAltName=IP:${LAN_IP},IP:127.0.0.1,DNS:localhost" 2>/dev/null

echo "[INFO] 证书生成完毕"
echo "  证书: ${CERT_FILE}"
echo "  密钥: ${KEY_FILE}"
echo ""
echo "  ⚠ 注意: 手机浏览器访问时需要手动信任此证书"
echo "    在手机浏览器中访问 https://${LAN_IP}:5000/mobile"
echo "    并选择「继续访问」/「高级→继续前往」"
echo ""

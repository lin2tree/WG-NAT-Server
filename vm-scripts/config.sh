#!/bin/bash
#
# WireGuard VPN 配置文件
# 请根据实际情况修改以下配置项
#
# 作者: FCloudVPN Team
# 版本: 1.0.0
# 更新日期: 2026-04-17
#

# ==================== VPN 管理服务配置 ====================

# VPN 管理服务的 API 地址
# 格式: http://服务器IP:端口
# 示例: http://192.168.1.10:8000
VPN_SERVER_URL="http://YOUR_SERVER_IP:8000"

# 虚拟机认证令牌
# 从 VPN 管理服务的环境变量 VM_TOKEN 获取
# 此令牌用于验证虚拟机的合法身份
VM_TOKEN="YOUR_VM_TOKEN_HERE"

# ==================== WireGuard 配置 ====================

# WireGuard 接口名称
WG_INTERFACE="wg0"

# WireGuard 监听端口
# 默认使用 2588 端口
WG_PORT=2588

# ==================== 日志配置 ====================

# 日志文件路径
LOG_DIR="/var/log/wireguard-vpn"
LOG_FILE="${LOG_DIR}/vpn-client.log"

# 日志保留天数
LOG_RETENTION_DAYS=30

# ==================== 网络配置 ====================

# 内网接口名称
# 脚本会自动检测，如果检测失败请手动设置
# 示例: eth0, ens192, enp0s3
INTERNAL_INTERFACE=""

# ==================== 重试配置 ====================

# API 请求超时时间（秒）
API_TIMEOUT=30

# 最大重试次数
MAX_RETRIES=3

# 重试间隔（秒）
RETRY_INTERVAL=5

# ==================== 高级配置 ====================

# 是否启用调试模式
# 启用后会输出详细的调试信息
DEBUG=false

# 是否自动启动 WireGuard
# 设置为 true 时，初始化完成后自动启动服务
AUTO_START=true

# ==================== 辅助函数 ====================

# 获取本机 IP 地址
get_local_ip() {
    # 优先使用配置的接口
    if [ -n "$INTERNAL_INTERFACE" ]; then
        ip -4 addr show "$INTERNAL_INTERFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
        return
    fi
    
    # 自动检测默认路由的接口
    local default_interface
    default_interface=$(ip route | grep default | awk '{print $5}' | head -1)
    
    if [ -n "$default_interface" ]; then
        ip -4 addr show "$default_interface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
    else
        # 最后尝试使用 hostname 命令
        hostname -I | awk '{print $1}'
    fi
}

# 记录日志
log() {
    local level=$1
    local message=$2
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    if [ "$DEBUG" = true ] || [ "$level" = "ERROR" ]; then
        echo "[$timestamp] [$level] $message"
    fi
}

# 发送 API 请求
send_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local retry_count=0
    local response
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if [ "$method" = "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" \
                -X GET \
                -H "X-VM-Token: $VM_TOKEN" \
                -H "Content-Type: application/json" \
                --connect-timeout "$API_TIMEOUT" \
                "${VPN_SERVER_URL}${endpoint}")
        else
            response=$(curl -s -w "\n%{http_code}" \
                -X POST \
                -H "X-VM-Token: $VM_TOKEN" \
                -H "Content-Type: application/json" \
                --connect-timeout "$API_TIMEOUT" \
                -d "$data" \
                "${VPN_SERVER_URL}${endpoint}")
        fi
        
        local http_code
        http_code=$(echo "$response" | tail -1)
        local body
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "200" ]; then
            echo "$body"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log "WARN" "请求失败 (HTTP $http_code)，重试 $retry_count/$MAX_RETRIES"
        sleep "$RETRY_INTERVAL"
    done
    
    log "ERROR" "请求失败，已达最大重试次数"
    return 1
}

# ==================== 验证配置 ====================

validate_config() {
    local errors=0
    
    if [ "$VPN_SERVER_URL" = "http://YOUR_SERVER_IP:8000" ]; then
        log "ERROR" "请配置 VPN_SERVER_URL"
        errors=$((errors + 1))
    fi
    
    if [ "$VM_TOKEN" = "YOUR_VM_TOKEN_HERE" ]; then
        log "ERROR" "请配置 VM_TOKEN"
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        return 1
    fi
    
    return 0
}

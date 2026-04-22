#!/bin/bash
#
# WireGuard VPN 一次性初始化脚本
# 用于虚拟机首次启动时自动配置 VPN
# 执行成功后自动删除，防止 Token 泄露
#
# 作者: FCloudVPN Team
# 版本: 3.0.0
# 更新日期: 2026-04-21
#
# 配置文件: /etc/fcloud/config.conf
#

set -e

CONFIG_FILE="/etc/fcloud/config.conf"
WG_INTERFACE="wg0"
LOG_FILE="/var/log/wireguard-vpn/one-shot.log"
ERROR_MESSAGE=""

log() {
    local level=$1
    local message=$2
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "$1"; }
log_error() { log "ERROR" "$1"; }

load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        ERROR_MESSAGE="配置文件不存在: $CONFIG_FILE"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    source "$CONFIG_FILE"
    
    if [ -z "$VPN_SERVER_URL" ]; then
        ERROR_MESSAGE="配置文件缺少 VPN_SERVER_URL"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    if [ -z "$VM_TOKEN" ]; then
        ERROR_MESSAGE="配置文件缺少 VM_TOKEN"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    log_info "配置加载成功: $VPN_SERVER_URL"
    return 0
}

send_ready_request() {
    local success=$1
    local error_msg=$2
    
    local json_body
    if [ "$success" = "true" ]; then
        json_body='{"success": true}'
    else
        local escaped_msg
        escaped_msg=$(echo "$error_msg" | sed 's/"/\\"/g' | sed 's/\n/\\n/g')
        json_body="{\"success\": false, \"error_message\": \"$escaped_msg\"}"
    fi
    
    curl -s -X POST \
        -H "Authorization: Bearer $VM_TOKEN" \
        -H "Content-Type: application/json" \
        --connect-timeout 30 \
        --max-time 60 \
        -d "$json_body" \
        "${VPN_SERVER_URL}/api/vm/ready" > /dev/null 2>&1 || true
}

request_vpn_config() {
    log_info "请求 VPN 配置..."
    
    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X GET \
        -H "Authorization: Bearer $VM_TOKEN" \
        -H "Content-Type: application/json" \
        --connect-timeout 30 \
        --max-time 60 \
        "${VPN_SERVER_URL}/api/vm/config") || {
        ERROR_MESSAGE="请求 VPN 配置失败: 网络错误"
        log_error "$ERROR_MESSAGE"
        return 1
    }
    
    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" != "200" ]; then
        ERROR_MESSAGE="请求 VPN 配置失败: HTTP $http_code"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    local success
    success=$(echo "$body" | jq -r '.success' 2>/dev/null || echo "false")
    
    if [ "$success" != "true" ]; then
        local msg
        msg=$(echo "$body" | jq -r '.message // .detail // "未知错误"' 2>/dev/null || echo "解析响应失败")
        ERROR_MESSAGE="获取配置失败: $msg"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    echo "$body"
    return 0
}

generate_wg_config() {
    local config_data=$1
    local config_file="/etc/wireguard/${WG_INTERFACE}.conf"
    
    log_info "生成 WireGuard 配置..."
    
    local server_config
    server_config=$(echo "$config_data" | jq -r '.data.server.config_file')
    
    if [ -z "$server_config" ] || [ "$server_config" = "null" ]; then
        ERROR_MESSAGE="配置文件内容为空"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    mkdir -p /etc/wireguard
    echo "$server_config" > "$config_file"
    chmod 600 "$config_file"
    
    log_info "配置文件已生成: $config_file"
    return 0
}

start_wireguard() {
    log_info "启动 WireGuard..."
    
    if wg show "$WG_INTERFACE" &> /dev/null; then
        wg-quick down "$WG_INTERFACE" 2>/dev/null || true
    fi
    
    if ! wg-quick up "$WG_INTERFACE" 2>&1 | tee -a "$LOG_FILE"; then
        ERROR_MESSAGE="wg-quick up 失败"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    return 0
}

check_wireguard() {
    log_info "检查 WireGuard 状态..."
    
    if ! wg show "$WG_INTERFACE" &> /dev/null; then
        ERROR_MESSAGE="WireGuard 接口 $WG_INTERFACE 未启动"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    log_info "WireGuard 启动成功"
    return 0
}

cleanup() {
    log_info "清理敏感信息..."
    
    rm -f "$CONFIG_FILE"
    rm -f "$0"
    
    history -c 2>/dev/null || true
    unset VM_TOKEN 2>/dev/null || true
    
    log_info "清理完成"
}

main() {
    mkdir -p /var/log/wireguard-vpn
    
    log_info "=========================================="
    log_info "WireGuard VPN 初始化脚本 v3.0.0"
    log_info "=========================================="
    
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行"
        exit 1
    fi
    
    if ! load_config; then
        send_ready_request "false" "$ERROR_MESSAGE"
        exit 1
    fi
    
    CONFIG_RESPONSE=""
    if ! CONFIG_RESPONSE=$(request_vpn_config); then
        send_ready_request "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    if ! generate_wg_config "$CONFIG_RESPONSE"; then
        send_ready_request "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    if ! start_wireguard; then
        send_ready_request "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    if ! check_wireguard; then
        send_ready_request "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    send_ready_request "true" ""
    
    if command -v systemctl &> /dev/null; then
        systemctl enable "wg-quick@${WG_INTERFACE}" > /dev/null 2>&1
    fi
    
    log_info "=========================================="
    log_info "初始化完成"
    log_info "=========================================="
    
    cleanup
    exit 0
}

main

#!/bin/bash
#
# WireGuard VPN 一次性初始化脚本
# 执行成功后自动删除，防止 Token 泄露
#

set -e

VPN_SERVER_URL="http://YOUR_SERVER_IP:8000"
VM_TOKEN="YOUR_VM_TOKEN"
WG_INTERFACE="wg0"
ERROR_MESSAGE=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

send_ready() {
    local success=$1
    local error_msg=$2
    
    local json_body
    if [ "$success" = "true" ]; then
        json_body='{"success": true}'
    else
        local escaped_msg
        escaped_msg=$(echo "$error_msg" | sed 's/"/\\"/g')
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

get_vpn_config() {
    log "请求 VPN 配置..."
    
    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X GET \
        -H "Authorization: Bearer $VM_TOKEN" \
        -H "Content-Type: application/json" \
        --connect-timeout 30 \
        --max-time 60 \
        "${VPN_SERVER_URL}/api/vm/config") || {
        ERROR_MESSAGE="网络请求失败"
        return 1
    }
    
    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" != "200" ]; then
        ERROR_MESSAGE="HTTP $http_code: $(echo "$body" | jq -r '.detail // .message // "未知错误"' 2>/dev/null || echo "$body")"
        return 1
    fi
    
    local success
    success=$(echo "$body" | jq -r '.success' 2>/dev/null || echo "false")
    
    if [ "$success" != "true" ]; then
        ERROR_MESSAGE=$(echo "$body" | jq -r '.message // .detail // "未知错误"' 2>/dev/null || echo "解析失败")
        return 1
    fi
    
    echo "$body"
}

write_wg_config() {
    local config_data=$1
    local config_file="/etc/wireguard/${WG_INTERFACE}.conf"
    
    local server_config
    server_config=$(echo "$config_data" | jq -r '.data.server.config_file')
    
    if [ -z "$server_config" ] || [ "$server_config" = "null" ]; then
        ERROR_MESSAGE="配置内容为空"
        return 1
    fi
    
    mkdir -p /etc/wireguard
    echo "$server_config" > "$config_file"
    chmod 600 "$config_file"
    
    log "配置文件已生成: $config_file"
}

start_wg() {
    log "启动 WireGuard..."
    
    wg show "$WG_INTERFACE" &> /dev/null && wg-quick down "$WG_INTERFACE" 2>/dev/null || true
    
    if ! wg-quick up "$WG_INTERFACE"; then
        ERROR_MESSAGE="wg-quick up 失败"
        return 1
    fi
    
    if ! wg show "$WG_INTERFACE" &> /dev/null; then
        ERROR_MESSAGE="WireGuard 未启动"
        return 1
    fi
    
    log "WireGuard 启动成功"
}

cleanup() {
    rm -f "$0"
    unset VM_TOKEN 2>/dev/null || true
}

main() {
    if [ "$EUID" -ne 0 ]; then
        echo "需要 root 权限" >&2
        exit 1
    fi
    
    log "开始初始化..."
    
    CONFIG_RESPONSE=""
    if ! CONFIG_RESPONSE=$(get_vpn_config); then
        send_ready "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    if ! write_wg_config "$CONFIG_RESPONSE"; then
        send_ready "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    if ! start_wg; then
        send_ready "false" "$ERROR_MESSAGE"
        cleanup
        exit 1
    fi
    
    send_ready "true" ""
    
    systemctl enable "wg-quick@${WG_INTERFACE}" > /dev/null 2>&1 || true
    
    log "初始化完成"
    cleanup
}

main

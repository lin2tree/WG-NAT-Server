#!/bin/bash
#
# WireGuard VPN 一次性初始化脚本
# 用于虚拟机首次启动时自动配置 VPN
# 执行成功后自动删除，防止 Token 泄露
#
# 作者: FCloudVPN Team
# 版本: 2.0.0
# 更新日期: 2026-04-21
#
# 使用方式:
#   方式一：环境变量
#     export VPN_SERVER_URL="http://192.168.1.10:8000"
#     export VM_TOKEN="your_token"
#     sudo -E bash one-shot.sh
#
#   方式二：命令行参数
#     sudo bash one-shot.sh --server http://192.168.1.10:8000 --token your_token
#
#   方式三：cloud-init
#     #cloud-config
#     runcmd:
#       - VPN_SERVER_URL=http://192.168.1.10:8000 VM_TOKEN=your_token /path/to/one-shot.sh
#

set -e

VPN_SERVER_URL="${VPN_SERVER_URL:-}"
VM_TOKEN="${VM_TOKEN:-}"
WG_INTERFACE="${WG_INTERFACE:-wg0}"
API_TIMEOUT="${API_TIMEOUT:-30}"
AUTO_DELETE="${AUTO_DELETE:-true}"

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

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--server)
                VPN_SERVER_URL="$2"
                shift 2
                ;;
            -t|--token)
                VM_TOKEN="$2"
                shift 2
                ;;
            -i|--interface)
                WG_INTERFACE="$2"
                shift 2
                ;;
            --no-delete)
                AUTO_DELETE="false"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

validate_config() {
    if [ -z "$VPN_SERVER_URL" ]; then
        ERROR_MESSAGE="缺少 VPN_SERVER_URL 配置"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    if [ -z "$VM_TOKEN" ]; then
        ERROR_MESSAGE="缺少 VM_TOKEN 配置"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    log_info "配置验证通过"
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
    
    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Authorization: Bearer $VM_TOKEN" \
        -H "Content-Type: application/json" \
        --connect-timeout "$API_TIMEOUT" \
        --max-time "$((API_TIMEOUT * 2))" \
        -d "$json_body" \
        "${VPN_SERVER_URL}/api/vm/ready") || true
    
    local http_code
    http_code=$(echo "$response" | tail -1)
    
    if [ "$http_code" = "200" ]; then
        log_info "状态上报成功"
    else
        log_warn "状态上报失败: HTTP $http_code"
    fi
}

request_vpn_config() {
    log_info "正在请求 VPN 配置..."
    
    local response
    local curl_exit_code=0
    
    response=$(curl -s -w "\n%{http_code}" \
        -X GET \
        -H "Authorization: Bearer $VM_TOKEN" \
        -H "Content-Type: application/json" \
        --connect-timeout "$API_TIMEOUT" \
        --max-time "$((API_TIMEOUT * 2))" \
        "${VPN_SERVER_URL}/api/vm/config") || curl_exit_code=$?
    
    if [ $curl_exit_code -ne 0 ]; then
        ERROR_MESSAGE="请求 VPN 配置失败: curl 退出码 $curl_exit_code"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" != "200" ]; then
        ERROR_MESSAGE="请求 VPN 配置失败: HTTP $http_code, 响应: $body"
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
    
    log_info "正在生成 WireGuard 配置..."
    
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
    log_info "正在启动 WireGuard..."
    
    if wg show "$WG_INTERFACE" &> /dev/null; then
        log_info "WireGuard 已在运行，先停止..."
        wg-quick down "$WG_INTERFACE" || true
    fi
    
    if ! wg-quick up "$WG_INTERFACE" 2>&1 | tee -a "$LOG_FILE"; then
        ERROR_MESSAGE="wg-quick up 失败"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    return 0
}

check_wireguard() {
    log_info "正在检查 WireGuard 状态..."
    
    if ! wg show "$WG_INTERFACE" &> /dev/null; then
        ERROR_MESSAGE="WireGuard 接口 $WG_INTERFACE 未启动"
        log_error "$ERROR_MESSAGE"
        return 1
    fi
    
    local interface_info
    interface_info=$(wg show "$WG_INTERFACE" 2>&1)
    log_info "WireGuard 状态:\n$interface_info"
    
    local listen_port
    listen_port=$(wg show "$WG_INTERFACE" listen-port 2>/dev/null || echo "未知")
    log_info "监听端口: $listen_port"
    
    local public_key
    public_key=$(wg show "$WG_INTERFACE" public-key 2>/dev/null || echo "未知")
    log_info "公钥: $public_key"
    
    log_info "WireGuard 启动成功"
    return 0
}

cleanup() {
    if [ "$AUTO_DELETE" = "true" ]; then
        log_info "正在清理脚本文件..."
        
        local script_path
        script_path=$(readlink -f "$0" 2>/dev/null || echo "$0")
        
        if [ -f "$script_path" ]; then
            rm -f "$script_path"
            log_info "脚本文件已删除: $script_path"
        fi
        
        history -c 2>/dev/null || true
        unset VM_TOKEN 2>/dev/null || true
    fi
}

main() {
    mkdir -p /var/log/wireguard-vpn
    
    log_info "=========================================="
    log_info "WireGuard VPN 一次性初始化脚本 v2.0.0"
    log_info "=========================================="
    
    if [ "$EUID" -ne 0 ]; then
        ERROR_MESSAGE="请使用 root 用户运行此脚本"
        log_error "$ERROR_MESSAGE"
        echo "$ERROR_MESSAGE" >&2
        exit 1
    fi
    
    parse_args "$@"
    
    if ! validate_config; then
        send_ready_request "false" "$ERROR_MESSAGE"
        cleanup
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
        log_info "已设置开机自启"
    fi
    
    log_info "=========================================="
    log_info "初始化完成！"
    log_info "=========================================="
    log_info "VPN 接口: $WG_INTERFACE"
    log_info "配置文件: /etc/wireguard/${WG_INTERFACE}.conf"
    log_info "日志文件: $LOG_FILE"
    
    cleanup
    exit 0
}

main "$@"

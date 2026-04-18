#!/bin/bash
#
# WireGuard VPN 一次性初始化脚本
# 用于虚拟机首次启动时自动配置 VPN
# 执行成功后自动删除，防止 Token 泄露
#
# 作者: FCloudVPN Team
# 版本: 1.0.0
# 更新日期: 2026-04-17
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

# ==================== 配置参数 ====================
# 优先级：命令行参数 > 环境变量 > 默认值

VPN_SERVER_URL="${VPN_SERVER_URL:-}"
VM_TOKEN="${VM_TOKEN:-}"
WG_INTERFACE="${WG_INTERFACE:-wg0}"
WG_PORT="${WG_PORT:-2588}"
API_TIMEOUT="${API_TIMEOUT:-30}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"
AUTO_DELETE="${AUTO_DELETE:-true}"

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ==================== 日志函数 ====================
LOG_FILE="/var/log/wireguard-vpn/one-shot.log"

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

# ==================== 解析命令行参数 ====================
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

# ==================== 验证配置 ====================
validate_config() {
    if [ -z "$VPN_SERVER_URL" ]; then
        log_error "缺少 VPN_SERVER_URL 配置"
        log_error "请通过环境变量或 --server 参数指定"
        exit 1
    fi
    
    if [ -z "$VM_TOKEN" ]; then
        log_error "缺少 VM_TOKEN 配置"
        log_error "请通过环境变量或 --token 参数指定"
        exit 1
    fi
    
    log_info "配置验证通过"
}

# ==================== 检测操作系统 ====================
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    log_info "检测到操作系统: $OS"
}

# ==================== 安装依赖 ====================
install_dependencies() {
    log_info "正在安装依赖..."
    
    case $OS in
        ubuntu|debian)
            export DEBIAN_FRONTEND=noninteractive
            log_info "更新软件包列表..."
            apt-get update -qq || {
                log_error "apt-get update 失败"
                exit 1
            }
            log_info "安装 WireGuard 及依赖..."
            apt-get install -y -qq wireguard wireguard-tools curl jq || {
                log_error "依赖安装失败"
                exit 1
            }
            ;;
        centos|rhel|rocky|almalinux)
            log_info "安装 EPEL 仓库..."
            yum install -y -q epel-release || {
                log_error "EPEL 仓库安装失败"
                exit 1
            }
            log_info "安装 WireGuard 及依赖..."
            yum install -y -q wireguard-tools curl jq || {
                log_error "依赖安装失败"
                exit 1
            }
            ;;
        alpine)
            log_info "安装 WireGuard 及依赖..."
            apk add --no-cache wireguard-tools curl jq || {
                log_error "依赖安装失败"
                exit 1
            }
            ;;
        *)
            log_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    # 验证安装
    log_info "验证安装..."
    if ! command -v wg &> /dev/null; then
        log_error "WireGuard 安装验证失败"
        exit 1
    fi
    if ! command -v curl &> /dev/null; then
        log_error "curl 安装验证失败"
        exit 1
    fi
    if ! command -v jq &> /dev/null; then
        log_error "jq 安装验证失败"
        exit 1
    fi
    
    # 启用 IP 转发
    log_info "启用 IP 转发..."
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p > /dev/null 2>&1 || {
        log_warn "sysctl 配置可能未生效，但继续执行"
    }
    
    log_info "依赖安装完成"
}

# ==================== 获取本机 IP ====================
get_local_ip() {
    local interface
    interface=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'dev \K\S+')
    
    if [ -n "$interface" ]; then
        ip -4 addr show "$interface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
    else
        hostname -I | awk '{print $1}'
    fi
}

# ==================== 发送 API 请求 ====================
send_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        local response
        local curl_exit_code=0
        
        if [ "$method" = "GET" ]; then
            response=$(timeout $((API_TIMEOUT + 5)) curl -s -w "\n%{http_code}" \
                -X GET \
                -H "X-VM-Token: $VM_TOKEN" \
                -H "Content-Type: application/json" \
                --connect-timeout "$API_TIMEOUT" \
                --max-time "$((API_TIMEOUT * 2))" \
                "${VPN_SERVER_URL}${endpoint}") || curl_exit_code=$?
        else
            response=$(timeout $((API_TIMEOUT + 5)) curl -s -w "\n%{http_code}" \
                -X POST \
                -H "X-VM-Token: $VM_TOKEN" \
                -H "Content-Type: application/json" \
                --connect-timeout "$API_TIMEOUT" \
                --max-time "$((API_TIMEOUT * 2))" \
                -d "$data" \
                "${VPN_SERVER_URL}${endpoint}") || curl_exit_code=$?
        fi
        
        if [ $curl_exit_code -eq 124 ]; then
            log_warn "请求超时，重试 $((retry_count + 1))/$MAX_RETRIES"
            retry_count=$((retry_count + 1))
            sleep "$RETRY_INTERVAL"
            continue
        elif [ $curl_exit_code -ne 0 ]; then
            log_warn "请求失败 (exit: $curl_exit_code)，重试 $((retry_count + 1))/$MAX_RETRIES"
            retry_count=$((retry_count + 1))
            sleep "$RETRY_INTERVAL"
            continue
        fi
        
        local http_code
        http_code=$(echo "$response" | tail -1)
        local body
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "200" ]; then
            echo "$body"
            return 0
        fi
        
        log_warn "HTTP $http_code，重试 $((retry_count + 1))/$MAX_RETRIES"
        retry_count=$((retry_count + 1))
        sleep "$RETRY_INTERVAL"
    done
    
    log_error "请求失败，已达最大重试次数"
    return 1
}

# ==================== 请求 VPN 配置 ====================
request_vpn_config() {
    log_info "正在请求 VPN 配置..."
    
    local response
    response=$(send_request "GET" "/api/vm/config" "")
    
    if [ $? -ne 0 ]; then
        log_error "获取 VPN 配置失败"
        exit 1
    fi
    
    local success
    success=$(echo "$response" | jq -r '.success')
    
    if [ "$success" != "true" ]; then
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message // "未知错误"')
        log_error "获取配置失败: $error_msg"
        exit 1
    fi
    
    echo "$response" | jq -r '.data'
}

# ==================== 生成 WireGuard 配置 ====================
generate_wg_config() {
    local config_data=$1
    local config_file="/etc/wireguard/${WG_INTERFACE}.conf"
    
    log_info "正在生成 WireGuard 配置..."
    
    local server_private_key
    server_private_key=$(echo "$config_data" | jq -r '.server_private_key')
    
    local vpn_subnet
    vpn_subnet=$(echo "$config_data" | jq -r '.vpn_subnet')
    
    local default_interface
    default_interface=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'dev \K\S+')
    [ -z "$default_interface" ] && default_interface="eth0"
    
    mkdir -p /etc/wireguard
    
    cat > "$config_file" << EOF
[Interface]
PrivateKey = ${server_private_key}
ListenPort = ${WG_PORT}
Address = ${vpn_subnet}/24
SaveConfig = false
PostUp = iptables -A FORWARD -i ${WG_INTERFACE} -j ACCEPT; iptables -A FORWARD -o ${WG_INTERFACE} -j ACCEPT; iptables -t nat -A POSTROUTING -o ${default_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i ${WG_INTERFACE} -j ACCEPT; iptables -D FORWARD -o ${WG_INTERFACE} -j ACCEPT; iptables -t nat -D POSTROUTING -o ${default_interface} -j MASQUERADE
EOF
    
    chmod 600 "$config_file"
    log_info "配置文件已生成: $config_file"
}

# ==================== 启动 WireGuard ====================
start_wireguard() {
    log_info "正在启动 WireGuard..."
    
    if wg show "$WG_INTERFACE" &> /dev/null; then
        wg-quick down "$WG_INTERFACE" || true
    fi
    
    wg-quick up "$WG_INTERFACE"
    
    if wg show "$WG_INTERFACE" &> /dev/null; then
        log_info "WireGuard 启动成功"
    else
        log_error "WireGuard 启动失败"
        exit 1
    fi
}

# ==================== 上报就绪状态 ====================
report_ready() {
    log_info "正在上报就绪状态..."
    
    local response
    response=$(send_request "POST" "/api/vm/ready" "{}")
    
    if [ $? -ne 0 ]; then
        log_warn "就绪状态上报失败，但不影响 VPN 使用"
        return 0
    fi
    
    local success
    success=$(echo "$response" | jq -r '.success')
    
    if [ "$success" = "true" ]; then
        log_info "就绪状态上报成功"
    else
        log_warn "就绪状态上报失败，但不影响 VPN 使用"
    fi
}

# ==================== 设置开机自启 ====================
enable_autostart() {
    log_info "正在设置开机自启..."
    
    if command -v systemctl &> /dev/null; then
        systemctl enable "wg-quick@${WG_INTERFACE}" > /dev/null 2>&1
        log_info "已设置开机自启"
    else
        log_warn "非 systemd 系统，请手动配置开机自启"
    fi
}

# ==================== 清理敏感信息 ====================
cleanup() {
    if [ "$AUTO_DELETE" = "true" ]; then
        log_info "正在清理脚本文件..."
        
        # 获取脚本绝对路径
        local script_path
        script_path=$(readlink -f "$0" 2>/dev/null || echo "$0")
        
        # 删除脚本文件
        if [ -f "$script_path" ]; then
            rm -f "$script_path"
            log_info "脚本文件已删除: $script_path"
        fi
        
        # 清除历史记录中的敏感信息
        history -c 2>/dev/null || true
        
        # 清除环境变量（如果可能）
        unset VM_TOKEN 2>/dev/null || true
    fi
}

# ==================== 主函数 ====================
main() {
    # 创建日志目录
    mkdir -p /var/log/wireguard-vpn
    
    log_info "=========================================="
    log_info "WireGuard VPN 一次性初始化脚本"
    log_info "=========================================="
    
    # 检查 root 权限
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 解析参数
    parse_args "$@"
    
    # 验证配置
    validate_config
    
    # 检测操作系统
    detect_os
    
    # 安装依赖
    install_dependencies
    
    # 获取本机 IP
    VM_IP=$(get_local_ip)
    log_info "本机 IP: $VM_IP"
    
    # 请求 VPN 配置
    CONFIG_DATA=$(request_vpn_config)
    
    # 生成 WireGuard 配置
    generate_wg_config "$CONFIG_DATA"
    
    # 启动 WireGuard
    start_wireguard
    
    # 上报就绪状态
    report_ready
    
    # 设置开机自启
    enable_autostart
    
    log_info "=========================================="
    log_info "初始化完成！"
    log_info "=========================================="
    log_info "VPN 接口: $WG_INTERFACE"
    log_info "配置文件: /etc/wireguard/${WG_INTERFACE}.conf"
    log_info "日志文件: $LOG_FILE"
    log_info ""
    
    # 清理
    cleanup
    
    exit 0
}

# 执行主函数
main "$@"

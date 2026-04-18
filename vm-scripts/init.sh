#!/bin/bash
#
# WireGuard VPN 初始化脚本
# 用于虚拟机首次启动时获取 VPN 配置并启动服务
#
# 作者: FCloudVPN Team
# 版本: 1.0.0
# 更新日期: 2026-04-17
#

set -e  # 遇到错误立即退出

# ==================== 加载配置 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ==================== 日志函数 ====================
log_info() {
    local message=$1
    echo -e "${GREEN}[INFO]${NC} $message"
    log "INFO" "$message"
}

log_warn() {
    local message=$1
    echo -e "${YELLOW}[WARN]${NC} $message"
    log "WARN" "$message"
}

log_error() {
    local message=$1
    echo -e "${RED}[ERROR]${NC} $message"
    log "ERROR" "$message"
}

log_debug() {
    if [ "$DEBUG" = true ]; then
        local message=$1
        echo -e "${BLUE}[DEBUG]${NC} $message"
        log "DEBUG" "$message"
    fi
}

# ==================== 检查依赖 ====================
check_dependencies() {
    log_info "检查依赖..."
    
    local missing=()
    
    # 检查 WireGuard
    if ! command -v wg &> /dev/null; then
        missing+=("wireguard-tools")
    fi
    
    # 检查 curl
    if ! command -v curl &> /dev/null; then
        missing+=("curl")
    fi
    
    # 检查 jq
    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "缺少依赖: ${missing[*]}"
        log_error "请先运行 install.sh 安装依赖"
        exit 1
    fi
    
    log_info "依赖检查通过"
}

# ==================== 获取本机 IP ====================
get_vm_ip() {
    local ip
    ip=$(get_local_ip)
    
    if [ -z "$ip" ]; then
        log_error "无法获取本机 IP 地址"
        exit 1
    fi
    
    log_info "本机 IP 地址: $ip"
    echo "$ip"
}

# ==================== 请求 VPN 配置 ====================
request_vpn_config() {
    local vm_ip=$1
    
    log_info "正在向 VPN 管理服务请求配置..."
    log_debug "请求地址: ${VPN_SERVER_URL}/api/vm/config"
    log_debug "虚拟机 IP: $vm_ip"
    
    # 发送配置请求
    local response
    response=$(send_request "GET" "/api/vm/config" "")
    
    if [ $? -ne 0 ]; then
        log_error "请求 VPN 配置失败"
        exit 1
    fi
    
    log_debug "响应内容: $response"
    
    # 解析响应
    local success
    success=$(echo "$response" | jq -r '.success')
    
    if [ "$success" != "true" ]; then
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message // "未知错误"')
        log_error "获取配置失败: $error_msg"
        exit 1
    fi
    
    # 提取配置数据
    local config_data
    config_data=$(echo "$response" | jq -r '.data')
    
    echo "$config_data"
}

# ==================== 生成 WireGuard 配置文件 ====================
generate_wg_config() {
    local config_data=$1
    local config_file="/etc/wireguard/${WG_INTERFACE}.conf"
    
    log_info "正在生成 WireGuard 配置文件..."
    
    # 提取配置参数
    local server_private_key
    server_private_key=$(echo "$config_data" | jq -r '.server_private_key')
    
    local vpn_subnet
    vpn_subnet=$(echo "$config_data" | jq -r '.vpn_subnet')
    
    local public_port
    public_port=$(echo "$config_data" | jq -r '.public_port')
    
    local server_public_key
    server_public_key=$(echo "$config_data" | jq -r '.server_public_key')
    
    log_debug "VPN 子网: $vpn_subnet"
    log_debug "公网端口: $public_port"
    
    # 生成配置文件
    cat > "$config_file" << EOF
# WireGuard Server Configuration
# 自动生成于: $(date '+%Y-%m-%d %H:%M:%S')
# 虚拟机 IP: $(get_local_ip)

[Interface]
# 服务端私钥
PrivateKey = ${server_private_key}

# 监听端口
ListenPort = ${WG_PORT}

# VPN 子网地址
Address = ${vpn_subnet}/24

# 保存配置更改
SaveConfig = false

# PostUp 脚本 - 启动时执行
PostUp = iptables -A FORWARD -i ${WG_INTERFACE} -j ACCEPT
PostUp = iptables -A FORWARD -o ${WG_INTERFACE} -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o ${INTERNAL_INTERFACE:-eth0} -j MASQUERADE

# PostDown 脚本 - 停止时执行
PostDown = iptables -D FORWARD -i ${WG_INTERFACE} -j ACCEPT
PostDown = iptables -D FORWARD -o ${WG_INTERFACE} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o ${INTERNAL_INTERFACE:-eth0} -j MASQUERADE

# ========================================
# 客户端配置 (由 VPN 管理服务生成)
# ========================================
# 以下客户端配置由服务端管理
# 请勿手动修改
EOF
    
    # 设置权限
    chmod 600 "$config_file"
    
    log_info "配置文件已生成: $config_file"
}

# ==================== 启动 WireGuard ====================
start_wireguard() {
    log_info "正在启动 WireGuard..."
    
    # 检查是否已运行
    if wg show "$WG_INTERFACE" &> /dev/null; then
        log_warn "WireGuard 已在运行，正在重启..."
        wg-quick down "$WG_INTERFACE" || true
    fi
    
    # 启动 WireGuard
    wg-quick up "$WG_INTERFACE"
    
    # 验证启动状态
    if wg show "$WG_INTERFACE" &> /dev/null; then
        log_info "WireGuard 启动成功"
        
        # 显示接口信息
        if [ "$DEBUG" = true ]; then
            wg show "$WG_INTERFACE"
        fi
    else
        log_error "WireGuard 启动失败"
        exit 1
    fi
}

# ==================== 上报就绪状态 ====================
report_ready() {
    local vm_ip=$1
    
    log_info "正在上报就绪状态..."
    
    # 发送就绪请求
    local response
    response=$(send_request "POST" "/api/vm/ready" "{}")
    
    if [ $? -ne 0 ]; then
        log_error "上报就绪状态失败"
        # 不退出，允许重试
        return 1
    fi
    
    # 解析响应
    local success
    success=$(echo "$response" | jq -r '.success')
    
    if [ "$success" = "true" ]; then
        log_info "就绪状态上报成功"
        return 0
    else
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message // "未知错误"')
        log_error "就绪状态上报失败: $error_msg"
        return 1
    fi
}

# ==================== 设置开机自启 ====================
enable_autostart() {
    log_info "正在设置开机自启..."
    
    # systemd 系统
    if command -v systemctl &> /dev/null; then
        systemctl enable "wg-quick@${WG_INTERFACE}"
        log_info "已设置开机自启: wg-quick@${WG_INTERFACE}"
    else
        log_warn "非 systemd 系统，请手动配置开机自启"
        log_warn "可以将 'wg-quick up $WG_INTERFACE' 添加到 /etc/rc.local"
    fi
}

# ==================== 清理日志 ====================
cleanup_logs() {
    log_info "正在清理旧日志..."
    
    find "$LOG_DIR" -name "*.log" -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
    
    log_info "日志清理完成"
}

# ==================== 主函数 ====================
main() {
    log_info "=========================================="
    log_info "WireGuard VPN 初始化脚本"
    log_info "=========================================="
    log_info ""
    
    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    # 清理旧日志
    cleanup_logs
    
    # 验证配置
    if ! validate_config; then
        log_error "配置验证失败，请检查 config.sh"
        exit 1
    fi
    
    # 检查依赖
    check_dependencies
    
    # 获取本机 IP
    VM_IP=$(get_vm_ip)
    
    # 请求 VPN 配置
    CONFIG_DATA=$(request_vpn_config "$VM_IP")
    
    # 生成 WireGuard 配置
    generate_wg_config "$CONFIG_DATA"
    
    # 启动 WireGuard
    if [ "$AUTO_START" = true ]; then
        start_wireguard
        
        # 上报就绪状态
        report_ready "$VM_IP"
        
        # 设置开机自启
        enable_autostart
    fi
    
    log_info ""
    log_info "=========================================="
    log_info "初始化完成！"
    log_info "=========================================="
    log_info ""
    log_info "VPN 接口: $WG_INTERFACE"
    log_info "配置文件: /etc/wireguard/${WG_INTERFACE}.conf"
    log_info "日志文件: $LOG_FILE"
    log_info ""
    log_info "常用命令:"
    log_info "  查看状态: wg show $WG_INTERFACE"
    log_info "  停止服务: wg-quick down $WG_INTERFACE"
    log_info "  启动服务: wg-quick up $WG_INTERFACE"
    log_info "  查看日志: tail -f $LOG_FILE"
    log_info ""
}

# 执行主函数
main "$@"

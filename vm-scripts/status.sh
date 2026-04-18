#!/bin/bash
#
# WireGuard VPN 状态检查脚本
# 用于检查 VPN 连接状态和配置信息
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
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==================== 检查 WireGuard 安装 ====================
check_installation() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}WireGuard 安装检查${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # 检查 WireGuard 命令
    if command -v wg &> /dev/null; then
        local wg_version
        wg_version=$(wg --version 2>&1 | head -1)
        echo -e "WireGuard: ${GREEN}已安装${NC} ($wg_version)"
    else
        echo -e "WireGuard: ${RED}未安装${NC}"
        return 1
    fi
    
    # 检查 wg-quick 命令
    if command -v wg-quick &> /dev/null; then
        echo -e "wg-quick:  ${GREEN}已安装${NC}"
    else
        echo -e "wg-quick:  ${RED}未安装${NC}"
    fi
    
    # 检查 curl
    if command -v curl &> /dev/null; then
        echo -e "curl:      ${GREEN}已安装${NC}"
    else
        echo -e "curl:      ${RED}未安装${NC}"
    fi
    
    # 检查 jq
    if command -v jq &> /dev/null; then
        echo -e "jq:        ${GREEN}已安装${NC}"
    else
        echo -e "jq:        ${RED}未安装${NC}"
    fi
    
    echo ""
    return 0
}

# ==================== 检查 WireGuard 运行状态 ====================
check_running_status() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}WireGuard 运行状态${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    if ! wg show "$WG_INTERFACE" &> /dev/null; then
        echo -e "状态: ${RED}未运行${NC}"
        echo ""
        log_info "启动命令: wg-quick up $WG_INTERFACE"
        return 1
    fi
    
    echo -e "状态: ${GREEN}运行中${NC}"
    echo ""
    
    # 显示接口信息
    wg show "$WG_INTERFACE"
    echo ""
    
    return 0
}

# ==================== 检查配置文件 ====================
check_config_file() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}配置文件检查${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    local config_file="/etc/wireguard/${WG_INTERFACE}.conf"
    
    if [ -f "$config_file" ]; then
        echo -e "配置文件: ${GREEN}存在${NC}"
        echo -e "路径: $config_file"
        echo -e "权限: $(stat -c '%a' "$config_file" 2>/dev/null || stat -f '%Lp' "$config_file")"
        echo -e "大小: $(du -h "$config_file" | cut -f1)"
        echo ""
        
        # 检查配置文件内容
        if grep -q "PrivateKey" "$config_file"; then
            echo -e "私钥: ${GREEN}已配置${NC}"
        else
            echo -e "私钥: ${RED}未配置${NC}"
        fi
        
        if grep -q "ListenPort" "$config_file"; then
            local port
            port=$(grep "ListenPort" "$config_file" | awk '{print $3}')
            echo -e "监听端口: ${GREEN}$port${NC}"
        else
            echo -e "监听端口: ${RED}未配置${NC}"
        fi
        
        if grep -q "Address" "$config_file"; then
            local address
            address=$(grep "Address" "$config_file" | awk '{print $3}')
            echo -e "VPN 地址: ${GREEN}$address${NC}"
        else
            echo -e "VPN 地址: ${RED}未配置${NC}"
        fi
    else
        echo -e "配置文件: ${RED}不存在${NC}"
        echo -e "路径: $config_file"
        echo ""
        log_info "请先运行 init.sh 生成配置"
        return 1
    fi
    
    echo ""
    return 0
}

# ==================== 检查网络连接 ====================
check_network() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}网络连接检查${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # 获取本机 IP
    local vm_ip
    vm_ip=$(get_local_ip)
    echo -e "本机 IP: ${GREEN}$vm_ip${NC}"
    
    # 获取默认网络接口
    local default_interface
    default_interface=$(ip route | grep default | awk '{print $5}' | head -1)
    echo -e "网络接口: ${GREEN}${default_interface:-未知}${NC}"
    
    # 检查 IP 转发
    local ip_forward
    ip_forward=$(cat /proc/sys/net/ipv4/ip_forward)
    if [ "$ip_forward" = "1" ]; then
        echo -e "IP 转发: ${GREEN}已启用${NC}"
    else
        echo -e "IP 转发: ${YELLOW}未启用${NC}"
    fi
    
    echo ""
    
    # 检查 VPN 服务器连接
    if [ -n "$VPN_SERVER_URL" ]; then
        echo "正在检查 VPN 管理服务连接..."
        
        local server_reachable=false
        if curl -s --connect-timeout 5 "${VPN_SERVER_URL}/health" > /dev/null 2>&1; then
            echo -e "VPN 管理服务: ${GREEN}可达${NC}"
            server_reachable=true
        else
            echo -e "VPN 管理服务: ${RED}不可达${NC}"
        fi
    else
        echo -e "VPN 管理服务: ${YELLOW}未配置${NC}"
    fi
    
    echo ""
}

# ==================== 检查日志 ====================
check_logs() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}日志检查${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        echo -e "日志文件: ${GREEN}存在${NC}"
        echo -e "路径: $LOG_FILE"
        echo -e "大小: $(du -h "$LOG_FILE" | cut -f1)"
        echo ""
        
        # 显示最近的日志
        echo "最近 10 条日志:"
        echo "----------------------------------------"
        tail -10 "$LOG_FILE"
        echo "----------------------------------------"
    else
        echo -e "日志文件: ${YELLOW}不存在${NC}"
    fi
    
    echo ""
}

# ==================== 检查系统服务 ====================
check_systemd_service() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}系统服务检查${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    if command -v systemctl &> /dev/null; then
        local service_name="wg-quick@${WG_INTERFACE}"
        
        if systemctl is-enabled "$service_name" &> /dev/null; then
            echo -e "开机自启: ${GREEN}已启用${NC}"
        else
            echo -e "开机自启: ${YELLOW}未启用${NC}"
        fi
        
        if systemctl is-active "$service_name" &> /dev/null; then
            echo -e "服务状态: ${GREEN}运行中${NC}"
        else
            echo -e "服务状态: ${RED}未运行${NC}"
        fi
    else
        echo -e "系统类型: ${YELLOW}非 systemd 系统${NC}"
    fi
    
    echo ""
}

# ==================== 显示帮助信息 ====================
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -a, --all      显示所有检查项"
    echo "  -l, --logs     显示日志内容"
    echo "  -v, --verbose  显示详细输出"
    echo ""
    echo "示例:"
    echo "  $0              # 显示状态摘要"
    echo "  $0 --all        # 显示所有检查项"
    echo "  $0 --logs       # 显示日志内容"
    echo ""
}

# ==================== 主函数 ====================
main() {
    local show_all=false
    local show_logs=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -a|--all)
                show_all=true
                shift
                ;;
            -l|--logs)
                show_logs=true
                shift
                ;;
            -v|--verbose)
                DEBUG=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}WireGuard VPN 状态检查${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # 检查安装
    check_installation
    
    # 检查运行状态
    check_running_status
    
    # 检查配置文件
    check_config_file
    
    # 检查网络
    if [ "$show_all" = true ]; then
        check_network
    fi
    
    # 检查系统服务
    if [ "$show_all" = true ]; then
        check_systemd_service
    fi
    
    # 检查日志
    if [ "$show_logs" = true ] || [ "$show_all" = true ]; then
        check_logs
    fi
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}检查完成${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

# 执行主函数
main "$@"

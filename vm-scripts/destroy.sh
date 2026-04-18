#!/bin/bash
#
# WireGuard VPN 销毁脚本
# 用于停止 WireGuard 服务并清理配置文件
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
NC='\033[0m'  # No Color

# ==================== 日志函数 ====================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    log "INFO" "$1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    log "WARN" "$1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "ERROR" "$1"
}

# ==================== 停止 WireGuard ====================
stop_wireguard() {
    log_info "正在停止 WireGuard..."
    
    if ! wg show "$WG_INTERFACE" &> /dev/null; then
        log_warn "WireGuard 未在运行"
        return 0
    fi
    
    # 停止 WireGuard
    wg-quick down "$WG_INTERFACE"
    
    if wg show "$WG_INTERFACE" &> /dev/null; then
        log_error "WireGuard 停止失败"
        return 1
    fi
    
    log_info "WireGuard 已停止"
    return 0
}

# ==================== 禁用开机自启 ====================
disable_autostart() {
    log_info "正在禁用开机自启..."
    
    # systemd 系统
    if command -v systemctl &> /dev/null; then
        systemctl disable "wg-quick@${WG_INTERFACE}" 2>/dev/null || true
        log_info "已禁用开机自启"
    else
        log_warn "非 systemd 系统，请手动移除自启配置"
    fi
}

# ==================== 清理配置文件 ====================
cleanup_config() {
    local keep_logs=$1
    
    log_info "正在清理配置文件..."
    
    local config_file="/etc/wireguard/${WG_INTERFACE}.conf"
    
    if [ -f "$config_file" ]; then
        # 备份配置文件
        local backup_file="${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$config_file" "$backup_file"
        log_info "配置已备份到: $backup_file"
        
        # 删除配置文件
        rm -f "$config_file"
        log_info "配置文件已删除"
    else
        log_warn "配置文件不存在: $config_file"
    fi
    
    # 清理日志
    if [ "$keep_logs" = false ]; then
        log_info "正在清理日志文件..."
        
        if [ -d "$LOG_DIR" ]; then
            # 备份日志目录
            local log_backup="${LOG_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
            mv "$LOG_DIR" "$log_backup"
            log_info "日志已备份到: $log_backup"
        fi
    fi
}

# ==================== 清理 iptables 规则 ====================
cleanup_iptables() {
    log_info "正在清理 iptables 规则..."
    
    # 获取默认网络接口
    local default_interface
    default_interface=$(ip route | grep default | awk '{print $5}' | head -1)
    
    if [ -z "$default_interface" ]; then
        default_interface="eth0"
    fi
    
    # 删除 WireGuard 相关的 iptables 规则
    iptables -D FORWARD -i "$WG_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -D FORWARD -o "$WG_INTERFACE" -j ACCEPT 2>/dev/null || true
    iptables -t nat -D POSTROUTING -o "$default_interface" -j MASQUERADE 2>/dev/null || true
    
    log_info "iptables 规则已清理"
}

# ==================== 显示帮助信息 ====================
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help       显示帮助信息"
    echo "  -k, --keep-logs  保留日志文件"
    echo "  -f, --force      强制清理（不询问确认）"
    echo "  -v, --verbose    显示详细输出"
    echo ""
    echo "示例:"
    echo "  $0                # 交互式清理"
    echo "  $0 --keep-logs    # 保留日志文件"
    echo "  $0 --force        # 强制清理（不询问）"
    echo ""
}

# ==================== 主函数 ====================
main() {
    local keep_logs=false
    local force=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -k|--keep-logs)
                keep_logs=true
                shift
                ;;
            -f|--force)
                force=true
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
    
    log_info "=========================================="
    log_info "WireGuard VPN 销毁脚本"
    log_info "=========================================="
    log_info ""
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    # 确认操作
    if [ "$force" = false ]; then
        echo -e "${YELLOW}警告: 此操作将停止 VPN 服务并清理所有配置${NC}"
        echo ""
        read -p "确定要继续吗？(y/N): " confirm
        
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            exit 0
        fi
    fi
    
    # 停止 WireGuard
    stop_wireguard
    
    # 禁用开机自启
    disable_autostart
    
    # 清理 iptables 规则
    cleanup_iptables
    
    # 清理配置文件
    cleanup_config "$keep_logs"
    
    log_info ""
    log_info "=========================================="
    log_info "清理完成"
    log_info "=========================================="
    log_info ""
    log_info "VPN 服务已停止并清理"
    log_info "如需重新配置，请运行 init.sh"
    log_info ""
}

# 执行主函数
main "$@"

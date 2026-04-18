#!/bin/bash
#
# WireGuard VPN 就绪状态上报脚本
# 用于手动上报或重新上报 VPN 就绪状态
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

# ==================== 检查 WireGuard 状态 ====================
check_wireguard_status() {
    log_info "检查 WireGuard 运行状态..."
    
    if ! command -v wg &> /dev/null; then
        log_error "WireGuard 未安装"
        exit 1
    fi
    
    if ! wg show "$WG_INTERFACE" &> /dev/null; then
        log_error "WireGuard 接口 $WG_INTERFACE 未运行"
        log_info "请先运行 init.sh 启动 WireGuard"
        exit 1
    fi
    
    log_info "WireGuard 正在运行"
    
    # 显示接口信息
    echo ""
    wg show "$WG_INTERFACE"
    echo ""
}

# ==================== 上报就绪状态 ====================
report_ready() {
    local vm_ip=$1
    
    log_info "正在向 VPN 管理服务上报就绪状态..."
    log_info "虚拟机 IP: $vm_ip"
    
    # 发送就绪请求
    local response
    response=$(send_request "POST" "/api/vm/ready" "{}")
    
    if [ $? -ne 0 ]; then
        log_error "上报就绪状态失败"
        log_error "请检查网络连接和服务器配置"
        exit 1
    fi
    
    # 解析响应
    local success
    success=$(echo "$response" | jq -r '.success')
    
    if [ "$success" = "true" ]; then
        log_info "✓ 就绪状态上报成功"
        
        # 显示返回的配置信息
        local data
        data=$(echo "$response" | jq -r '.data // empty')
        
        if [ -n "$data" ]; then
            echo ""
            log_info "配置信息:"
            echo "$data" | jq -r '.'
            echo ""
        fi
        
        return 0
    else
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message // "未知错误"')
        log_error "就绪状态上报失败: $error_msg"
        
        # 特殊错误处理
        case "$error_msg" in
            *"记录已销毁"*)
                log_error "配置已被销毁，请重新运行 init.sh 获取新配置"
                ;;
            *"未找到"*)
                log_error "配置不存在，请先运行 init.sh 获取配置"
                ;;
        esac
        
        return 1
    fi
}

# ==================== 显示帮助信息 ====================
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -f, --force    强制上报（不检查 WireGuard 状态）"
    echo "  -v, --verbose  显示详细输出"
    echo ""
    echo "示例:"
    echo "  $0              # 正常上报就绪状态"
    echo "  $0 --force      # 强制上报（跳过状态检查）"
    echo ""
}

# ==================== 主函数 ====================
main() {
    local force=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
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
    log_info "WireGuard VPN 就绪状态上报"
    log_info "=========================================="
    log_info ""
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    # 验证配置
    if ! validate_config; then
        log_error "配置验证失败，请检查 config.sh"
        exit 1
    fi
    
    # 检查 WireGuard 状态
    if [ "$force" = false ]; then
        check_wireguard_status
    else
        log_warn "跳过 WireGuard 状态检查"
    fi
    
    # 获取本机 IP
    VM_IP=$(get_local_ip)
    
    if [ -z "$VM_IP" ]; then
        log_error "无法获取本机 IP 地址"
        exit 1
    fi
    
    # 上报就绪状态
    if report_ready "$VM_IP"; then
        log_info "=========================================="
        log_info "上报完成"
        log_info "=========================================="
        exit 0
    else
        log_info "=========================================="
        log_info "上报失败"
        log_info "=========================================="
        exit 1
    fi
}

# 执行主函数
main "$@"

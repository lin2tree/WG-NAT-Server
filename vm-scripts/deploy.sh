#!/bin/bash
#
# WireGuard VPN 快速部署脚本
# 用于一键安装和配置 WireGuard VPN 客户端
#
# 作者: FCloudVPN Team
# 版本: 1.0.0
# 更新日期: 2026-04-17
#

set -e  # 遇到错误立即退出

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ==================== 全局变量 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/etc/wireguard"
LOG_DIR="/var/log/wireguard-vpn"

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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# ==================== 显示欢迎信息 ====================
show_welcome() {
    clear
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  WireGuard VPN 客户端快速部署脚本${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "此脚本将自动完成以下操作："
    echo "  1. 安装 WireGuard 及依赖"
    echo "  2. 配置 VPN 连接参数"
    echo "  3. 获取并应用 VPN 配置"
    echo "  4. 启动 VPN 服务"
    echo "  5. 设置开机自启"
    echo ""
}

# ==================== 收集配置信息 ====================
collect_config() {
    log_step "步骤 1/5: 收集配置信息"
    echo ""
    
    # VPN 服务器地址
    read -p "请输入 VPN 管理服务地址 (例如: http://192.168.1.10:8000): " server_url
    
    if [ -z "$server_url" ]; then
        log_error "服务器地址不能为空"
        exit 1
    fi
    
    # VM Token
    read -p "请输入 VM 认证令牌: " vm_token
    
    if [ -z "$vm_token" ]; then
        log_error "VM Token 不能为空"
        exit 1
    fi
    
    # WireGuard 接口名称
    read -p "WireGuard 接口名称 [默认: wg0]: " wg_interface
    wg_interface=${wg_interface:-wg0}
    
    # 是否自动启动
    read -p "是否在配置完成后自动启动 VPN? [Y/n]: " auto_start
    auto_start=${auto_start:-Y}
    
    echo ""
    log_info "配置信息已收集"
}

# ==================== 安装依赖 ====================
install_dependencies() {
    log_step "步骤 2/5: 安装依赖"
    echo ""
    
    # 检查是否已安装
    if command -v wg &> /dev/null && command -v curl &> /dev/null && command -v jq &> /dev/null; then
        log_info "依赖已安装，跳过安装步骤"
        return 0
    fi
    
    # 运行安装脚本
    if [ -f "${SCRIPT_DIR}/install.sh" ]; then
        bash "${SCRIPT_DIR}/install.sh"
    else
        log_error "找不到安装脚本: install.sh"
        exit 1
    fi
    
    echo ""
}

# ==================== 配置 VPN 参数 ====================
configure_vpn() {
    log_step "步骤 3/5: 配置 VPN 参数"
    echo ""
    
    # 创建目录
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    
    # 生成配置文件
    cat > "${INSTALL_DIR}/config.sh" << EOF
#!/bin/bash
# WireGuard VPN 配置文件
# 自动生成于: $(date '+%Y-%m-%d %H:%M:%S')

VPN_SERVER_URL="${server_url}"
VM_TOKEN="${vm_token}"
WG_INTERFACE="${wg_interface}"
WG_PORT=2588
LOG_DIR="${LOG_DIR}"
LOG_FILE="${LOG_DIR}/vpn-client.log"
LOG_RETENTION_DAYS=30
INTERNAL_INTERFACE=""
API_TIMEOUT=30
MAX_RETRIES=3
RETRY_INTERVAL=5
DEBUG=false
AUTO_START=true

get_local_ip() {
    local default_interface
    default_interface=\$(ip route | grep default | awk '{print \$5}' | head -1)
    if [ -n "\$default_interface" ]; then
        ip -4 addr show "\$default_interface" | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
    else
        hostname -I | awk '{print \$1}'
    fi
}

log() {
    local level=\$1
    local message=\$2
    local timestamp
    timestamp=\$(date '+%Y-%m-%d %H:%M:%S')
    echo "[\$timestamp] [\$level] \$message" >> "\$LOG_FILE"
}

send_request() {
    local method=\$1
    local endpoint=\$2
    local data=\$3
    local retry_count=0
    local response
    
    while [ \$retry_count -lt \$MAX_RETRIES ]; do
        if [ "\$method" = "GET" ]; then
            response=\$(curl -s -w "\n%{http_code}" -X GET -H "X-VM-Token: \$VM_TOKEN" -H "Content-Type: application/json" --connect-timeout "\$API_TIMEOUT" "\${VPN_SERVER_URL}\${endpoint}")
        else
            response=\$(curl -s -w "\n%{http_code}" -X POST -H "X-VM-Token: \$VM_TOKEN" -H "Content-Type: application/json" --connect-timeout "\$API_TIMEOUT" -d "\$data" "\${VPN_SERVER_URL}\${endpoint}")
        fi
        
        local http_code
        http_code=\$(echo "\$response" | tail -1)
        local body
        body=\$(echo "\$response" | sed '\$d')
        
        if [ "\$http_code" = "200" ]; then
            echo "\$body"
            return 0
        fi
        
        retry_count=\$((retry_count + 1))
        log "WARN" "请求失败 (HTTP \$http_code)，重试 \$retry_count/\$MAX_RETRIES"
        sleep "\$RETRY_INTERVAL"
    done
    
    log "ERROR" "请求失败，已达最大重试次数"
    return 1
}

validate_config() {
    local errors=0
    if [ "\$VPN_SERVER_URL" = "http://YOUR_SERVER_IP:8000" ]; then
        log "ERROR" "请配置 VPN_SERVER_URL"
        errors=\$((errors + 1))
    fi
    if [ "\$VM_TOKEN" = "YOUR_VM_TOKEN_HERE" ]; then
        log "ERROR" "请配置 VM_TOKEN"
        errors=\$((errors + 1))
    fi
    if [ \$errors -gt 0 ]; then
        return 1
    fi
    return 0
}
EOF
    
    # 复制其他脚本
    cp "${SCRIPT_DIR}/init.sh" "${INSTALL_DIR}/"
    cp "${SCRIPT_DIR}/report-ready.sh" "${INSTALL_DIR}/"
    cp "${SCRIPT_DIR}/destroy.sh" "${INSTALL_DIR}/"
    cp "${SCRIPT_DIR}/status.sh" "${INSTALL_DIR}/"
    
    # 设置权限
    chmod +x "${INSTALL_DIR}"/*.sh
    chmod 700 "$INSTALL_DIR"
    
    log_info "配置文件已生成: ${INSTALL_DIR}/config.sh"
    echo ""
}

# ==================== 初始化 VPN ====================
initialize_vpn() {
    log_step "步骤 4/5: 初始化 VPN"
    echo ""
    
    if [[ "$auto_start" =~ ^[Yy]$ ]]; then
        # 运行初始化脚本
        bash "${INSTALL_DIR}/init.sh"
    else
        log_info "跳过自动启动，稍后可运行以下命令启动："
        log_info "  bash ${INSTALL_DIR}/init.sh"
    fi
    
    echo ""
}

# ==================== 显示完成信息 ====================
show_complete() {
    log_step "步骤 5/5: 完成"
    echo ""
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  部署完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "安装目录: $INSTALL_DIR"
    echo "日志目录: $LOG_DIR"
    echo ""
    echo "常用命令:"
    echo "  查看状态: bash ${INSTALL_DIR}/status.sh"
    echo "  查看日志: tail -f ${LOG_DIR}/vpn-client.log"
    echo "  停止 VPN: bash ${INSTALL_DIR}/destroy.sh"
    echo "  重启 VPN: wg-quick down ${wg_interface} && wg-quick up ${wg_interface}"
    echo ""
    echo "配置文件: ${INSTALL_DIR}/config.sh"
    echo ""
}

# ==================== 显示帮助信息 ====================
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -s, --server   VPN 服务器地址"
    echo "  -t, --token    VM 认证令牌"
    echo "  -i, --interface WireGuard 接口名称"
    echo "  --no-start     配置后不自动启动"
    echo ""
    echo "示例:"
    echo "  $0                                        # 交互式部署"
    echo "  $0 -s http://192.168.1.10:8000 -t token   # 快速部署"
    echo ""
}

# ==================== 主函数 ====================
main() {
    local server_url=""
    local vm_token=""
    local wg_interface="wg0"
    local auto_start="Y"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--server)
                server_url="$2"
                shift 2
                ;;
            -t|--token)
                vm_token="$2"
                shift 2
                ;;
            -i|--interface)
                wg_interface="$2"
                shift 2
                ;;
            --no-start)
                auto_start="N"
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 显示欢迎信息
    show_welcome
    
    # 如果参数不全，则进入交互模式
    if [ -z "$server_url" ] || [ -z "$vm_token" ]; then
        collect_config
    else
        log_info "使用命令行参数配置"
    fi
    
    # 安装依赖
    install_dependencies
    
    # 配置 VPN
    configure_vpn
    
    # 初始化 VPN
    initialize_vpn
    
    # 显示完成信息
    show_complete
}

# 执行主函数
main "$@"

#!/bin/bash
#
# WireGuard VPN 客户端安装脚本
# 用于在虚拟机上安装 WireGuard 及相关依赖
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

# ==================== 检测操作系统 ====================
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    log_info "检测到操作系统: $OS $OS_VERSION"
}

# ==================== 安装 WireGuard (Debian/Ubuntu) ====================
install_debian() {
    log_info "正在更新软件包列表..."
    apt-get update -y
    
    log_info "正在安装 WireGuard..."
    apt-get install -y wireguard wireguard-tools
    
    log_info "正在安装网络工具..."
    apt-get install -y net-tools curl jq
    
    log_info "正在启用 IP 转发..."
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
}

# ==================== 安装 WireGuard (CentOS/RHEL) ====================
install_centos() {
    log_info "正在安装 EPEL 仓库..."
    yum install -y epel-release
    
    log_info "正在更新软件包..."
    yum update -y
    
    log_info "正在安装 WireGuard..."
    yum install -y wireguard-tools
    
    log_info "正在安装网络工具..."
    yum install -y net-tools curl jq
    
    log_info "正在启用 IP 转发..."
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
}

# ==================== 安装 WireGuard (Alpine) ====================
install_alpine() {
    log_info "正在更新软件包..."
    apk update
    
    log_info "正在安装 WireGuard..."
    apk add wireguard-tools
    
    log_info "正在安装网络工具..."
    apk add net-tools curl jq
    
    log_info "正在启用 IP 转发..."
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
}

# ==================== 验证安装 ====================
verify_installation() {
    log_info "正在验证安装..."
    
    if command -v wg &> /dev/null; then
        WG_VERSION=$(wg --version 2>&1 | head -1)
        log_info "WireGuard 安装成功: $WG_VERSION"
    else
        log_error "WireGuard 安装失败"
        exit 1
    fi
    
    if command -v curl &> /dev/null; then
        log_info "curl 安装成功"
    else
        log_error "curl 安装失败"
        exit 1
    fi
    
    if command -v jq &> /dev/null; then
        log_info "jq 安装成功"
    else
        log_error "jq 安装失败"
        exit 1
    fi
    
    # 检查 IP 转发是否启用
    IP_FORWARD=$(cat /proc/sys/net/ipv4/ip_forward)
    if [ "$IP_FORWARD" == "1" ]; then
        log_info "IP 转发已启用"
    else
        log_warn "IP 转发未启用，请手动检查"
    fi
}

# ==================== 创建必要目录 ====================
create_directories() {
    log_info "正在创建必要目录..."
    
    # WireGuard 配置目录
    mkdir -p /etc/wireguard
    
    # 脚本日志目录
    mkdir -p /var/log/wireguard-vpn
    
    # 设置权限
    chmod 700 /etc/wireguard
    chmod 755 /var/log/wireguard-vpn
    
    log_info "目录创建完成"
}

# ==================== 主函数 ====================
main() {
    log_info "=========================================="
    log_info "WireGuard VPN 客户端安装脚本"
    log_info "=========================================="
    
    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 检测操作系统
    detect_os
    
    # 根据操作系统安装
    case $OS in
        ubuntu|debian)
            install_debian
            ;;
        centos|rhel|rocky|almalinux)
            install_centos
            ;;
        alpine)
            install_alpine
            ;;
        *)
            log_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    # 创建目录
    create_directories
    
    # 验证安装
    verify_installation
    
    log_info "=========================================="
    log_info "安装完成！"
    log_info "=========================================="
    log_info ""
    log_info "下一步："
    log_info "1. 编辑 /etc/wireguard/config.sh 配置服务器地址和令牌"
    log_info "2. 运行 /etc/wireguard/init.sh 初始化 VPN 配置"
    log_info ""
}

# 执行主函数
main "$@"

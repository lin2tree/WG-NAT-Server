# VM Scripts - 虚拟机 VPN 客户端脚本集

本目录包含在虚拟机上运行的 WireGuard VPN 客户端脚本，与 FCloudVPN 管理服务配套使用。

## 📖 目录结构

```
vm-scripts/
├── deploy.sh              # 一键部署脚本（推荐使用）
├── install.sh             # 依赖安装脚本
├── config.sh              # 配置文件模板
├── init.sh                # VPN 初始化脚本
├── report-ready.sh        # 就绪状态上报脚本
├── destroy.sh             # VPN 销毁脚本
├── status.sh              # 状态检查脚本
├── systemd/               # Systemd 服务文件
│   └── wg-quick@.service
└── README.md              # 本文档
```

## 🚀 快速开始

### 方式一：一键部署（推荐）

```bash
# 1. 下载脚本到虚拟机
git clone https://github.com/lin2tree/WG-NAT-Server.git
cd WG-NAT-Server/vm-scripts

# 2. 运行一键部署脚本
sudo bash deploy.sh

# 3. 按提示输入配置信息
# - VPN 管理服务地址（例如：http://192.168.1.10:8000）
# - VM 认证令牌（从管理员获取）
# - WireGuard 接口名称（默认：wg0）
```

### 方式二：手动部署

```bash
# 1. 安装依赖
sudo bash install.sh

# 2. 编辑配置文件
sudo cp config.sh /etc/wireguard/
sudo vi /etc/wireguard/config.sh

# 3. 修改以下配置项
VPN_SERVER_URL="http://YOUR_SERVER_IP:8000"
VM_TOKEN="YOUR_VM_TOKEN_HERE"

# 4. 运行初始化脚本
sudo bash /etc/wireguard/init.sh

# 5. 检查状态
sudo bash /etc/wireguard/status.sh
```

## 📋 脚本说明

### 1. deploy.sh - 一键部署脚本

**功能**: 自动完成安装、配置、初始化全流程

**用法**:
```bash
# 交互式部署
sudo bash deploy.sh

# 命令行参数部署
sudo bash deploy.sh \
  --server http://192.168.1.10:8000 \
  --token your_vm_token \
  --interface wg0
```

**参数**:
| 参数 | 说明 | 示例 |
|-----|------|------|
| `-s, --server` | VPN 管理服务地址 | `http://192.168.1.10:8000` |
| `-t, --token` | VM 认证令牌 | `your_vm_token` |
| `-i, --interface` | WireGuard 接口名称 | `wg0` |
| `--no-start` | 配置后不自动启动 | - |

---

### 2. install.sh - 依赖安装脚本

**功能**: 安装 WireGuard 及相关依赖

**用法**:
```bash
sudo bash install.sh
```

**安装内容**:
- WireGuard Tools
- curl
- jq
- net-tools

**支持系统**:
- Ubuntu / Debian
- CentOS / RHEL / Rocky Linux / AlmaLinux
- Alpine Linux

---

### 3. config.sh - 配置文件

**功能**: 存储 VPN 连接配置参数

**配置项**:
| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `VPN_SERVER_URL` | VPN 管理服务地址 | - |
| `VM_TOKEN` | VM 认证令牌 | - |
| `WG_INTERFACE` | WireGuard 接口名称 | `wg0` |
| `WG_PORT` | WireGuard 监听端口 | `2588` |
| `LOG_DIR` | 日志目录 | `/var/log/wireguard-vpn` |
| `LOG_FILE` | 日志文件路径 | `${LOG_DIR}/vpn-client.log` |
| `LOG_RETENTION_DAYS` | 日志保留天数 | `30` |
| `API_TIMEOUT` | API 请求超时时间（秒） | `30` |
| `MAX_RETRIES` | 最大重试次数 | `3` |
| `RETRY_INTERVAL` | 重试间隔（秒） | `5` |
| `DEBUG` | 是否启用调试模式 | `false` |
| `AUTO_START` | 是否自动启动 | `true` |

---

### 4. init.sh - VPN 初始化脚本

**功能**: 向 VPN 管理服务请求配置并启动 WireGuard

**流程**:
1. 检查依赖
2. 获取本机 IP 地址
3. 向管理服务请求 VPN 配置
4. 生成 WireGuard 配置文件
5. 启动 WireGuard 服务
6. 上报就绪状态
7. 设置开机自启

**用法**:
```bash
sudo bash init.sh
```

**生成文件**:
- `/etc/wireguard/wg0.conf` - WireGuard 配置文件
- `/var/log/wireguard-vpn/vpn-client.log` - 日志文件

---

### 5. report-ready.sh - 就绪状态上报脚本

**功能**: 手动上报或重新上报 VPN 就绪状态

**用法**:
```bash
# 正常上报
sudo bash report-ready.sh

# 强制上报（跳过状态检查）
sudo bash report-ready.sh --force

# 显示详细输出
sudo bash report-ready.sh --verbose
```

**参数**:
| 参数 | 说明 |
|-----|------|
| `-h, --help` | 显示帮助信息 |
| `-f, --force` | 强制上报（不检查 WireGuard 状态） |
| `-v, --verbose` | 显示详细输出 |

---

### 6. destroy.sh - VPN 销毁脚本

**功能**: 停止 WireGuard 服务并清理配置文件

**用法**:
```bash
# 交互式清理
sudo bash destroy.sh

# 保留日志文件
sudo bash destroy.sh --keep-logs

# 强制清理（不询问确认）
sudo bash destroy.sh --force
```

**参数**:
| 参数 | 说明 |
|-----|------|
| `-h, --help` | 显示帮助信息 |
| `-k, --keep-logs` | 保留日志文件 |
| `-f, --force` | 强制清理（不询问确认） |
| `-v, --verbose` | 显示详细输出 |

**操作内容**:
1. 停止 WireGuard 服务
2. 禁用开机自启
3. 清理 iptables 规则
4. 备份并删除配置文件
5. 可选：清理日志文件

---

### 7. status.sh - 状态检查脚本

**功能**: 检查 VPN 连接状态和配置信息

**用法**:
```bash
# 显示状态摘要
sudo bash status.sh

# 显示所有检查项
sudo bash status.sh --all

# 显示日志内容
sudo bash status.sh --logs
```

**参数**:
| 参数 | 说明 |
|-----|------|
| `-h, --help` | 显示帮助信息 |
| `-a, --all` | 显示所有检查项 |
| `-l, --logs` | 显示日志内容 |
| `-v, --verbose` | 显示详细输出 |

**检查项**:
- WireGuard 安装状态
- WireGuard 运行状态
- 配置文件状态
- 网络连接状态
- 系统服务状态
- 日志文件状态

---

## 🔄 工作流程

### 初始化流程

```
┌─────────────────┐
│  虚拟机启动      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  运行 init.sh   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  获取本机 IP     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 请求 VPN 配置    │◄────── VPN 管理服务
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 生成配置文件     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 启动 WireGuard  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  上报就绪状态    │───────► VPN 管理服务
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  设置开机自启    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   初始化完成     │
└─────────────────┘
```

### 销毁流程

```
┌─────────────────┐
│  运行 destroy.sh │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  停止 WireGuard  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  禁用开机自启    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 清理 iptables   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  备份配置文件    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  删除配置文件    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   清理完成       │
└─────────────────┘
```

---

## 🔧 常用命令

### WireGuard 管理

```bash
# 启动 VPN
wg-quick up wg0

# 停止 VPN
wg-quick down wg0

# 重启 VPN
wg-quick down wg0 && wg-quick up wg0

# 查看状态
wg show wg0

# 查看接口信息
ip addr show wg0
```

### 日志查看

```bash
# 查看实时日志
tail -f /var/log/wireguard-vpn/vpn-client.log

# 查看最近 100 行日志
tail -100 /var/log/wireguard-vpn/vpn-client.log

# 搜索日志
grep "ERROR" /var/log/wireguard-vpn/vpn-client.log
```

### 网络诊断

```bash
# 检查端口监听
netstat -tulnp | grep 2588

# 检查路由
ip route show table all

# 测试 VPN 连接
ping 10.1.0.1  # 替换为 VPN 网关地址
```

---

## 🐛 故障排查

### 问题 1: 无法连接到 VPN 管理服务

**症状**: `请求 VPN 配置失败`

**排查步骤**:
1. 检查网络连接
   ```bash
   ping YOUR_SERVER_IP
   curl -v http://YOUR_SERVER_IP:8000/health
   ```

2. 检查防火墙
   ```bash
   # 检查出站规则
   iptables -L OUTPUT -n -v
   ```

3. 检查配置
   ```bash
   cat /etc/wireguard/config.sh | grep VPN_SERVER_URL
   ```

---

### 问题 2: WireGuard 启动失败

**症状**: `WireGuard 启动失败`

**排查步骤**:
1. 检查配置文件语法
   ```bash
   wg-quick up wg0 --verbose
   ```

2. 检查端口占用
   ```bash
   netstat -tulnp | grep 2588
   ```

3. 检查内核模块
   ```bash
   lsmod | grep wireguard
   modprobe wireguard
   ```

4. 查看详细错误
   ```bash
   journalctl -u wg-quick@wg0 -n 50
   ```

---

### 问题 3: 就绪状态上报失败

**症状**: `就绪状态上报失败: 记录已销毁`

**原因**: 配置已被外部前端应用销毁

**解决**: 重新运行 init.sh 获取新配置
```bash
sudo bash /etc/wireguard/init.sh
```

---

### 问题 4: VPN 连接不通

**症状**: 无法 ping 通 VPN 网关

**排查步骤**:
1. 检查 WireGuard 状态
   ```bash
   wg show wg0
   ```

2. 检查 IP 转发
   ```bash
   cat /proc/sys/net/ipv4/ip_forward
   ```

3. 检查防火墙规则
   ```bash
   iptables -L -n -v
   iptables -t nat -L -n -v
   ```

4. 检查路由
   ```bash
   ip route show
   ```

---

## 📝 配置示例

### 最小配置

```bash
# /etc/wireguard/config.sh
VPN_SERVER_URL="http://192.168.1.10:8000"
VM_TOKEN="your_vm_token_here"
WG_INTERFACE="wg0"
```

### 完整配置

```bash
# /etc/wireguard/config.sh
VPN_SERVER_URL="http://192.168.1.10:8000"
VM_TOKEN="your_vm_token_here"
WG_INTERFACE="wg0"
WG_PORT=2588
LOG_DIR="/var/log/wireguard-vpn"
LOG_FILE="${LOG_DIR}/vpn-client.log"
LOG_RETENTION_DAYS=30
INTERNAL_INTERFACE="eth0"
API_TIMEOUT=30
MAX_RETRIES=3
RETRY_INTERVAL=5
DEBUG=false
AUTO_START=true
```

---

## 🔐 安全建议

1. **保护配置文件**
   ```bash
   chmod 600 /etc/wireguard/config.sh
   chmod 600 /etc/wireguard/wg0.conf
   ```

2. **定期更新令牌**
   - 联系管理员定期更换 VM Token

3. **监控日志**
   ```bash
   # 设置日志监控
   tail -f /var/log/wireguard-vpn/vpn-client.log | grep -E "ERROR|WARN"
   ```

4. **限制访问权限**
   ```bash
   # 仅允许 root 访问
   chown -R root:root /etc/wireguard
   chmod 700 /etc/wireguard
   ```

---

## 📚 相关文档

- [WireGuard 官方文档](https://www.wireguard.com/)
- [FCloudVPN 主项目文档](../README.md)
- [前端功能文档](../前端功能.md)

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📞 支持

如有问题，请联系：
- 项目主页: https://github.com/lin2tree/WG-NAT-Server
- 问题反馈: https://github.com/lin2tree/WG-NAT-Server/issues

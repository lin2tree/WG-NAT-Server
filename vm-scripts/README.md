# VM Scripts - 虚拟机 VPN 客户端脚本

本目录包含在虚拟机上运行的 WireGuard VPN 客户端一次性初始化脚本，与 FCloudVPN 管理服务配套使用。

## 📖 目录结构

```
vm-scripts/
├── one-shot.sh    # 一次性初始化脚本（唯一需要的脚本）
└── README.md      # 本文档
```

## 🚀 快速开始

### 使用方式

**方式一：环境变量**
```bash
export VPN_SERVER_URL="http://192.168.1.10:8000"
export VM_TOKEN="your_vm_token"
sudo -E bash one-shot.sh
```

**方式二：命令行参数**
```bash
sudo bash one-shot.sh \
  --server http://192.168.1.10:8000 \
  --token your_vm_token
```

**方式三：cloud-init 配置**
```yaml
#cloud-config
runcmd:
  - VPN_SERVER_URL=http://192.168.1.10:8000 VM_TOKEN=your_token /path/to/one-shot.sh
```

**方式四：systemd 服务**
```ini
[Unit]
Description=VPN One-Shot Initialization
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
Environment="VPN_SERVER_URL=http://192.168.1.10:8000"
Environment="VM_TOKEN=your_token"
ExecStart=/path/to/one-shot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

## 📋 脚本说明

### one-shot.sh - 一次性初始化脚本

**功能**: 虚拟机首次启动时自动配置 VPN，执行成功后自动删除脚本防止 Token 泄露

**参数**:
| 参数 | 说明 | 示例 |
|-----|------|------|
| `-s, --server` | VPN 管理服务地址 | `http://192.168.1.10:8000` |
| `-t, --token` | VM 认证令牌 | `your_vm_token` |
| `-i, --interface` | WireGuard 接口名称 | `wg0` |
| `--no-delete` | 执行后不删除脚本 | - |

**特点**:
- ✅ 完全无人值守，无需交互
- ✅ 自动检测操作系统并安装依赖
- ✅ 自动获取本机 IP 和网络接口
- ✅ 完整的超时和重试机制
- ✅ 执行成功后自动删除脚本，防止 Token 泄露
- ✅ 清除历史记录和环境变量中的敏感信息

**执行流程**:
1. 验证配置参数
2. 检测操作系统
3. 安装 WireGuard 及依赖
4. 获取本机 IP 地址
5. 向管理服务请求 VPN 配置
6. 生成 WireGuard 配置文件
7. 启动 WireGuard 服务
8. 上报就绪状态
9. 设置开机自启
10. 清理脚本文件

## 🔧 常用命令

### WireGuard 管理

```bash
# 查看状态
wg show wg0

# 停止 VPN
wg-quick down wg0

# 启动 VPN
wg-quick up wg0

# 重启 VPN
wg-quick down wg0 && wg-quick up wg0
```

### 日志查看

```bash
# 查看实时日志
tail -f /var/log/wireguard-vpn/one-shot.log

# 查看最近日志
tail -100 /var/log/wireguard-vpn/one-shot.log
```

## 🐛 故障排查

### 问题 1: 无法连接到 VPN 管理服务

**排查步骤**:
```bash
# 检查网络连接
ping YOUR_SERVER_IP

# 检查服务可达性
curl -v http://YOUR_SERVER_IP:8000/health
```

### 问题 2: WireGuard 启动失败

**排查步骤**:
```bash
# 检查配置文件
cat /etc/wireguard/wg0.conf

# 手动启动查看错误
wg-quick up wg0 --verbose

# 查看系统日志
journalctl -u wg-quick@wg0 -n 50
```

### 问题 3: 脚本执行失败

**排查步骤**:
```bash
# 查看日志
cat /var/log/wireguard-vpn/one-shot.log

# 手动重新执行
sudo bash one-shot.sh --server ... --token ... --no-delete
```

## 🔐 安全建议

1. **Token 安全**: 脚本执行成功后会自动删除，防止 Token 泄露
2. **环境变量**: 推荐通过环境变量注入 Token，避免命令行历史记录泄露
3. **权限控制**: 确保脚本文件权限为 600
4. **网络隔离**: 确保 VM Token 仅用于可信的虚拟机

## 📚 相关文档

- [WireGuard 官方文档](https://www.wireguard.com/)
- [FCloudVPN 主项目文档](../README.md)

## 📄 许可证

MIT License

## 📞 支持

如有问题，请联系：
- 项目主页: https://github.com/lin2tree/WG-NAT-Server
- 问题反馈: https://github.com/lin2tree/WG-NAT-Server/issues

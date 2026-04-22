# VM Scripts - 虚拟机 VPN 客户端脚本

本目录包含在虚拟机上运行的 WireGuard VPN 客户端一次性初始化脚本，与 FCloudVPN 管理服务配套使用。

## 📖 目录结构

```
vm-scripts/
├── one-shot.sh    # 一次性初始化脚本
└── README.md      # 本文档
```

## 🚀 快速开始

### 部署方式

管理系统在生成脚本时，替换以下占位符：

```bash
VPN_SERVER_URL="http://YOUR_SERVER_IP:8000"  # 替换为实际服务器地址
VM_TOKEN="YOUR_VM_TOKEN"                      # 替换为实际 Token
```

### 运行脚本

```bash
sudo bash one-shot.sh
```

## 📋 脚本说明

### one-shot.sh - 一次性初始化脚本

**功能**: 虚拟机首次启动时自动配置 VPN，执行成功后自动删除脚本防止 Token 泄露

**特点**:
- ✅ 完全无人值守，无需交互
- ✅ 无配置文件依赖，参数硬编码
- ✅ 无本地日志，错误信息上报到服务器
- ✅ 执行成功后自动删除脚本，防止 Token 泄露
- ✅ 错误信息通过 API 上报到管理后台

**执行流程**:
1. 请求 `/api/vm/config` 获取 VPN 配置
2. 写入 `/etc/wireguard/wg0.conf`
3. 启动 WireGuard 服务
4. 检查服务状态
5. 上报结果到 `/api/vm/ready`（成功或错误信息）
6. 删除脚本自身

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

## 🐛 故障排查

### 问题 1: 无法连接到 VPN 管理服务

```bash
# 检查网络连接
ping YOUR_SERVER_IP

# 检查服务可达性
curl -v http://YOUR_SERVER_IP:8000/health
```

### 问题 2: WireGuard 启动失败

```bash
# 检查配置文件
cat /etc/wireguard/wg0.conf

# 手动启动查看错误
wg-quick up wg0

# 查看系统日志
journalctl -u wg-quick@wg0 -n 50
```

### 问题 3: 查看错误信息

错误信息会上报到管理后台，请在管理后台的**日志**页面查看。

## 🔐 安全建议

1. **Token 安全**: 脚本执行成功后会自动删除，防止 Token 泄露
2. **权限控制**: 确保脚本文件权限为 600
3. **网络隔离**: 确保 VM Token 仅用于可信的虚拟机

## 📚 相关文档

- [WireGuard 官方文档](https://www.wireguard.com/)
- [FCloudVPN 主项目文档](../README.md)

## 📄 许可证

MIT License

## 📞 支持

如有问题，请联系：
- 项目主页: https://github.com/lin2tree/WG-NAT-Server
- 问题反馈: https://github.com/lin2tree/WG-NAT-Server/issues

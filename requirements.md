# 云环境 WireGuard VPN 管理服务产品需求文档 (PRD)

## 1. 项目背景

在云端局域网（VPC）环境下，虚拟机通常不具备公网 IP。为了实现运维人员能够从公网安全、可控地连接到特定的虚拟机，本项目旨在构建一个后台服务，通过预设防火墙端口映射，自动管理和分发 WireGuard VPN 配置。

## 2. 系统角色与网络架构

### 2.1 系统角色

- **虚拟机 (VM)**：运行在云端局域网，执行一次性初始化脚本。
- **本服务 (VPN Manager)**：核心控制单元，负责秘钥生成、状态管理及 API 提供。
- **前端应用 (Management Console)**：供运维人员查看状态、下载配置、执行销毁。
- **用户电脑 (Client)**：安装 WireGuard 客户端，通过下载的配置连接虚拟机。

### 2.2 网络与网段逻辑

- **前置条件**：所有虚拟机的内网 IP 必须属于同一个大类网段（B类地址一致），例如：`172.26.x.x`。
- **VPN 网段自动映射**：
  - 若 VM 内网 IP 为 `A.B.C.D`，则其 VPN 网段固定为 `10.C.D.0/24`。
  - **虚拟机侧 IP**：`10.C.D.254`
  - **客户端侧 IP**：`10.C.D.1` 至 `10.C.D.5`（每个 VM 预生成 5 个客户端配置）。
- **端口映射规则**：管理员预先建立映射关系池：`私网IP:2588 <-> 公网IP:随机UDP端口`。

## 3. 核心业务流程

1. **资源初始化**：Root 管理员导入内网 IP 与公网端口的映射表。
2. **VM 首次启动**：执行一次性脚本，通过内网 API 请求配置。
3. **配置生成**：服务根据请求来源 IP（Source IP）识别 VM，生成 Server/Client 秘钥对，存入数据库。
4. **状态锁定**：VM 脚本启动 WireGuard 成功后，通过 API 上报 `started` 状态，随后脚本自毁。
5. **用户接入**：用户通过管理后台下载客户端配置，建立加密隧道。
6. **资源回收**：前端发起销毁请求，服务将配置移入归档表，释放 IP 占用状态。

## 4. API 接口定义

*所有接口均使用* ***POST*** *方法，并采用* ***HTTPS*** *加密。*

### 4.1 虚拟机端接口

- **获取配置 (`/api/v1/vpn/provision`)**
  - **鉴权**：固化 Token + 请求来源 IP 校验。
  - **逻辑**：仅允许 `init` 状态请求。返回 Server 端配置。
- **上报就绪 (`/api/v1/vpn/ready`)**
  - **逻辑**：将状态由 `created` 更新为 `started`。此后该 IP 无法再请求秘钥。

### 4.2 管理端接口

- **查询客户端配置 (`/api/v1/vpn/query_client`)**
  - **鉴权**：管理员 Token。
  - **功能**：返回指定 IP 的 5 个客户端配置 JSON（含备注名）。
- **销毁配置 (`/api/v1/vpn/decommission`)**
  - **鉴权**：管理员 Token。
  - **功能**：将记录移入 `vpn_archives`，标记 `deleted_at`，清理 `vpn_configs`。

## 5. 数据库设计 (PostgreSQL)

### 5.1 vpn\_resource\_pool (资源池)

- `internal_ip` (PK), `internal_port` (2588), `public_ip`, `public_port`, `status` (available/in\_use)

### 5.2 vpn\_configs (活跃配置)

- `id` (SERIAL), `internal_ip`, `vpn_subnet`, `server_config`, `client_configs` (JSONB), `status` (created/started), `created_at`, `started_at`

### 5.3 vpn\_archives (归档记录)

- 结构同 `vpn_configs`，增加 `deleted_at` 字段。

## 6. 管理后台功能要求

- **角色区分**：
  - **Root**：全权限，可查看明文秘钥，可导入/修改资源池映射。
  - **Admin**：仅查看权限，秘钥字段必须进行 **星号 (\*) 脱敏** 处理。
- **查询逻辑 (拆分展示)**：
  - 默认展示 `vpn_configs` 表中的活跃记录。
  - 提供“查看历史”按钮，点击后弹窗展示该 IP 在 `vpn_archives` 中的历史记录。
- **导入逻辑**：批量导入 IP 段时，系统必须自动校验 IP 地址前两位（B类）的一致性。

## 7. 技术约束

### 1. 幂等性与状态锁 (Strict Idempotency)

- **细节补充**：在 `provision` 接口逻辑中，必须明确：若请求 IP 对应的状态为 `created`，必须返回**相同**的秘钥和配置。这是为了防止虚拟机脚本在安装过程中因网络抖动重试时，导致前后秘钥不一致而连接失败。

### 2. 安全性加固 (Source IP Binding)

- **细节补充**：后端在处理 `provision` 接口时，**严禁**从 JSON Body 中读取 IP 地址。必须强制从 TCP 报文头的 `RemoteAddr` 中提取请求来源 IP。这在代码实现层面是防止“越权获取他人秘钥”的核心屏障。

### 3. 配置模板的完整性 (WireGuard Standard)

- **细节补充**：Server 端配置必须包含 `PostUp` 和 `PostDown` 的 `iptables` 规则（用于开启 NAT 转发），且 Client 端必须包含 `PersistentKeepalive = 25`。如果不写这两项，用户连接后将无法访问虚拟机局域网，且连接容易因云端防火墙超时而中断。


# 云环境 WireGuard VPN 管理服务产品需求文档 (PRD)

## 1. 项目背景

在云端局域网（VPC）环境下，虚拟机通常不具备公网 IP。为了实现运维人员能够从公网安全、可控地连接到特定的虚拟机，本项目旨在构建一个后台服务，通过预设防火墙端口映射，自动管理和分发 WireGuard VPN 配置。

## 2. 系统角色与网络架构

### 2.1 系统角色

- **虚拟机 (VM)**：运行在云端局域网，执行一次性初始化脚本，通过 VM Token 访问后端 API。
- **本服务 (VPN Manager)**：核心控制单元，负责秘钥生成、状态管理及 API 提供。
  - **Frontend**: 前端服务（nginx），供管理员通过浏览器访问
  - **Backend**: 后端服务（FastAPI），提供所有 API 接口
- **第三方应用 (3rd App)**：通过第三方应用 Token 访问 backend，获取配置信息或销毁虚拟机配置。
- **用户电脑 (Client)**：安装 WireGuard 客户端，通过下载的配置连接虚拟机。

### 2.2 网络与网段逻辑

- **前置条件**：所有虚拟机的内网 IP 必须属于同一个大类网段（B类地址一致），例如：`10.11.x.x`。
- **VPN 网段自动映射**：
  - 若 VM 内网 IP 为 `A.B.C.D`，则其 VPN 网段固定为 `{VPN_SUBNET}.C.D.0/24`（默认 VPN_SUBNET=10）。
  - **虚拟机侧 IP**：`{VPN_SUBNET}.C.D.254`
  - **客户端侧 IP**：`{VPN_SUBNET}.C.D.1` 至 `{VPN_SUBNET}.C.D.N`（每个 VM 预生成 N 个客户端配置，默认 N=6，可通过 `WIREGUARD_CLIENT_COUNT` 配置）。
- **端口映射规则**：管理员预先建立映射关系池：`私网IP:2588 <-> 公网IP:随机UDP端口`。
- **公网IP管理**：支持导入多个公网IP，可指定默认公网IP，每个VM可单独配置使用的公网IP。

## 3. 核心业务流程

1. **资源初始化**：Admin 管理员导入公网IP、设置端口范围、导入内网 IP 与公网端口的映射表。
2. **VM 首次启动**：执行一次性脚本，通过 VM Token 认证请求配置。
3. **配置生成**：服务根据请求来源 IP（从 TCP 层获取）识别 VM，生成 Server/Client 秘钥对，存入数据库。
4. **状态锁定**：VM 脚本启动 WireGuard 成功后，通过 API 上报 `started` 状态，随后脚本自毁。
5. **用户接入**：
   - 管理员通过管理后台下载客户端配置
   - 第三方应用通过 API 下载客户端配置
6. **资源回收**：第三方应用发起销毁请求，服务将配置移入归档表，释放 IP 占用状态。

## 4. API 接口定义

### 4.1 认证方式

系统使用三种独立的 Token：

| Token 类型      | 用途           | 格式    | 配置项                |
| -------------- | -------------- | ------- | -------------------- |
| VM Token       | VM 访问后端 API | 简单字符串 | `VM_TOKEN`           |
| 第三方应用 Token | 第三方应用访问 API | 简单字符串 | `THIRD_PARTY_TOKEN`  |
| JWT Token      | 浏览器管理员访问 | JWT 格式 | `ADMIN_JWT_SECRET`   |

**重要**：三种 Token 完全独立，不可互换使用！

### 4.2 虚拟机端接口 (VM API)

**基础路径**: `/api/vm/*`

**认证**: VM Token + TCP 层 IP 验证

#### 获取配置

- **路径**: `GET /api/vm/config`
- **鉴权**: VM Token + 请求来源 IP 校验（从 TCP 层获取，不信任任何 HTTP Header）
- **逻辑**: 
  - 若配置不存在，创建新配置并返回
  - 若配置存在且状态为 `init`，返回已有配置（幂等）
  - 若配置存在且状态为 `started`，返回错误
- **响应**: 返回 Server 端配置

#### 上报就绪

- **路径**: `POST /api/vm/ready`
- **鉴权**: VM Token
- **逻辑**: 将状态由 `init` 更新为 `started`

### 4.3 第三方应用接口 (3rd API)

**基础路径**: `/api/3rd/*`

**认证**: 第三方应用 Token

#### 查询配置概况

- **路径**: `GET /api/3rd/configs/{vm_ip}/info`
- **功能**: 返回指定 IP 的客户端配置概况（私钥脱敏）
- **前置条件**: VM 状态必须为 `started`

#### 下载客户端配置

- **路径**: `GET /api/3rd/configs/{vm_ip}/download`
- **功能**: 下载所有客户端配置文件（wg.conf）
- **前置条件**: VM 状态必须为 `started`

#### 销毁配置

- **路径**: `POST /api/3rd/configs/{vm_ip}/destroy`
- **功能**: 将记录移入 `vpn_archives`，标记 `deleted_at`，清理 `vpn_configs`

### 4.4 管理端接口 (Admin API)

**基础路径**: `/api/admin/*`

**认证**: JWT Token

#### 公网 IP 管理

| 方法     | 路径                                   | 说明     | 权限   |
| -------- | -------------------------------------- | -------- | ------ |
| GET      | `/api/admin/public-ips`                | 列出公网IP | 所有用户 |
| POST     | `/api/admin/public-ips`                | 导入公网IP | Admin  |
| PUT      | `/api/admin/public-ips/{id}/default`   | 设为默认  | Admin  |
| DELETE   | `/api/admin/public-ips/{id}`           | 删除公网IP | Admin  |

#### 端口范围管理

| 方法 | 路径                      | 说明     | 权限   |
| ---- | ----------------------- | ------ | ------ |
| GET  | `/api/admin/port-range` | 获取端口范围 | 所有用户 |
| POST | `/api/admin/port-range` | 设置端口范围 | Admin  |

#### 资源池管理

| 方法     | 路径                                        | 说明     | 权限   |
| -------- | ------------------------------------------- | -------- | ------ |
| GET      | `/api/admin/resource-pool`                  | 列出资源池 | 所有用户 |
| POST     | `/api/admin/resource-pool/import`           | 导入IP   | Admin  |
| DELETE   | `/api/admin/resource-pool/{id}`             | 删除映射  | Admin  |
| POST     | `/api/admin/resource-pool/batch-delete`     | 批量删除  | Admin  |
| GET      | `/api/admin/resource-pool/export`           | 导出CSV  | Admin  |
| PUT      | `/api/admin/resource-pool/{id}/public-ip`   | 更新公网IP | Admin  |

#### VPN 配置管理

| 方法 | 路径                                                  | 说明       | 权限   |
| ---- | ----------------------------------------------------- | ---------- | ------ |
| GET  | `/api/admin/configs`                                  | 列出配置   | 所有用户 |
| GET  | `/api/admin/configs/{vm_ip}`                          | 配置详情   | 所有用户 |
| GET  | `/api/admin/configs/{vm_ip}/clients`                  | 客户端配置 | 所有用户 |
| GET  | `/api/admin/configs/{vm_ip}/download/server`          | 下载服务器配置 | Admin  |
| GET  | `/api/admin/configs/{vm_ip}/download/client/{name}`   | 下载客户端配置 | Admin  |
| GET  | `/api/admin/configs/{vm_ip}/download/clients`         | 下载所有客户端 | Admin  |
| GET  | `/api/admin/configs/export`                           | 导出CSV   | Admin  |

#### 归档管理

| 方法 | 路径                           | 说明    | 权限   |
| ---- | ------------------------------ | ------- | ------ |
| GET  | `/api/admin/archives`          | 列出归档 | 所有用户 |
| GET  | `/api/admin/archives/export`   | 导出CSV | Admin  |

#### 日志管理

| 方法 | 路径                | 说明   | 权限   |
| ---- | ------------------- | ------ | ------ |
| GET  | `/api/admin/logs`   | 列出日志 | 所有用户 |

#### 用户管理

| 方法     | 路径                              | 说明       | 权限   |
| -------- | --------------------------------- | ---------- | ------ |
| GET      | `/api/auth/users`                 | 列出用户   | Admin  |
| POST     | `/api/auth/users`                 | 创建用户   | Admin  |
| PUT      | `/api/auth/users/{id}`            | 更新用户   | Admin  |
| DELETE   | `/api/auth/users/{id}`            | 删除用户   | Admin  |
| PUT      | `/api/auth/users/{id}/password`   | 修改用户密码 | Admin  |

### 4.5 认证接口 (Auth API)

**基础路径**: `/api/auth/*`

#### 获取 RSA 公钥

- **路径**: `GET /api/auth/public-key`
- **功能**: 获取 RSA 公钥用于密码加密

#### 加密登录

- **路径**: `POST /api/auth/login/encrypted`
- **功能**: 使用 RSA-OAEP 加密密码登录
- **响应**: JWT Token

## 5. 数据库设计 (PostgreSQL)

### 5.1 public_ips (公网IP)

| 字段         | 类型        | 说明           |
| ------------ | ----------- | -------------- |
| id           | SERIAL PK   | 主键           |
| ip_address   | VARCHAR(45) | IP地址（唯一） |
| is_default   | BOOLEAN     | 是否为默认IP   |
| description  | VARCHAR(255)| 描述           |
| created_at   | DATETIME    | 创建时间       |

### 5.2 port_ranges (端口范围)

| 字段        | 类型      | 说明     |
| ----------- | --------- | -------- |
| id          | SERIAL PK | 主键     |
| start_port  | INTEGER   | 起始端口 |
| end_port    | INTEGER   | 结束端口 |
| created_at  | DATETIME  | 创建时间 |
| updated_at  | DATETIME  | 更新时间 |

### 5.3 resource_pools (资源池)

| 字段        | 类型        | 说明               |
| ----------- | ----------- | ------------------ |
| id          | SERIAL PK   | 主键               |
| internal_ip | VARCHAR(45) | 内网IP（唯一）     |
| public_ip_id| INTEGER FK  | 关联公网IP         |
| public_port | INTEGER     | 公网端口（唯一）   |
| created_at  | DATETIME    | 创建时间           |
| updated_at  | DATETIME    | 更新时间           |
| deleted_at  | DATETIME    | 软删除时间         |

### 5.4 vpn_configs (活跃配置)

| 字段               | 类型        | 说明                    |
| ------------------ | ----------- | ----------------------- |
| id                 | SERIAL PK   | 主键                    |
| vm_ip              | VARCHAR(45) | 虚拟机IP（唯一）        |
| server_private_key | TEXT        | 服务器私钥              |
| server_public_key  | TEXT        | 服务器公钥              |
| client_configs     | JSONB       | 客户端配置列表          |
| status             | VARCHAR(20) | 状态：init/started      |
| created_at         | DATETIME    | 创建时间                |
| started_at         | DATETIME    | 启动时间                |

### 5.5 vpn_archives (归档记录)

| 字段               | 类型        | 说明                    |
| ------------------ | ----------- | ----------------------- |
| id                 | SERIAL PK   | 主键                    |
| vm_ip              | VARCHAR(45) | 虚拟机IP                |
| server_private_key | TEXT        | 服务器私钥              |
| server_public_key  | TEXT        | 服务器公钥              |
| client_configs     | JSONB       | 客户端配置列表          |
| status             | VARCHAR(20) | 状态：deleted           |
| created_at         | DATETIME    | 创建时间                |
| deleted_at         | DATETIME    | 删除时间                |

### 5.6 users (用户)

| 字段          | 类型        | 说明               |
| ------------- | ----------- | ------------------ |
| id            | SERIAL PK   | 主键               |
| username      | VARCHAR(50) | 用户名（唯一）     |
| password_hash | VARCHAR(255)| 密码哈希           |
| role          | VARCHAR(20) | 角色：admin/user   |
| created_at    | DATETIME    | 创建时间           |

### 5.7 operation_logs (操作日志)

| 字段             | 类型        | 说明           |
| ---------------- | ----------- | -------------- |
| id               | SERIAL PK   | 主键           |
| request_time     | DATETIME    | 请求时间       |
| source_ip        | VARCHAR(45) | 来源IP         |
| request_path     | VARCHAR(255)| 请求路径       |
| request_method   | VARCHAR(10) | 请求方法       |
| request_params   | JSONB       | 请求参数       |
| response_status  | INTEGER     | 响应状态码     |
| response_time_ms | INTEGER     | 响应时间（毫秒）|
| error_message    | TEXT        | 错误信息       |

## 6. 管理后台功能要求

### 6.1 角色区分

| 角色  | 权限                                       |
| ----- | ------------------------------------------ |
| admin | 全权限，可查看明文秘钥，可导入/修改资源池映射 |
| user  | 仅查看权限，秘钥字段必须进行脱敏处理         |

### 6.2 界面功能

- **VPN 配置页面**：展示 `vpn_configs` 表中的活跃记录
- **已归档数据页面**：展示 `vpn_archives` 表中的历史记录
- **资源池页面**：管理公网IP、端口范围、VM IP映射
- **用户管理页面**：管理用户账号（仅 admin 可见完整功能）
- **操作日志页面**：查看所有 API 调用记录

### 6.3 安全特性

- **密码传输加密**：登录时密码使用 RSA-OAEP 加密传输
- **IP 验证**：VM API 直接从 TCP 层获取客户端 IP，不信任任何 HTTP Header
- **Token 分离**：VM Token、第三方应用 Token、JWT Token 完全独立

## 7. 技术约束

### 7.1 幂等性与状态锁 (Strict Idempotency)

- **细节补充**：在 `/api/vm/config` 接口逻辑中，若请求 IP 对应的配置已存在且状态为 `init`，必须返回**相同**的秘钥和配置。这是为了防止虚拟机脚本在安装过程中因网络抖动重试时，导致前后秘钥不一致而连接失败。

### 7.2 安全性加固 (Source IP Binding)

- **细节补充**：后端在处理 VM API 时，**严禁**从 JSON Body 或 HTTP Header 中读取 IP 地址。必须强制从 TCP 报文头的 `RemoteAddr` 中提取请求来源 IP。这在代码实现层面是防止"越权获取他人秘钥"的核心屏障。

### 7.3 配置模板的完整性 (WireGuard Standard)

- **Server 端配置**：
  - 必须包含 `PostUp` 和 `PostDown` 的 `iptables` 规则（用于开启 NAT 转发和 Peer 间通信）
  - 每个 Peer 必须包含 `PersistentKeepalive` 配置
- **Client 端配置**：
  - 必须包含 `PersistentKeepalive = 25`
  - Endpoint 必须使用正确的公网 IP（从资源池或默认公网 IP 获取）

### 7.4 公网 IP 获取优先级

客户端配置中的 Endpoint 公网 IP 按以下优先级获取：
1. 资源池中该 VM 关联的公网 IP
2. 数据库中标记为 `is_default=True` 的默认公网 IP
3. 兜底值：`YOUR_PUBLIC_IP`

## 8. 环境配置

### 8.1 必需配置项

| 变量                     | 说明              | 默认值               |
| ------------------------ | ----------------- | -------------------- |
| SERVER_IP                | 服务器IP地址       | localhost            |
| DB_PASSWORD              | 数据库密码         | -                    |
| DEFAULT_ADMIN_USERNAME   | 默认管理员用户名   | admin                |
| DEFAULT_ADMIN_PASSWORD   | 默认管理员密码     | admin123             |
| VM_TOKEN                 | VM访问Token       | vm_default_token     |
| THIRD_PARTY_TOKEN        | 第三方应用Token    | 3rd_default_token    |
| ADMIN_JWT_SECRET         | JWT密钥           | -                    |
| PUBLIC_IP                | WireGuard公网IP   | -                    |

### 8.2 可选配置项

| 变量                     | 说明              | 默认值 |
| ------------------------ | ----------------- | ------ |
| WIREGUARD_VPN_SUBNET     | VPN子网前缀       | 10     |
| WIREGUARD_SERVER_PORT    | WireGuard服务器端口 | 2588   |
| WIREGUARD_CLIENT_COUNT   | 每VM客户端数量    | 6      |
| WIREGUARD_KEEPALIVE      | Keepalive间隔(秒) | 25     |
| LOG_RETENTION_DAYS       | 日志保留天数      | 90     |
| ADMIN_JWT_EXPIRE_HOURS   | JWT过期时间(小时) | 24     |

# FCloud API 接口文档

## 目录

1. [架构概述](#架构概述)
2. [认证方式](#认证方式)
3. [API分类](#api分类)
4. [时序与依赖关系](#时序与依赖关系)
5. [接口详情](#接口详情)

***

## 架构概述

```
┌─────────────────────────────────────────────────────────────────┐
│                           服务器                                  │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │  frontend   │    │   backend   │    │  postgres   │          │
│  │   (nginx)   │    │  (FastAPI)  │    │  (数据库)    │          │
│  │   端口:80   │    │  端口:8000  │    │  端口:5432  │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│        ↑                   ↑                   ↑                 │
│    对外:80            对外:8000          仅内部访问              │
└────────┼───────────────────┼───────────────────┼─────────────────┘
         │                   │                   
    ┌────┴────┐         ┌────┴────┐
    │  浏览器  │         │VM / 3rd │
    │ (管理员) │         │   应用   │
    └─────────┘         └─────────┘
```

**术语说明**:

- **frontend**: 服务器上的前端服务（nginx），管理员通过浏览器访问
- **backend**: 服务器上的后端服务（FastAPI）
- **VM**: 虚拟机，通过 VM Token 访问 backend
- **3rd**: 第三方应用，通过第三方应用Token 访问 backend

***

## 认证方式

### 1. 浏览器管理员 (Frontend)

**认证方式**: JWT Token + RSA加密传输

**流程**:

1. 前端请求 `/api/auth/public-key` 获取RSA公钥
2. 前端使用公钥加密密码 (OAEP)
3. 发送加密后的密码到 `/api/auth/login/encrypted`
4. 后端返回JWT Token
5. 后续请求携带 `Authorization: Bearer <jwt token>`

### 2. VM (虚拟机)

**认证方式**: VM Token + TCP层IP验证

**流程**:

1. VM发送请求携带 `Authorization: Bearer <vm_token>`
2. 后端从TCP连接获取VM真实IP（不信任任何header）
3. 使用IP作为VM身份标识

**安全特性**:

- 直接从TCP层获取客户端IP，防止IP伪造
- 不信任 X-Forwarded-For 等header
- VM Token 与第三方应用Token 完全独立

### 3. 第三方应用 (3rd App)

**认证方式**: 第三方应用Token (预置Token)

**流程**:

1. 第三方应用发送请求携带 `Authorization: Bearer <third_party_token>`
2. 后端验证Token有效性

**安全特性**:

- 使用预置的 THIRD_PARTY_TOKEN，与 VM Token 完全独立

***

## API分类

### 按访问者分类

| API路径          | 访问者    | 认证方式      | 说明     |
| -------------- | ------ | --------- | ------ |
| `/api/vm/*`    | VM     | VM Token  | VM配置管理 |
| `/api/3rd/*`   | 第三方应用  | 第三方应用Token | 第三方集成  |
| `/api/admin/*` | 浏览器管理员 | JWT Token | 管理后台   |
| `/api/auth/*`  | 所有     | 混合        | 认证相关   |

### 按功能分类

| 功能模块  | API路径                        | 说明         |
| ----- | ---------------------------- | ---------- |
| VM配置  | `/api/vm/*`                  | VM初始化和状态报告 |
| 第三方集成 | `/api/3rd/*`                 | 配置查询、下载、销毁 |
| 认证    | `/api/auth/*`                | 登录、用户管理    |
| 公网IP  | `/api/admin/public-ips/*`    | 公网IP管理     |
| 端口范围  | `/api/admin/port-range`      | 端口范围配置     |
| 资源池   | `/api/admin/resource-pool/*` | VM IP资源管理  |
| VPN配置 | `/api/admin/configs/*`       | VPN配置管理    |
| 归档    | `/api/admin/archives/*`      | 已销毁配置查询    |
| 日志    | `/api/admin/logs`            | 操作日志       |

***

## 时序与依赖关系

### 1. VM初始化流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│   VM    │     │ Backend │     │Resource │     │  VPN    │
│         │     │         │     │  Pool   │     │ Config  │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │
     │ GET /api/vm/config            │               │
     │──────────────>│               │               │
     │               │ 查询资源池     │               │
     │               │──────────────>│               │
     │               │ 返回端口映射   │               │
     │               │<──────────────│               │
     │               │               │   创建配置    │
     │               │──────────────────────────────>│
     │               │               │   返回配置    │
     │               │<──────────────────────────────│
     │ 返回服务器配置 │               │               │
     │<──────────────│               │               │
     │               │               │               │
     │ POST /api/vm/ready            │               │
     │──────────────>│               │               │
     │               │   更新状态    │               │
     │               │──────────────────────────────>│
     │ 返回成功       │               │               │
     │<──────────────│               │               │
     │               │               │               │
```

**依赖关系**:

- VM调用 `/api/vm/config` 前，资源池中必须已有该VM的IP记录
- 资源池记录由管理员通过 `/api/admin/resource-pool/import` 导入

### 2. 第三方应用流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  3rd    │     │ Backend │     │  VPN    │
│  App    │     │         │     │ Config  │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     │ GET /api/3rd/configs/{vm_ip}/info
     │──────────────>│               │
     │               │   查询配置    │
     │               │──────────────>│
     │               │   返回配置    │
     │               │<──────────────│
     │ 返回客户端配置 │               │
     │<──────────────│               │
     │               │               │
     │ GET /api/3rd/configs/{vm_ip}/download
     │──────────────>│               │
     │ 返回配置文件   │               │
     │<──────────────│               │
     │               │               │
     │ POST /api/3rd/configs/{vm_ip}/destroy
     │──────────────>│               │
     │               │   归档配置    │
     │               │──────────────>│
     │ 返回成功       │               │
     │<──────────────│               │
     │               │               │
```

**依赖关系**:

- 查询客户端配置: VM状态必须为 `started`
- 下载配置文件: VM状态必须为 `started`
- 销毁配置: 配置必须存在且未销毁

### 3. 状态流转图

```
                    ┌──────────────┐
                    │  资源池导入   │
                    │ (管理员操作)  │
                    └──────┬───────┘
                           │
                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   资源池      │───>│   VM调用     │───>│   VM调用     │
│  (待分配)     │    │  /vm/config  │    │  /vm/ready   │
└──────────────┘    │  (初始化)    │    │  (启动)      │
                    └──────────────┘    └──────┬───────┘
                                               │
                    ┌──────────────┐           │
                    │  3rd调用      │<──────────┘
                    │  /destroy    │
                    │  (销毁归档)   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   归档表      │
                    │  (已销毁)     │
                    └──────────────┘
```

### 4. 接口依赖与互斥关系

| 操作                 | 前置条件            | 后置影响            | 互斥操作     |
| ------------------ | --------------- | --------------- | -------- |
| VM初始化 `/vm/config` | 资源池有对应IP        | 创建VPN配置，状态=init | -        |
| VM就绪 `/vm/ready`   | 配置存在，状态=init    | 状态=started      | -        |
| 3rd查询配置            | 配置存在，状态=started | -               | 销毁后无法查询  |
| 3rd下载配置            | 配置存在，状态=started | -               | 销毁后无法下载  |
| 3rd销毁配置            | 配置存在            | 移至归档表           | 销毁后无法再操作 |

### 5. 错误场景处理

| 场景           | 错误信息                      | 处理建议         |
| ------------ | ------------------------- | ------------ |
| VM初始化时资源池无IP | "该IP未在资源池中配置"       | 管理员先导入IP到资源池 |
| 3rd查询已销毁配置   | "Configuration not found" | 配置已被销毁，查询归档表 |
| 3rd下载已销毁配置   | "Configuration not found" | 配置已被销毁，无法下载  |
| VM重复初始化      | -                         | 幂等操作，返回已有配置  |
| VM重复就绪       | -                         | 幂等操作，返回当前状态  |

***

## 接口详情

### VM API

#### GET /api/vm/config

获取VPN服务器配置，用于VM初始化WireGuard。

**请求**:

```http
GET /api/vm/config HTTP/1.1
Host: <server>:8000
Authorization: Bearer <vm_token>
```

**响应** (成功):

```json
{
  "success": true,
  "data": {
    "vm_ip": "10.11.12.3",
    "status": "init",
    "server": {
      "config_file": "[Interface]\n...",
      "public_key": "...",
      "listen_port": 2588
    }
  }
}
```

**错误响应**:

- `401`: Invalid VM token
- `400`: 该IP未在资源池中配置

**幂等性**: 是，重复调用返回相同配置

***

#### POST /api/vm/ready

报告VM已启动WireGuard。

**请求**:

```http
POST /api/vm/ready HTTP/1.1
Host: <server>:8000
Authorization: Bearer <vm_token>
```

**响应** (成功):

```json
{
  "success": true,
  "message": "VM 10.11.12.3 marked as started",
  "data": {
    "vm_ip": "10.11.12.3",
    "status": "started",
    "started_at": "2026-04-20T10:00:00"
  }
}
```

**幂等性**: 是，已启动状态重复调用不报错

***

### 3rd API (第三方应用)

#### GET /api/3rd/configs/{vm_ip}/info

获取VM的客户端配置概况信息。

**请求**:

```http
GET /api/3rd/configs/10.11.12.3/info HTTP/1.1
Host: <server>:8000
Authorization: Bearer <third_party_token>
```

**响应** (成功):

```json
{
  "success": true,
  "data": {
    "vm_ip": "10.11.12.3",
    "status": "started",
    "server_public_key": "...",
    "clients": [
      {
        "name": "wg1",
        "vpn_ip": "10.12.3.1",
        "private_key_masked": "SGg5****C08=",
        "public_key": "..."
      }
    ]
  }
}
```

**错误响应**:

- `401`: Invalid third-party token
- `404`: Configuration not found
- `400`: Configuration is not started (状态非started)

***

#### GET /api/3rd/configs/{vm_ip}/download

下载所有客户端配置文件。

**请求**:

```http
GET /api/3rd/configs/10.11.12.3/download HTTP/1.1
Host: <server>:8000
Authorization: Bearer <third_party_token>
```

**响应**: WireGuard配置文件 (`wg.conf`)，包含所有客户端配置

**错误响应**:

- `401`: Invalid third-party token
- `404`: Configuration not found
- `400`: Configuration is not started

***

#### POST /api/3rd/configs/{vm_ip}/destroy

销毁VM配置（移至归档表）。

**请求**:

```http
POST /api/3rd/configs/10.11.12.3/destroy HTTP/1.1
Host: <server>:8000
Authorization: Bearer <third_party_token>
```

**响应** (成功):

```json
{
  "success": true,
  "message": "Configuration for 10.11.12.3 has been destroyed",
  "data": {
    "vm_ip": "10.11.12.3",
    "deleted_at": "2026-04-20T12:00:00"
  }
}
```

**错误响应**:

- `401`: Invalid third-party token
- `404`: Configuration not found

**注意**: 销毁后配置移至归档表，无法再查询或下载

***

### Auth API

#### GET /api/auth/public-key

获取RSA公钥用于密码加密。

**响应**:

```json
{
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
}
```

***

#### POST /api/auth/login/encrypted

使用RSA加密密码登录。

**请求**:

```http
POST /api/auth/login/encrypted HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=admin&encrypted_password=<rsa_encrypted>
```

**响应**:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

***

### Admin API

#### 公网IP管理

| 方法     | 路径                                   | 说明     | 权限    |
| ------ | ------------------------------------ | ------ | ----- |
| GET    | `/api/admin/public-ips`              | 列出公网IP | 所有用户  |
| POST   | `/api/admin/public-ips`              | 导入公网IP | Admin |
| PUT    | `/api/admin/public-ips/{id}/default` | 设为默认   | Admin |
| DELETE | `/api/admin/public-ips/{id}`         | 删除公网IP | Admin |

#### 端口范围管理

| 方法   | 路径                      | 说明     | 权限    |
| ---- | ----------------------- | ------ | ----- |
| GET  | `/api/admin/port-range` | 获取端口范围 | 所有用户  |
| POST | `/api/admin/port-range` | 设置端口范围 | Admin |

#### 资源池管理

| 方法     | 路径                                        | 说明     | 权限    |
| ------ | ----------------------------------------- | ------ | ----- |
| GET    | `/api/admin/resource-pool`                | 列出资源池  | 所有用户  |
| POST   | `/api/admin/resource-pool/import`         | 导入IP   | Admin |
| DELETE | `/api/admin/resource-pool/{id}`           | 删除映射   | Admin |
| POST   | `/api/admin/resource-pool/batch-delete`   | 批量删除   | Admin |
| GET    | `/api/admin/resource-pool/export`         | 导出CSV  | Admin |
| PUT    | `/api/admin/resource-pool/{id}/public-ip` | 更新公网IP | Admin |

#### VPN配置管理

| 方法  | 路径                                                  | 说明      | 权限    |
| --- | --------------------------------------------------- | ------- | ----- |
| GET | `/api/admin/configs`                                | 列出配置    | 所有用户  |
| GET | `/api/admin/configs/{vm_ip}`                        | 配置详情    | 所有用户  |
| GET | `/api/admin/configs/{vm_ip}/clients`                | 客户端配置   | 所有用户  |
| GET | `/api/admin/configs/{vm_ip}/download/server`        | 下载服务器配置 | Admin |
| GET | `/api/admin/configs/{vm_ip}/download/client/{name}` | 下载客户端配置 | Admin |
| GET | `/api/admin/configs/{vm_ip}/download/clients`       | 下载所有客户端 | Admin |
| GET | `/api/admin/configs/export`                         | 导出CSV   | Admin |

#### 归档管理

| 方法  | 路径                           | 说明    | 权限    |
| --- | ---------------------------- | ----- | ----- |
| GET | `/api/admin/archives`        | 列出归档  | 所有用户  |
| GET | `/api/admin/archives/export` | 导出CSV | Admin |

#### 日志管理

| 方法  | 路径                | 说明   | 权限   |
| --- | ----------------- | ---- | ---- |
| GET | `/api/admin/logs` | 列出日志 | 所有用户 |

***

## 安全说明

### 1. 传输加密

- **浏览器↔Frontend**: 密码使用RSA-OAEP加密传输
- **VM↔Backend**: 使用VM Token认证，IP从TCP层获取
- **3rd↔Backend**: 使用第三方应用Token认证

### 2. Token分离

| Token类型      | 用途           | 格式    | 配置项                |
| ------------ | ------------ | ----- | ------------------ |
| VM Token     | VM访问后端API    | 简单字符串 | `VM_TOKEN`         |
| 第三方应用Token  | 第三方应用访问后端API | 简单字符串 | `THIRD_PARTY_TOKEN` |
| JWT Token    | 浏览器管理员访问API  | JWT格式 | `ADMIN_JWT_SECRET` |

**重要**: 三种Token完全独立，不可互换使用！

### 3. IP验证

VM API直接从TCP层获取客户端IP，不信任任何HTTP header，防止IP伪造攻击。

### 4. 权限控制

| 角色    | 权限          |
| ----- | ----------- |
| admin | 所有操作        |
| user  | 查看数据、修改自己密码 |

***

## 配置说明

### 环境变量

| 变量                     | 说明              | 默认值               |
| ---------------------- | --------------- | ----------------- |
| SERVER_IP              | 服务器IP地址         | localhost         |
| FRONTEND_PORT          | 前端端口            | 80                |
| BACKEND_PORT           | 后端端口            | 8000              |
| DB_PASSWORD            | 数据库密码           | -                 |
| DEFAULT_ADMIN_USERNAME | 默认管理员用户名        | admin             |
| DEFAULT_ADMIN_PASSWORD | 默认管理员密码         | admin123          |
| VM_TOKEN               | VM访问Token       | vm_default_token  |
| THIRD_PARTY_TOKEN      | 第三方应用Token      | 3rd_default_token |
| ADMIN_JWT_SECRET       | JWT密钥           | -                 |
| ADMIN_JWT_EXPIRE_HOURS | JWT过期时间(小时)     | 24                |
| PUBLIC_IP              | WireGuard公网IP   | -                 |
| WIREGUARD_VPN_SUBNET   | VPN子网前缀         | 10                |
| WIREGUARD_SERVER_PORT  | WireGuard服务器端口  | 2588              |
| WIREGUARD_CLIENT_COUNT | 每VM客户端数量        | 6                 |
| WIREGUARD_KEEPALIVE    | Keepalive间隔(秒)  | 25                |
| LOG_RETENTION_DAYS     | 日志保留天数          | 90                |

### 端口配置

通过 `.env` 文件配置：

```bash
FRONTEND_PORT=80
BACKEND_PORT=8000
```

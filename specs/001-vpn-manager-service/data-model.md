# Data Model: WireGuard VPN Manager Service

**Date**: 2026-04-17
**Feature**: 001-vpn-manager-service

## Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────────┐
│   port_ranges   │     │   resource_pools    │
├─────────────────┤     ├─────────────────────┤
│ id (PK)         │     │ id (PK)             │
│ start_port      │     │ internal_ip (UK)    │
│ end_port        │     │ public_port (UK)    │
│ created_at      │     │ created_at          │
│ updated_at      │     │ updated_at          │
└─────────────────┘     │ deleted_at          │
                        └─────────────────────┘
                                 │
                                 │ 1:1 (by IP)
                                 ▼
┌─────────────────────┐     ┌─────────────────────┐
│    vpn_configs      │     │    vpn_archives     │
│    (主表)            │     │    (归档表)          │
├─────────────────────┤     ├─────────────────────┤
│ id (PK)             │     │ id (PK)             │
│ vm_ip (UK)          │────▶│ vm_ip               │
│ server_private_key  │     │ server_private_key  │
│ server_public_key   │     │ server_public_key   │
│ client_configs      │     │ client_configs      │
│ status              │     │ status              │
│ created_at          │     │ created_at          │
│ started_at          │     │ deleted_at          │
└─────────────────────┘     └─────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│       users         │     │  operation_logs     │
├─────────────────────┤     ├─────────────────────┤
│ id (PK)             │     │ id (PK)             │
│ username (UK)       │     │ request_time        │
│ password_hash       │     │ source_ip           │
│ role                │     │ request_path        │
│ created_at          │     │ request_method      │
└─────────────────────┘     │ request_params      │
                            │ response_status     │
                            │ response_time_ms    │
                            └─────────────────────┘
```

## Entity Definitions

### 1. PortRange (端口范围配置)

**用途**: 存储Root管理员配置的公网UDP端口范围

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 主键 |
| start_port | INTEGER | NOT NULL | 起始端口 |
| end_port | INTEGER | NOT NULL | 结束端口 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**约束**:
- `start_port < end_port`
- `start_port >= 1024` (非特权端口)
- `end_port <= 65535`

**业务规则**:
- 系统只允许存在一条端口范围记录
- 修改端口范围时需检查已分配端口是否在新范围内

---

### 2. ResourcePool (资源池映射)

**用途**: 存储内网IP与公网端口的映射关系

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 主键 |
| internal_ip | INET | NOT NULL, UNIQUE | 内网IP地址 |
| public_port | INTEGER | NOT NULL, UNIQUE | 分配的公网UDP端口 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |
| deleted_at | TIMESTAMP | | 删除时间（软删除） |

**索引**:
- `idx_resource_pools_ip` ON (internal_ip)
- `idx_resource_pools_port` ON (public_port)
- `idx_resource_pools_deleted` ON (deleted_at) WHERE deleted_at IS NULL

**业务规则**:
- 删除前需检查是否存在活跃配置（FR-008）
- 端口必须从端口范围内分配
- 端口分配时需确保不冲突

---

### 3. VpnConfig (VPN配置 - 主表)

**用途**: 存储状态1和状态2的VPN配置记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 主键 |
| vm_ip | INET | NOT NULL, UNIQUE | 虚拟机IP地址 |
| server_private_key | TEXT | NOT NULL | Server端私钥 |
| server_public_key | TEXT | NOT NULL | Server端公钥 |
| client_configs | JSONB | NOT NULL | 5个客户端配置 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'init' | 状态 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| started_at | TIMESTAMP | | 状态2转变时间 |

**client_configs JSON结构**:
```json
[
  {
    "name": "client1",
    "private_key": "...",
    "public_key": "...",
    "vpn_ip": "10.C.D.1",
    "config_file": "[Interface]..."
  },
  // ... 共5个客户端
]
```

**索引**:
- `idx_vpn_configs_ip` ON (vm_ip)
- `idx_vpn_configs_status` ON (status)

**状态枚举**:
- `init` (状态1): VM已请求配置，等待就绪上报
- `started` (状态2): VM已上报就绪

**业务规则**:
- 状态只能从init → started
- 状态1的配置支持多次就绪上报（幂等性）
- 销毁时移入归档表

---

### 4. VpnArchive (VPN配置 - 归档表)

**用途**: 存储状态3的VPN配置历史记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 主键 |
| vm_ip | INET | NOT NULL | 虚拟机IP地址 |
| server_private_key | TEXT | NOT NULL | Server端私钥 |
| server_public_key | TEXT | NOT NULL | Server端公钥 |
| client_configs | JSONB | NOT NULL | 5个客户端配置 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'deleted' | 状态 |
| created_at | TIMESTAMP | NOT NULL | 原始创建时间 |
| deleted_at | TIMESTAMP | DEFAULT NOW() | 删除时间 |

**索引**:
- `idx_vpn_archives_ip` ON (vm_ip)
- `idx_vpn_archives_deleted_at` ON (deleted_at)

**业务规则**:
- 从主表移入时保留所有原始数据
- 支持历史查询

---

### 5. User (用户)

**用途**: 存储管理前端用户信息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 主键 |
| username | VARCHAR(50) | NOT NULL, UNIQUE | 用户名 |
| password_hash | TEXT | NOT NULL | 密码哈希 |
| role | VARCHAR(20) | NOT NULL | 角色 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**角色枚举**:
- `root`: Root管理员，全权限
- `admin`: 普通管理员，受限权限

**业务规则**:
- 密码使用bcrypt加密存储
- Root管理员可以管理其他用户

---

### 6. OperationLog (操作日志)

**用途**: 记录所有API请求和响应

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 主键 |
| request_time | TIMESTAMP | DEFAULT NOW() | 请求时间 |
| source_ip | INET | NOT NULL | 来源IP |
| request_path | VARCHAR(255) | NOT NULL | 请求路径 |
| request_method | VARCHAR(10) | NOT NULL | 请求方法 |
| request_params | JSONB | | 请求参数 |
| response_status | INTEGER | NOT NULL | 响应状态码 |
| response_time_ms | INTEGER | NOT NULL | 响应时间（毫秒） |

**索引**:
- `idx_operation_logs_time` ON (request_time)
- `idx_operation_logs_ip` ON (source_ip)
- `idx_operation_logs_path` ON (request_path)

**业务规则**:
- 日志保留3个月
- 超过3个月的日志自动清理

---

## State Transitions

### VpnConfig状态流转

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌──────────┐  VM请求配置  ┌──────────┐  VM上报就绪  ┌──────────┐
│  不存在   │─────────────▶│   init   │─────────────▶│ started  │
└──────────┘              │  (状态1)  │              │ (状态2)  │
                          └──────────┘              └──────────┘
                                │                         │
                                │ 外部前端应用销毁          │ 外部前端应用销毁
                                │                         │
                                ▼                         ▼
                          ┌──────────────────────────────────┐
                          │           deleted                │
                          │          (状态3)                 │
                          │        移入归档表                 │
                          └──────────────────────────────────┘
```

### 状态转换规则

| 当前状态 | 触发事件 | 目标状态 | 动作 |
|----------|----------|----------|------|
| 不存在 | VM请求配置 | init | 生成配置，保存到主表 |
| init | VM上报就绪 | started | 更新状态，记录started_at |
| init | 外部前端应用销毁 | deleted | 移入归档表 |
| started | 外部前端应用销毁 | deleted | 移入归档表 |

---

## Index Strategy

### 高频查询场景

1. **VM请求配置**: `SELECT * FROM vpn_configs WHERE vm_ip = ?`
   - 索引: `idx_vpn_configs_ip`

2. **外部前端应用查询配置**: `SELECT * FROM vpn_configs WHERE vm_ip = ? AND status != 'deleted'`
   - 索引: `idx_vpn_configs_ip`

3. **管理前端查看配置列表**: `SELECT * FROM vpn_configs WHERE status = ? ORDER BY created_at DESC`
   - 索引: `idx_vpn_configs_status`

4. **日志查询**: `SELECT * FROM operation_logs WHERE request_time BETWEEN ? AND ?`
   - 索引: `idx_operation_logs_time`

5. **端口分配检查**: `SELECT public_port FROM resource_pools WHERE deleted_at IS NULL`
   - 索引: `idx_resource_pools_deleted`

---

## Migration Plan

### 初始化迁移

```sql
-- 1. 创建端口范围表
CREATE TABLE port_ranges (
    id SERIAL PRIMARY KEY,
    start_port INTEGER NOT NULL,
    end_port INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_port_range CHECK (start_port < end_port AND start_port >= 1024 AND end_port <= 65535)
);

-- 2. 创建资源池表
CREATE TABLE resource_pools (
    id SERIAL PRIMARY KEY,
    internal_ip INET NOT NULL,
    public_port INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    CONSTRAINT unique_internal_ip UNIQUE (internal_ip),
    CONSTRAINT unique_public_port UNIQUE (public_port)
);

CREATE INDEX idx_resource_pools_ip ON resource_pools (internal_ip);
CREATE INDEX idx_resource_pools_port ON resource_pools (public_port);

-- 3. 创建VPN配置主表
CREATE TABLE vpn_configs (
    id SERIAL PRIMARY KEY,
    vm_ip INET NOT NULL,
    server_private_key TEXT NOT NULL,
    server_public_key TEXT NOT NULL,
    client_configs JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'init',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    CONSTRAINT unique_vm_ip UNIQUE (vm_ip),
    CONSTRAINT valid_status CHECK (status IN ('init', 'started'))
);

CREATE INDEX idx_vpn_configs_ip ON vpn_configs (vm_ip);
CREATE INDEX idx_vpn_configs_status ON vpn_configs (status);

-- 4. 创建VPN配置归档表
CREATE TABLE vpn_archives (
    id SERIAL PRIMARY KEY,
    vm_ip INET NOT NULL,
    server_private_key TEXT NOT NULL,
    server_public_key TEXT NOT NULL,
    client_configs JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'deleted',
    created_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vpn_archives_ip ON vpn_archives (vm_ip);
CREATE INDEX idx_vpn_archives_deleted_at ON vpn_archives (deleted_at);

-- 5. 创建用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_username UNIQUE (username),
    CONSTRAINT valid_role CHECK (role IN ('root', 'admin'))
);

-- 6. 创建操作日志表
CREATE TABLE operation_logs (
    id SERIAL PRIMARY KEY,
    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_ip INET NOT NULL,
    request_path VARCHAR(255) NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    request_params JSONB,
    response_status INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL
);

CREATE INDEX idx_operation_logs_time ON operation_logs (request_time);
CREATE INDEX idx_operation_logs_ip ON operation_logs (source_ip);

-- 7. 插入默认Root用户 (密码: admin123)
INSERT INTO users (username, password_hash, role) 
VALUES ('root', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.Xqt8F.qAu', 'root');
```

### 日志清理定时任务

```sql
-- 每天执行一次，清理3个月前的日志
DELETE FROM operation_logs WHERE request_time < NOW() - INTERVAL '3 months';
```

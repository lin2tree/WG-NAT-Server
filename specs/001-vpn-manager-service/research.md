# Research: WireGuard VPN Manager Service

**Date**: 2026-04-17
**Feature**: 001-vpn-manager-service

## 1. WireGuard命令行工具集成

### Decision
使用Python的`subprocess`模块调用WireGuard的`wg`命令生成密钥对，配置文件使用Jinja2模板生成。

### Rationale
- WireGuard官方工具`wg`是生成密钥对的标准方式
- `subprocess`是Python调用外部命令的标准库，无需额外依赖
- Jinja2模板引擎灵活且易于维护配置文件格式

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 使用Python库（如wireguard-py） | 纯Python实现 | 社区库不成熟，可能有兼容性问题 | 拒绝 |
| 直接调用wg命令 | 官方工具，稳定可靠 | 需要安装WireGuard | 采用 |
| 使用Docker容器封装wg | 环境隔离 | 增加部署复杂度 | 拒绝 |

### Implementation Notes
```python
import subprocess

def generate_keypair() -> tuple[str, str]:
    private_key = subprocess.run(['wg', 'genkey'], capture_output=True, text=True).stdout.strip()
    public_key = subprocess.run(['wg', 'pubkey'], input=private_key, capture_output=True, text=True).stdout.strip()
    return private_key, public_key
```

### WireGuard配置文件模板

**Server端配置**:
```ini
[Interface]
PrivateKey = {{ private_key }}
Address = {{ vpn_ip }}/24
ListenPort = 2588
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = {{ client_public_key_1 }}
AllowedIPs = {{ client_vpn_ip_1 }}/32

# ... 更多客户端
```

**Client端配置**:
```ini
[Interface]
PrivateKey = {{ client_private_key }}
Address = {{ client_vpn_ip }}/24
DNS = 8.8.8.8

[Peer]
PublicKey = {{ server_public_key }}
Endpoint = {{ public_ip }}:{{ public_port }}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

---

## 2. FastAPI最佳实践

### Decision
采用FastAPI作为后端框架，使用依赖注入模式管理数据库会话和认证，使用中间件实现日志记录。

### Rationale
- FastAPI原生支持异步，性能优异
- 自动生成OpenAPI文档，符合宪法"文档优先"原则
- 依赖注入模式便于测试和模块化

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| FastAPI | 异步、自动文档、类型提示 | 相对较新 | 采用 |
| Flask | 成熟稳定 | 同步、无自动文档 | 拒绝 |
| Django | 功能全面 | 过于重量级 | 拒绝 |

### Project Structure
```
backend/
├── src/
│   ├── api/
│   │   ├── deps.py          # 依赖注入
│   │   ├── vm.py            # VM端API
│   │   ├── frontend_app.py  # 外部前端应用API
│   │   └── admin.py         # 管理前端API
│   ├── core/
│   │   ├── config.py        # 配置管理
│   │   ├── security.py      # Token验证
│   │   └── logging.py       # 日志中间件
│   └── main.py
```

### Key Patterns

**依赖注入**:
```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/config")
def get_config(db: Session = Depends(get_db), request: Request):
    source_ip = request.client.host
    # ...
```

**日志中间件**:
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    # 记录日志
    return response
```

---

## 3. PostgreSQL数据模型设计

### Decision
使用SQLAlchemy ORM，主表存储活跃配置，归档表存储已删除配置，使用索引优化查询性能。

### Rationale
- SQLAlchemy是Python最成熟的ORM
- 分表设计便于数据管理和查询性能
- 索引优化确保高并发场景下的性能

### Database Schema

**port_ranges表**:
```sql
CREATE TABLE port_ranges (
    id SERIAL PRIMARY KEY,
    start_port INTEGER NOT NULL,
    end_port INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_port_range CHECK (start_port < end_port)
);
```

**resource_pools表**:
```sql
CREATE TABLE resource_pools (
    id SERIAL PRIMARY KEY,
    internal_ip INET NOT NULL UNIQUE,
    public_port INTEGER NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_resource_pools_ip ON resource_pools (internal_ip);
CREATE INDEX idx_resource_pools_port ON resource_pools (public_port);
```

**vpn_configs表**:
```sql
CREATE TABLE vpn_configs (
    id SERIAL PRIMARY KEY,
    vm_ip INET NOT NULL UNIQUE,
    server_private_key TEXT NOT NULL,
    server_public_key TEXT NOT NULL,
    client_configs JSONB NOT NULL,  -- 存储5个客户端配置
    status VARCHAR(20) NOT NULL DEFAULT 'init',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('init', 'started'))
);

CREATE INDEX idx_vpn_configs_ip ON vpn_configs (vm_ip);
CREATE INDEX idx_vpn_configs_status ON vpn_configs (status);
```

**vpn_archives表**:
```sql
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
```

**users表**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('root', 'admin'))
);
```

**operation_logs表**:
```sql
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
```

### Partitioning Strategy
对于`operation_logs`表，考虑按月分区以便于日志清理：
```sql
-- 3个月后自动删除
DELETE FROM operation_logs WHERE request_time < NOW() - INTERVAL '3 months';
```

---

## 4. 前端框架选择

### Decision
使用Vue 3 + TypeScript + Element Plus作为管理前端技术栈。

### Rationale
- Vue 3组合式API便于代码组织
- TypeScript提供类型安全
- Element Plus是企业级UI组件库，适合管理后台

### Alternatives Considered
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| Vue 3 + Element Plus | 中文文档完善、企业级组件 | 相对React生态较小 | 采用 |
| React + Ant Design | 生态丰富、社区活跃 | 学习曲线较陡 | 拒绝 |
| 纯HTML/jQuery | 简单直接 | 不适合复杂交互 | 拒绝 |

### Frontend Structure
```
frontend/
├── src/
│   ├── views/
│   │   ├── LoginView.vue
│   │   ├── ResourcePoolView.vue
│   │   ├── VpnConfigView.vue
│   │   └── LogView.vue
│   ├── components/
│   │   ├── ConfigDetail.vue
│   │   ├── ConfigDownload.vue
│   │   └── HistoryModal.vue
│   ├── services/
│   │   └── api.ts
│   ├── stores/
│   │   └── auth.ts
│   └── router/
│       └── index.ts
```

---

## 5. Docker部署策略

### Decision
使用多阶段构建优化镜像大小，使用docker-compose编排开发环境。

### Rationale
- 多阶段构建减少最终镜像大小
- docker-compose便于本地开发和测试
- 健康检查确保服务可用性

### Dockerfile (Backend)
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src ./src
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: vpn_manager
      POSTGRES_USER: vpn_admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://vpn_admin:${DB_PASSWORD}@postgres:5432/vpn_manager
      VM_TOKEN: ${VM_TOKEN}
      ADMIN_TOKEN: ${ADMIN_TOKEN}
    depends_on:
      - postgres
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## Summary

| 研究项目 | 决策 | 关键技术 |
|----------|------|----------|
| WireGuard集成 | subprocess调用wg命令 | subprocess, Jinja2 |
| 后端框架 | FastAPI | FastAPI, SQLAlchemy, Pydantic |
| 数据库设计 | PostgreSQL + SQLAlchemy | 分表设计, 索引优化 |
| 前端框架 | Vue 3 + Element Plus | TypeScript, Pinia |
| 部署策略 | Docker多阶段构建 | docker-compose, 健康检查 |

所有研究项目已完成，可以进入Phase 1设计阶段。

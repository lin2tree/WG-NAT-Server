# Quick Start: WireGuard VPN Manager Service

**Date**: 2026-04-17
**Feature**: 001-vpn-manager-service

## 环境准备

### 系统要求

- **操作系统**: Linux (推荐 Ubuntu 22.04 或 CentOS 8+)
- **Python**: 3.11+
- **Node.js**: 18+ (前端开发)
- **PostgreSQL**: 15+
- **Docker**: 24+ (可选，用于容器化部署)
- **WireGuard**: 1.0+ (用于生成密钥对)

### 安装依赖

#### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-15 wireguard-tools docker.io docker-compose

# CentOS/RHEL
sudo dnf install -y python3.11 python3.11-pip \
    postgresql-server wireguard-tools docker docker-compose
```

#### 2. 安装Python依赖

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

#### 3. 安装前端依赖

```bash
cd frontend
npm install
```

---

## 本地开发

### 1. 配置数据库

```bash
# 创建数据库
sudo -u postgres psql -c "CREATE DATABASE vpn_manager;"
sudo -u postgres psql -c "CREATE USER vpn_admin WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vpn_manager TO vpn_admin;"

# 运行迁移
cd backend
source .venv/bin/activate
alembic upgrade head
```

### 2. 配置环境变量

创建 `backend/.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://vpn_admin:your_password@localhost:5432/vpn_manager

# 安全配置
VM_TOKEN=your_vm_token_here
ADMIN_JWT_SECRET=your_jwt_secret_here
ADMIN_JWT_EXPIRE_HOURS=24

# 日志配置
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=90

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

### 3. 启动后端服务

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档: http://localhost:8000/docs

### 4. 启动前端服务

```bash
cd frontend
npm run dev
```

访问管理前端: http://localhost:3000

---

## 测试运行

### 单元测试

```bash
cd backend
source .venv/bin/activate
pytest tests/unit -v
```

### 集成测试

```bash
cd backend
source .venv/bin/activate
pytest tests/integration -v
```

### 测试覆盖率

```bash
cd backend
source .venv/bin/activate
pytest --cov=src --cov-report=html
```

覆盖率报告: `backend/htmlcov/index.html`

---

## Docker部署

### 1. 构建镜像

```bash
# 构建后端镜像
docker build -t vpn-manager-backend:latest ./backend

# 构建前端镜像
docker build -t vpn-manager-frontend:latest ./frontend
```

### 2. 使用docker-compose

创建 `docker-compose.yml`:

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vpn_admin -d vpn_manager"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    image: vpn-manager-backend:latest
    environment:
      DATABASE_URL: postgresql://vpn_admin:${DB_PASSWORD}@postgres:5432/vpn_manager
      VM_TOKEN: ${VM_TOKEN}
      ADMIN_JWT_SECRET: ${ADMIN_JWT_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: vpn-manager-frontend:latest
    depends_on:
      - backend
    ports:
      - "80:80"

volumes:
  postgres_data:
```

### 3. 启动服务

```bash
# 创建环境变量文件
cat > .env << EOF
DB_PASSWORD=your_secure_password
VM_TOKEN=your_vm_token
ADMIN_JWT_SECRET=your_jwt_secret
EOF

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 初始化配置

### 1. 创建Root管理员

首次启动后，系统会自动创建默认Root用户：

- 用户名: `root`
- 密码: `admin123`

**重要**: 请在生产环境中立即修改默认密码！

### 2. 配置端口范围

```bash
curl -X POST http://localhost:8000/api/admin/port-range \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"start_port": 10000, "end_port": 20000}'
```

### 3. 导入IP段

```bash
curl -X POST http://localhost:8000/api/admin/resource-pool \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ip_list": ["192.168.1.100", "192.168.1.101", "192.168.1.102"]}'
```

### 4. 导出映射关系

```bash
curl -X GET http://localhost:8000/api/admin/resource-pool/export \
  -H "Authorization: Bearer <token>" \
  -o mappings.csv
```

将导出的映射关系交给网络工程师配置防火墙。

---

## VM初始化脚本

VM首次启动时执行的初始化脚本示例：

```bash
#!/bin/bash

# VPN Manager API地址
VPN_MANAGER_URL="http://192.168.0.1:8000"
VM_TOKEN="your_vm_token"

# 获取配置
RESPONSE=$(curl -s -X GET "${VPN_MANAGER_URL}/api/vm/config" \
  -H "X-VM-Token: ${VM_TOKEN}")

# 解析配置
PRIVATE_KEY=$(echo $RESPONSE | jq -r '.private_key')
LISTEN_PORT=$(echo $RESPONSE | jq -r '.listen_port')
# ... 其他配置解析

# 写入WireGuard配置文件
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = ${PRIVATE_KEY}
Address = $(echo $RESPONSE | jq -r '.vpn_ip')/24
ListenPort = ${LISTEN_PORT}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# ... Peers配置
EOF

# 启动WireGuard
wg-quick up wg0

# 上报就绪状态
curl -s -X POST "${VPN_MANAGER_URL}/api/vm/ready" \
  -H "X-VM-Token: ${VM_TOKEN}"
```

---

## 常见问题

### Q: 如何重置Root密码？

```bash
# 进入后端容器
docker-compose exec backend bash

# 使用Python重置密码
python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('new_password'))
"

# 更新数据库
psql -U vpn_admin -d vpn_manager -c "UPDATE users SET password_hash = '<new_hash>' WHERE username = 'root';"
```

### Q: 如何查看日志？

```bash
# 查看后端日志
docker-compose logs -f backend

# 查看API日志（通过管理前端）
# 访问 http://localhost/logs
```

### Q: 如何备份数据库？

```bash
# 备份
docker-compose exec postgres pg_dump -U vpn_admin vpn_manager > backup.sql

# 恢复
docker-compose exec -T postgres psql -U vpn_admin vpn_manager < backup.sql
```

---

## 下一步

1. 配置生产环境的HTTPS证书
2. 设置日志轮转和监控告警
3. 配置数据库定时备份
4. 编写VM初始化脚本并集成到云平台
5. 与外部前端应用对接API

详细API文档请参考: [contracts/openapi.yaml](./contracts/openapi.yaml)

# FCloudVPN - WireGuard VPN Manager Service

一个基于 FastAPI 和 Vue 3 构建的 WireGuard VPN 管理服务，用于管理云端虚拟机的 VPN 配置。

## 📖 项目简介

FCloudVPN 是一个完整的 VPN 配置管理解决方案，专为只有一个公网 IP 的云平台环境设计。它允许用户通过 VPN 连接到云端虚拟机，同时提供完整的管理界面供管理员进行配置和监控。

### 核心功能

- **VM 配置管理**: 自动为虚拟机生成 WireGuard VPN 配置
- **资源池管理**: 管理内部 IP 地址和公网端口映射
- **状态追踪**: 实时追踪 VPN 配置的生命周期状态
- **操作日志**: 完整的操作审计日志，保留 90 天
- **角色权限**: 支持 Root 管理员和普通管理员两种角色
- **配置下载**: 支持下载客户端配置文件

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户电脑                                 │
│                    (WireGuard Client)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ VPN 连接
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      云平台 (单公网 IP)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FCloudVPN 服务                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │   后端 API  │  │  管理前端   │  │  PostgreSQL │     │   │
│  │  │  (FastAPI)  │  │  (Vue 3)    │  │  Database   │     │   │
│  │  └──────┬──────┘  └─────────────┘  └──────┬──────┘     │   │
│  │         │                                  │             │   │
│  │         └──────────────────────────────────┘             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    虚拟机集群                             │   │
│  │    ┌──────────┐    ┌──────────┐    ┌──────────┐        │   │
│  │    │   VM 1   │    │   VM 2   │    │   VM 3   │        │   │
│  │    │(内部 IP) │    │(内部 IP) │    │(内部 IP) │        │   │
│  │    └──────────┘    └──────────┘    └──────────┘        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 工作流程

1. **初始化阶段**: 管理员在资源池中导入可用的内部 IP 地址
2. **配置请求**: 虚拟机启动时向服务请求 VPN 配置
3. **配置生成**: 服务自动生成 WireGuard 密钥对和配置
4. **就绪上报**: 虚拟机配置完成后上报就绪状态
5. **客户端获取**: 前端应用获取客户端配置供用户下载
6. **销毁清理**: 虚拟机销毁时，配置归档到历史记录

## 📋 环境要求

### 生产环境

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+ (或使用 Docker 容器)
- WireGuard Tools (用于生成密钥)

### 开发环境

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- WireGuard Tools

## 🚀 快速开始

### 使用 Docker Compose (推荐)

1. **克隆项目**

```bash
git clone <repository-url>
cd FCloud
```

2. **创建环境变量文件**

```bash
# 创建 .env 文件
cat > .env << EOF
DB_PASSWORD=your_secure_password
VM_TOKEN=your_vm_token
ADMIN_JWT_SECRET=your_jwt_secret_key
EOF
```

3. **启动服务**

```bash
docker-compose up -d
```

4. **访问服务**

- 管理前端: http://localhost
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

5. **初始化管理员账户**

```bash
# 进入后端容器
docker-compose exec backend bash

# 创建 Root 管理员
python -c "
from src.core.database import SessionLocal
from src.core.security import get_password_hash
from src.models.user import User, UserRole

db = SessionLocal()
user = User(
    username='root',
    password_hash=get_password_hash('your_password'),
    role=UserRole.ROOT.value
)
db.add(user)
db.commit()
print('Root user created successfully')
"
```

### 手动部署

#### 后端部署

1. **安装依赖**

```bash
cd backend
pip install -e ".[dev]"
```

2. **配置环境变量**

```bash
export DATABASE_URL="postgresql://vpn_admin:password@localhost:5432/vpn_manager"
export VM_TOKEN="your_vm_token"
export ADMIN_JWT_SECRET="your_jwt_secret"
export ADMIN_JWT_EXPIRE_HOURS=24
export LOG_LEVEL=INFO
export LOG_RETENTION_DAYS=90
```

3. **初始化数据库**

```bash
# 创建数据库
createdb -U postgres vpn_manager

# 运行迁移
alembic upgrade head
```

4. **启动服务**

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

#### 前端部署

1. **安装依赖**

```bash
cd frontend
npm install
```

2. **配置 API 地址**

```bash
# 编辑 .env.production
VITE_API_BASE_URL=http://your-api-server:8000
```

3. **构建生产版本**

```bash
npm run build
```

4. **部署静态文件**

将 `dist` 目录部署到 Nginx 或其他 Web 服务器

## ⚙️ 配置说明

### 后端配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | - |
| `VM_TOKEN` | 虚拟机认证令牌 | `vm_default_token` |
| `ADMIN_JWT_SECRET` | JWT 签名密钥 | `admin_jwt_secret` |
| `ADMIN_JWT_EXPIRE_HOURS` | JWT 过期时间(小时) | `24` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_RETENTION_DAYS` | 日志保留天数 | `90` |

### 前端配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8000` |

### 端口范围配置

首次使用时，Root 管理员需要配置公网端口范围：

```bash
curl -X POST "http://localhost:8000/api/admin/port-range?start_port=10000&end_port=20000" \
  -H "Authorization: Bearer <root_token>"
```

## 📚 API 文档

### 认证方式

#### 管理员认证 (JWT)

```http
Authorization: Bearer <access_token>
```

#### 虚拟机认证 (Token)

```http
X-VM-Token: <vm_token>
```

#### 前端应用认证 (Token)

```http
X-VM-Token: <vm_token>
```

### 主要 API 端点

#### 虚拟机 API

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/vm/config` | 获取/创建 VPN 配置 |
| POST | `/api/vm/ready` | 上报配置完成 |

#### 前端应用 API

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/frontend/configs/{vm_ip}` | 获取客户端配置 |
| DELETE | `/api/frontend/configs/{vm_ip}` | 销毁配置 |
| GET | `/api/frontend/configs/{vm_ip}/download/{client_id}` | 下载客户端配置文件 |

#### 管理员 API

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/admin/configs` | 列出所有配置 |
| GET | `/api/admin/configs/{vm_ip}` | 获取配置详情 |
| GET | `/api/admin/configs/{vm_ip}/download/server` | 下载服务端配置 |
| GET | `/api/admin/configs/{vm_ip}/download/client/{client_id}` | 下载客户端配置 |
| GET | `/api/admin/port-range` | 获取端口范围配置 |
| POST | `/api/admin/port-range` | 设置端口范围 (仅 Root) |
| GET | `/api/admin/resource-pool` | 列出资源池 |
| POST | `/api/admin/resource-pool/import` | 导入 IP 地址 (仅 Root) |
| DELETE | `/api/admin/resource-pool/{id}` | 删除映射 (仅 Root) |
| GET | `/api/admin/resource-pool/export` | 导出映射 CSV |
| GET | `/api/admin/logs` | 查询操作日志 |

#### 认证 API

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/auth/login` | 管理员登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 获取当前用户信息 |

完整 API 文档请访问: http://localhost:8000/docs

## 🧪 测试

### 运行单元测试

```bash
cd backend
pytest tests/unit/ -v
```

### 运行集成测试

```bash
cd backend
# 确保 PostgreSQL 正在运行
pytest tests/integration/ -v
```

### 运行测试覆盖率

```bash
cd backend
pytest --cov=src --cov-report=html
```

### 前端测试

```bash
cd frontend
npm run test
```

## 🔧 开发指南

### 项目结构

```
FCloud/
├── backend/
│   ├── src/
│   │   ├── api/              # API 路由
│   │   │   ├── admin.py      # 管理员 API
│   │   │   ├── auth.py       # 认证 API
│   │   │   ├── deps.py       # 依赖注入
│   │   │   ├── frontend_app.py # 前端应用 API
│   │   │   ├── health.py     # 健康检查
│   │   │   └── vm.py         # 虚拟机 API
│   │   ├── core/             # 核心模块
│   │   │   ├── config.py     # 配置管理
│   │   │   ├── database.py   # 数据库连接
│   │   │   └── security.py   # 安全工具
│   │   ├── models/           # 数据模型
│   │   │   ├── base.py       # 基础模型
│   │   │   ├── operation_log.py # 操作日志
│   │   │   ├── port_range.py # 端口范围
│   │   │   ├── resource_pool.py # 资源池
│   │   │   ├── user.py       # 用户
│   │   │   ├── vpn_archive.py # VPN 归档
│   │   │   └── vpn_config.py # VPN 配置
│   │   ├── services/         # 业务逻辑
│   │   │   ├── vpn_config_service.py
│   │   │   └── wireguard_service.py
│   │   └── main.py           # 应用入口
│   ├── tests/                # 测试文件
│   ├── pyproject.toml        # 项目配置
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # 组件
│   │   ├── router/           # 路由
│   │   ├── services/         # API 服务
│   │   ├── stores/           # 状态管理
│   │   ├── views/            # 页面
│   │   │   ├── LoginView.vue
│   │   │   ├── VpnConfigView.vue
│   │   │   ├── ResourcePoolView.vue
│   │   │   └── LogView.vue
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

### 代码规范

#### Python

```bash
# 格式化代码
ruff check . --fix

# 类型检查
mypy src
```

#### TypeScript/Vue

```bash
# 格式化代码
npm run lint
```

### Git 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

## 🐳 Docker 构建

### 构建后端镜像

```bash
cd backend
docker build -t fcloudvpn-backend:latest .
```

### 构建前端镜像

```bash
cd frontend
docker build -t fcloudvpn-frontend:latest .
```

### 构建所有镜像

```bash
docker-compose build
```

### 推送到镜像仓库

```bash
docker tag fcloudvpn-backend:latest your-registry/fcloudvpn-backend:latest
docker tag fcloudvpn-frontend:latest your-registry/fcloudvpn-frontend:latest
docker push your-registry/fcloudvpn-backend:latest
docker push your-registry/fcloudvpn-frontend:latest
```

## 🔒 安全建议

1. **修改默认密码**: 首次部署后立即修改所有默认密码
2. **使用 HTTPS**: 生产环境必须使用 HTTPS
3. **定期轮换密钥**: 定期轮换 JWT 密钥和 VM Token
4. **限制网络访问**: 仅开放必要的端口
5. **备份数据库**: 定期备份 PostgreSQL 数据
6. **监控日志**: 定期检查操作日志，发现异常行为

## 📊 监控与运维

### 健康检查

```bash
curl http://localhost:8000/health
```

### 查看日志

```bash
# Docker Compose 日志
docker-compose logs -f backend

# 容器内日志
docker-compose exec backend tail -f /app/logs/app.log
```

### 数据库备份

```bash
# 备份
docker-compose exec postgres pg_dump -U vpn_admin vpn_manager > backup.sql

# 恢复
docker-compose exec -T postgres psql -U vpn_admin vpn_manager < backup.sql
```

## ❓ 常见问题

### 1. 虚拟机无法连接到服务

**检查项**:
- 确认 VM Token 配置正确
- 检查网络连通性
- 查看后端日志

### 2. 管理员无法登录

**检查项**:
- 确认用户已创建
- 检查密码是否正确
- 查看 JWT 配置

### 3. 配置下载失败

**检查项**:
- 确认配置状态为 `started`
- 检查文件权限
- 查看浏览器控制台

### 4. 端口分配失败

**检查项**:
- 确认端口范围已配置
- 检查端口是否已被占用
- 查看资源池状态

## 📄 许可证

MIT License

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📞 联系方式

- 项目主页: https://github.com/your-org/fcloudvpn
- 问题反馈: https://github.com/your-org/fcloudvpn/issues
- 邮箱: support@fcloudvpn.com

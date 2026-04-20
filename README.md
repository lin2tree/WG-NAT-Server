# FCloud - WireGuard VPN 管理系统

## 项目简介

FCloud 是一个 WireGuard VPN 配置管理系统，支持VM自动初始化VPN、管理员Web界面配置、第三方应用集成。

## 架构

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

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置服务器IP、密码等
```

主要配置项：

| 变量                     | 说明              | 默认值               |
| ---------------------- | --------------- | ----------------- |
| SERVER_IP              | 服务器IP地址         | localhost         |
| DEFAULT_ADMIN_USERNAME | 默认管理员用户名        | admin             |
| DEFAULT_ADMIN_PASSWORD | 默认管理员密码         | admin123          |
| VM_TOKEN               | VM访问Token       | vm_default_token  |
| THIRD_PARTY_TOKEN      | 第三方应用Token      | 3rd_default_token |
| ADMIN_JWT_SECRET       | JWT密钥           | admin_jwt_secret  |
| PUBLIC_IP              | WireGuard公网IP   | -                 |

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 访问服务

- **管理界面**: http://<SERVER_IP>/
- **后端API**: http://<SERVER_IP>:8000/
- **健康检查**: http://<SERVER_IP>:8000/health

### 4. 默认账号

默认管理员账户由环境变量配置：

- 用户名: `DEFAULT_ADMIN_USERNAME` (默认: admin)
- 密码: `DEFAULT_ADMIN_PASSWORD` (默认: admin123)

**注意**: 首次部署后修改 `.env` 文件不会影响已创建的用户。

## 使用流程

### 管理员操作

1. **导入公网IP**: 管理界面 → 资源池 → 导入Pub IP
2. **设置端口范围**: 管理界面 → 资源池 → 设置端口范围
3. **导入VM IP**: 管理界面 → 资源池 → 导入VM IP
4. **查看配置**: 管理界面 → VPN配置 → 查看已初始化的配置

### VM操作

VM通过API自动初始化VPN：

```bash
# 1. 获取配置
curl -X GET "http://<SERVER>:8000/api/vm/config" \
  -H "Authorization: Bearer <VM_TOKEN>"

# 2. 应用配置到WireGuard
# ... (VM自行处理)

# 3. 报告就绪
curl -X POST "http://<SERVER>:8000/api/vm/ready" \
  -H "Authorization: Bearer <VM_TOKEN>"
```

### 第三方应用操作

```powershell
# 使用预置的第三方应用Token 访问API
$headers = @{ "Authorization" = "Bearer <THIRD_PARTY_TOKEN>" }

# 1. 查询配置概况
Invoke-RestMethod -Uri "http://<SERVER>:8000/api/3rd/configs/<VM_IP>/info" `
    -Headers $headers

# 2. 下载所有客户端配置
Invoke-RestMethod -Uri "http://<SERVER>:8000/api/3rd/configs/<VM_IP>/download" `
    -Headers $headers -OutFile "wg.conf"

# 3. 销毁配置
Invoke-RestMethod -Uri "http://<SERVER>:8000/api/3rd/configs/<VM_IP>/destroy" `
    -Method POST -Headers $headers
```

## 安全特性

### 1. 传输加密

- **浏览器登录**: 密码使用RSA-OAEP加密传输
- **API访问**: 使用JWT Token认证

### 2. Token分离

| Token类型     | 用途           | 格式    | 配置项                |
| ------------ | ------------ | ----- | ------------------ |
| VM Token     | VM访问后端API    | 简单字符串 | `VM_TOKEN`         |
| 第三方应用Token  | 第三方应用访问后端API | 简单字符串 | `THIRD_PARTY_TOKEN` |
| JWT Token    | 浏览器管理员访问API  | JWT格式 | `ADMIN_JWT_SECRET` |

**重要**: 三种Token不可互换使用！

### 3. IP验证

VM API直接从TCP层获取客户端IP，不信任任何HTTP header，防止IP伪造攻击。

### 4. 权限控制

| 角色    | 权限          |
| ----- | ----------- |
| admin | 所有操作        |
| user  | 查看数据、修改自己密码 |

## 目录结构

```
FCloud/
├── backend/                # 后端代码
│   ├── src/
│   │   ├── api/           # API路由
│   │   ├── core/          # 核心模块
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   └── tasks/         # 定时任务
│   ├── alembic/           # 数据库迁移
│   └── Dockerfile
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── components/   # 公共组件
│   │   ├── services/     # API服务
│   │   └── stores/       # 状态管理
│   └── Dockerfile
├── docs/                  # 文档
│   └── API.md            # API文档
├── docker-compose.yml
└── .env                   # 环境配置
```

## 配置说明

详见 [.env](/.env) 文件

## API文档

详见 [API.md](/docs/API.md)

## 开发

### 后端开发

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 许可证

MIT

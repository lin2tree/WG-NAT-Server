# FCloudVPN 部署与测试记录

> 记录人：Hermes AI  
> 记录时间：2026-04-19  
> 部署环境：Ubuntu

---

## 1. 环境信息

| 项目 | 值 |
|------|-----|
| 操作系统 | Ubuntu (Linux) |
| Docker | 28.2.2 |
| Docker Compose | 2.37.1 |
| Python | 3.11.15 |
| Node.js | 22.22.2 |
| WireGuard Tools | v1.0.20210914 |
| 局域网IP | 192.168.51.134 (有线), 192.168.200.10 (无线) |
| PostgreSQL | Docker 容器内 (15) |

---

## 2. 部署步骤

### 2.1 创建 .env 配置文件

- 复制 `.env.example` 为 `.env`，填入测试环境配置
- 配置值：
  - DB_PASSWORD=fcloud_test_db_2026
  - VM_TOKEN=fcloud_vm_token_test
  - ADMIN_JWT_SECRET=fcloud_jwt_secret_test_2026
  - ADMIN_JWT_EXPIRE_HOURS=24
  - PUBLIC_IP=202.102.34.85
  - LOG_LEVEL=INFO
  - LOG_RETENTION_DAYS=90

### 2.2 修复 Docker 环境源 IP 丢失问题

**问题：** VM API 通过 `request.client.host` 获取客户端源 IP，用于识别 VM 并匹配资源池。但在 Docker + nginx 反向代理架构下，`request.client.host` 返回的是 Docker 内部网关 IP（如 172.x.x.x），而非真实客户端 IP，导致 VM 识别完全失效。

**原因：** 请求链路为 `客户端 → nginx容器(80) → backend容器(8000)`，nginx 作为反向代理转发请求到后端时，对后端而言 TCP 连接的来源是 nginx 容器 IP。

**解决：** 
- nginx 已有配置（无需修改）：`nginx.conf` 第 18-19 行已透传 `X-Real-IP` 和 `X-Forwarded-For` header
- 修改后端代码：`backend/src/api/deps.py` 的 `verify_vm_request` 函数，将原来直接取 `request.client.host` 改为按优先级读取 header：

```python
# 修改前（第73行）：
source_ip = request.client.host if request.client else None

# 修改后：
# 优先从 nginx 透传的 header 获取真实客户端 IP
# X-Forwarded-For 格式: "client_ip, proxy1_ip, proxy2_ip"，取第一个
source_ip = (
    request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    or request.headers.get("x-real-ip")
    or (request.client.host if request.client else None)
)
```

**优先级逻辑：**
1. `X-Forwarded-For` 第一个值（最原始客户端 IP）
2. `X-Real-IP`（nginx 设置的直连客户端 IP）
3. `request.client.host`（fallback，开发环境直连时有用）

**影响范围：** 仅 `verify_vm_request` 函数，该函数被 VM API 的 `/api/vm/config` 和 `/api/vm/ready` 两个端点依赖。

### 2.3 Docker Compose 构建并启动服务

构建过程中遇到多个问题（详见第3节），逐个修复后最终成功启动三个容器：

- **postgres**: 端口 5432，健康检查通过
- **backend**: 端口 8000，健康检查通过，Alembic 迁移自动执行
- **frontend**: 端口 80，nginx 提供 Vue SPA 和 API 反代

额外修改的配置文件：
- `docker-compose.yml`: 添加 `PUBLIC_IP` 环境变量传递，DATABASE_URL 密码改为引用 `.env` 变量
- `backend/src/core/config.py`: 新增 `PUBLIC_IP` 字段
- `.env`: 新增 `PUBLIC_IP=202.102.34.85`

### 2.4 初始化管理员账户

项目缺少自动初始化 root 用户的机制，手动通过以下步骤创建：

1. 用 `htpasswd` 生成 bcrypt 密码哈希
2. 通过 `docker exec psql` 直接插入 `users` 表
3. 初始时因 bcrypt 版本不兼容（详见问题5），先用 `$2y$` 格式哈希导致登录 500 错误
4. 后改用 Python `bcrypt` 库生成兼容的 `$2b$` 格式哈希，通过 `UPDATE` 更新
5. 最终登录验证通过

管理员账户信息：
- 用户名：`root`
- 密码：`lin1234`
- 角色：`root`

### 2.5 配置端口范围与资源池

通过 API 完成：
- 端口范围设置为 20000-30000（`POST /api/admin/port-range?start_port=20000&end_port=30000`）
- 导入 6 个测试 IP 到资源池（`POST /api/admin/resource-pool/import`）
- 验证导出 CSV 正常（`GET /api/admin/resource-pool/export`，返回 text/csv）

### 2.6 前端功能自动化测试

编写 `test_frontend.py` 自动化测试脚本，基于前端功能文档逐项测试后端 API 和前端路由完整性。

**测试结果：58/66 通过（87.9%）**

8 项失败分类：
- **环境限制（4项）**：2.7/2.10/2.11/2.12 — VM provision 需从内网发起请求，当前无 VM，无配置数据可测试，API 本身返回正确
- **设计问题（1项）**：4.3 — 操作日志表为空，后端仅在 VM API 记录日志，admin API 无中间件记录
- **测试脚本误判（3项）**：6.x 路由路径搜索问题，前端代码实际正确（文档写 `/vpn-configs`，代码用 `/configs`）

---

## 3. 遇到的问题与解决方案

| # | 问题描述 | 影响 | 解决方案 | 状态 |
|---|---------|------|---------|------|
| 1 | Docker+nginx 反代后 `request.client.host` 返回容器内网 IP | VM 无法被正确识别，整个核心流程失效 | 优先读 X-Forwarded-For / X-Real-IP header | ✅ 已修复 |
| 2 | docker-compose.yml 的 `version: "3.8"` 触发废弃警告 | 仅警告，不影响功能 | 无需处理（Compose V2 忽略此字段） | ⚠️ 无碍 |
| 3 | `pyproject.toml` 声明 `readme = "README.md"` 但文件不存在 | 后端 `hatch env create` 构建失败 (OSError) | 删除 pyproject.toml 中的 `readme` 行 | ✅ 已修复 |
| 4 | hatch 找不到项目包目录（期望 `vpn_manager_backend`，实际在 `src/`） | 后端构建失败 (ValueError) | pyproject.toml 添加 `[tool.hatch.build.targets.wheel] packages = ["src"]` | ✅ 已修复 |
| 5 | 前端 `.ts` 文件使用 Python 风格三引号注释 `"""..."""` | `vue-tsc` 编译失败 (TS1005) | 替换为 JS 标准注释 `// ...` | ✅ 已修复 |
| 6 | `router/index.ts` 中 `from` 参数未使用 | `vue-tsc` 报 TS6133 错误 | 改为 `_from` 前缀表示有意忽略 | ✅ 已修复 |
| 7 | 前端 `npm ci` 需要 `package-lock.json` 但不存在 | 前端构建失败 | Dockerfile 改用 `npm install` | ✅ 已修复 |
| 8 | Dockerfile PATH 硬编码 hatch 环境路径 `backend`，实际为 `vpn-manager-backend/哈希/` | 后端容器启动失败 (uvicorn not found) | 用 `find` 动态定位 venv bin 目录并创建符号链接 | ✅ 已修复 |
| 9 | Dockerfile 未复制 alembic 迁移文件，数据库表未创建 | 后端启动正常但数据库为空 | 复制 alembic 目录 + CMD 中先执行 `alembic upgrade head` | ✅ 已修复 |
| 10 | `passlib 1.7.4` + `bcrypt 5.0.0` 不兼容（bcrypt 4.1+ 去掉了 truncate 参数） | 管理员登录 500 错误 | 容器内降级 bcrypt 到 4.0.1；pyproject.toml 添加 `bcrypt>=4.0.0,<4.1.0` 约束 | ✅ 已修复 |
| 11 | `vm.py` 引用 `settings.PUBLIC_IP` 但 config.py 未定义此字段 | 运行时 AttributeError | config.py 新增 `PUBLIC_IP` 字段 + docker-compose.yml 传递环境变量 | ✅ 已修复 |
| 12 | docker-compose.yml DATABASE_URL 密码硬编码为掩码 | 后端无法连接数据库（密码错误） | 改为引用 `${DB_PASSWORD}` 环境变量 | ✅ 已修复 |
| 13 | 前端登录请求发送 JSON 格式，后端 `OAuth2PasswordRequestForm` 只接受 form-urlencoded | 登录按钮点击无反应，后端返回 422 | `api.ts` 登录改用 `URLSearchParams` + form-urlencoded | ✅ 已修复 |
| 14 | 前端资源池导入 API 路径错误：`/admin/resource-pool` → 应为 `/admin/resource-pool/import` | 导入 IP 功能失效 | 修正 `resourcePoolApi.import` 路径 | ✅ 已修复 |
| 15 | 前端端口范围设置用 JSON body 发送，后端期望 query params | 端口设置请求 422 | 改用 `api.post(url, null, { params: {...} })` | ✅ 已修复 |
| 16 | VPN 配置下载路径不匹配：前端 `/configs/{ip}/download?type=server`，后端 `/configs/{ip}/download/server` | 配置下载 404 | 修正路径 + 添加 `responseType: 'blob'` | ✅ 已修复 |
| 17 | 资源池导出 CSV 缺少 `responseType: 'blob'` | 导出文件损坏 | 添加 `responseType: 'blob'` | ✅ 已修复 |

---

## 4. 功能测试记录

### 4.1 基础服务验证

| 测试项 | 方法 | 结果 |
|--------|------|------|
| 后端健康检查 | `curl localhost:8000/health` | ✅ `{"status":"healthy","version":"0.1.0"}` |
| 前端页面 | `curl localhost:80/` | ✅ 200，返回 Vue SPA HTML |
| nginx API 代理 | `curl localhost:80/api/...` | ✅ 代理到后端正常 |
| 管理员登录 | `POST /api/auth/login` | ✅ 返回 JWT token |
| 数据库迁移 | Alembic 自动执行 | ✅ 7 张表已创建 |

### 4.2 前端功能测试（自动化脚本 test_frontend.py）

基于 `前端功能.md` 文档逐项测试，共 66 项，58 通过（87.9%）。

**1. 登录功能（14/14 通过）**

| 测试项 | 结果 |
|--------|------|
| 登录页面可访问 | ✅ |
| 正确凭据登录返回 token | ✅ |
| token_type=bearer | ✅ |
| 返回 user 信息 + role | ✅ |
| 错误密码返回 401 | ✅ |
| JSON 格式登录返回 422（符合预期） | ✅ |
| /auth/me 返回当前用户 | ✅ |
| 未认证访问 /auth/me 返回 401 | ✅ |
| /auth/logout 正常 | ✅ |

**2. VPN 配置页面（8/12 通过，4项因无VM数据跳过）**

| 测试项 | 结果 |
|--------|------|
| 配置列表 API 正常 | ✅ |
| 按 IP 搜索、状态筛选 | ✅ |
| 分页查询 | ✅ |
| VM 注册 provision（需内网 VM） | ❌ 环境限制 |
| 配置详情/下载（需先有 VM 配置） | ❌ 环境限制 |

**3. 资源池管理（14/14 通过）**

| 测试项 | 结果 |
|--------|------|
| 端口范围读取/设置 | ✅ 20000-30000 |
| 资源池列表、分页 | ✅ 6 条数据 |
| IP 导入/删除 | ✅ |
| CSV 导出 | ✅ text/csv |
| 不存在 ID 删除返回 404 | ✅ |

**4. 操作日志（4/5 通过）**

| 测试项 | 结果 |
|--------|------|
| 日志列表 API 正常 | ✅ |
| 按时间/IP 筛选 | ✅ |
| 日志列表有数据 | ❌ 表为空（后端仅记录 VM API 请求） |

**5. 通用/一致性（8/8 通过）**

| 测试项 | 结果 |
|--------|------|
| 后端 /health、Swagger /docs | ✅ |
| 前端覆盖文档所有 API 端点 | ✅ |
| 登录使用 form-urlencoded | ✅ |

**6. 前端视图完整性（10/13 通过，3项测试脚本误判）**

4 个视图文件全部存在，路由定义完整。3 项"失败"是测试脚本搜索字符串问题（路由用相对路径 `path: 'resource-pool'` 而非 `/resource-pool`），非实际 bug。

---

## 5. 验收结论

### 5.1 当前状态

- 三容器运行正常（postgres/backend/frontend）
- 管理员登录正常（root/lin1234）
- 资源池管理、端口配置、CSV 导出功能完备
- VPN 配置相关功能 API 完备，但需有 VM 实际注册后才能端到端验证
- 操作日志中间件仅覆盖 VM API，admin API 请求未被记录

### 5.2 遗留问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| bcrypt 验证慢（登录约 5-30 秒） | 🟡 中 | 容器内已降级到 4.0.1 但未持久化到镜像；下次 `docker compose build backend` 需用 pyproject.toml 中 bcrypt>=4.0.0,<4.1.0 约束重建 |
| admin API 无操作日志记录 | 🟡 中 | 仅 VM API 有日志，建议添加中间件统一记录 |
| 文档与代码路由不一致 | ⚪ 低 | 文档写 `/vpn-configs`，代码用 `/configs`，功能不受影响 |
| VM provision 未端到端验证 | 🟡 中 | 需从内网 VM 发起请求才能完整测试核心流程 |

---

## 附：已修改的源码文件清单

| 文件 | 修改内容 |
|------|---------|
| `backend/src/api/deps.py` | `verify_vm_request` 优先读 X-Forwarded-For/X-Real-IP |
| `backend/src/core/config.py` | 新增 `PUBLIC_IP` 配置字段 |
| `backend/pyproject.toml` | 删除 readme、添加 hatch build targets、bcrypt 版本约束 |
| `backend/Dockerfile` | 复制 src 到 builder、复制 alembic、动态定位 venv、CMD 先跑迁移 |
| `frontend/src/router/index.ts` | Python 三引号→JS 注释、from→_from |
| `frontend/src/services/api.ts` | Python 三引号→JS 注释；登录改 form-urlencoded；资源池导入路径修正；端口范围改 params；下载路径修正 + blob；导出加 blob |
| `frontend/src/stores/auth.ts` | Python 三引号→JS 注释 |
| `frontend/Dockerfile` | `npm ci` → `npm install` |
| `docker-compose.yml` | DATABASE_URL 引用变量、添加 PUBLIC_IP |
| `.env` | 新增 PUBLIC_IP |

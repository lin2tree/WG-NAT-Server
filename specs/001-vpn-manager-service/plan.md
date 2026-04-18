# Implementation Plan: WireGuard VPN Manager Service

**Branch**: `001-vpn-manager-service` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-vpn-manager-service/spec.md`

## Summary

本系统用于管理云端局域网内虚拟机的WireGuard VPN配置。由于云平台只有一个公网地址，通过本系统控制新建虚拟机的对外VPN，使用户电脑能够与虚拟机建立VPN连接。

**核心功能**：
- 资源池管理：Root管理员配置端口范围、导入内网IP段
- VPN配置生成：VM首次启动时自动生成WireGuard Server和Client配置
- 状态管理：配置状态流转（init → started → deleted）
- 管理前端：Web界面供管理员查看配置、下载配置文件

## Technical Context

**Language/Version**: Python 3.11+ (推荐，便于快速开发和运维)
**Primary Dependencies**: FastAPI (API框架), SQLAlchemy (ORM), WireGuard (命令行工具)
**Storage**: PostgreSQL (关系型数据库)
**Testing**: pytest (单元测试), pytest-asyncio (异步测试), httpx (API测试)
**Target Platform**: Linux server (云环境内网部署)
**Project Type**: web-service (后端API + 管理前端)
**Performance Goals**: P95 < 200ms, 100并发VM配置请求, 99.9%可用性
**Constraints**: HTTPS加密, Token认证, IP验证, 日志保留3个月
**Scale/Scope**: 预计管理数百个VM配置, 5个管理员用户

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. 测试驱动开发 (TDD) | ✅ PASS | 所有API端点必须有单元测试和集成测试 |
| II. 代码审查 | ✅ PASS | 所有代码变更通过Pull Request审查 |
| III. 文档优先 | ✅ PASS | API文档使用OpenAPI 3.0规范，自动生成 |
| IV. 安全合规 | ✅ PASS | HTTPS加密、Token认证、IP验证、敏感数据加密 |
| V. 效率与完备平衡 | ✅ PASS | 优先保证功能正确性，关键路径性能监控 |

**Gate Status**: ✅ PASSED - 可以进入Phase 0研究阶段

## Project Structure

### Documentation (this feature)

```text
specs/001-vpn-manager-service/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/          # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── port_range.py
│   │   ├── resource_pool.py
│   │   ├── vpn_config.py
│   │   ├── vpn_archive.py
│   │   ├── user.py
│   │   └── operation_log.py
│   ├── services/        # Business logic
│   │   ├── __init__.py
│   │   ├── resource_pool_service.py
│   │   ├── vpn_config_service.py
│   │   ├── wireguard_service.py
│   │   └── log_service.py
│   ├── api/             # FastAPI routes
│   │   ├── __init__.py
│   │   ├── vm.py        # VM端API
│   │   ├── frontend_app.py  # 外部前端应用API
│   │   ├── admin.py     # 管理前端API
│   │   └── auth.py      # 认证API
│   ├── core/            # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py    # Configuration
│   │   ├── security.py  # Token validation
│   │   └── logging.py   # Logging middleware
│   └── main.py          # FastAPI application entry
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── conftest.py      # Pytest fixtures
├── alembic/             # Database migrations
├── pyproject.toml       # Project dependencies
└── Dockerfile

frontend/
├── src/
│   ├── components/      # Vue/React components
│   ├── pages/           # Page components
│   ├── services/        # API client services
│   └── main.ts          # Frontend entry
├── tests/
├── package.json
└── Dockerfile

docker-compose.yml       # Development environment
```

**Structure Decision**: 采用Web应用结构（Option 2），分离后端API和管理前端。后端使用Python FastAPI，前端使用Vue.js或React。

## Complexity Tracking

> 无宪法违规，无需记录

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Phase 0: Research Tasks

### 待研究项目

1. **WireGuard命令行工具集成**
   - 如何在Python中调用wg命令生成密钥对
   - 配置文件格式和模板
   - 最佳实践

2. **FastAPI最佳实践**
   - 依赖注入模式
   - 中间件实现（日志记录、认证）
   - OpenAPI文档生成

3. **PostgreSQL数据模型设计**
   - 主表与归档表的分区策略
   - 索引优化
   - 并发控制

4. **前端框架选择**
   - Vue.js vs React
   - UI组件库选择
   - 构建工具

5. **Docker部署策略**
   - 多阶段构建
   - 环境变量管理
   - 健康检查

## Phase 1: Design Artifacts

### 待生成文档

1. **data-model.md** - 数据模型设计
   - 实体定义
   - 关系图
   - 索引策略
   - 迁移计划

2. **contracts/** - API契约
   - openapi.yaml - OpenAPI 3.0规范
   - VM端API契约
   - 外部前端应用API契约
   - 管理前端API契约

3. **quickstart.md** - 快速启动指南
   - 环境准备
   - 本地开发
   - 测试运行
   - 部署流程

## Next Steps

1. 执行Phase 0研究，生成 `research.md`
2. 执行Phase 1设计，生成 `data-model.md`, `contracts/`, `quickstart.md`
3. 更新agent上下文
4. 运行 `/speckit.tasks` 生成任务列表

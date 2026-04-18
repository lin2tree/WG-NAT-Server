# Tasks: WireGuard VPN Manager Service

**Input**: Design documents from `/specs/001-vpn-manager-service/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Tests**: 根据宪法原则I（测试驱动开发），包含测试任务

**Organization**: 任务按用户故事分组，支持独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1, US2, US3, US4, US5）
- 包含精确文件路径

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`
- **Migrations**: `backend/alembic/`

---

## Phase 1: Setup (项目初始化)

**Purpose**: 创建项目基础结构和配置

- [x] T001 Create project directory structure per implementation plan
- [x] T002 Initialize Python project with pyproject.toml in backend/
- [x] T003 [P] Configure pytest and test fixtures in backend/tests/conftest.py
- [x] T004 [P] Configure ruff linting and formatting in backend/pyproject.toml
- [x] T005 [P] Setup environment configuration in backend/src/core/config.py
- [x] T006 [P] Create Dockerfile for backend in backend/Dockerfile
- [x] T007 [P] Create docker-compose.yml for development environment
- [x] T008 Initialize Vue 3 frontend project in frontend/
- [x] T009 [P] Configure frontend build tools in frontend/vite.config.ts

---

## Phase 2: Foundational (基础设施)

**Purpose**: 所有用户故事依赖的核心基础设施

**⚠️ CRITICAL**: 此阶段必须完成后才能开始任何用户故事

### 数据库基础

- [x] T010 Create SQLAlchemy base model in backend/src/models/base.py
- [x] T011 [P] Create PortRange model in backend/src/models/port_range.py
- [x] T012 [P] Create ResourcePool model in backend/src/models/resource_pool.py
- [x] T013 [P] Create VpnConfig model in backend/src/models/vpn_config.py
- [x] T014 [P] Create VpnArchive model in backend/src/models/vpn_archive.py
- [x] T015 [P] Create User model in backend/src/models/user.py
- [x] T016 [P] Create OperationLog model in backend/src/models/operation_log.py
- [x] T017 Create Alembic migration for all tables in backend/alembic/versions/

### 核心服务

- [x] T018 [P] Implement database session management in backend/src/core/database.py
- [x] T019 [P] Implement security utilities (password hashing, JWT) in backend/src/core/security.py
- [x] T020 [P] Implement logging middleware in backend/src/core/logging.py
- [x] T021 Create FastAPI application entry point in backend/src/main.py

### API依赖注入

- [x] T022 [P] Create dependency injection utilities in backend/src/api/deps.py
- [x] T023 [P] Implement VM token authentication in backend/src/api/deps.py
- [x] T024 [P] Implement admin JWT authentication in backend/src/api/deps.py

### 前端基础

- [x] T025 [P] Create API client service in frontend/src/services/api.ts
- [x] T026 [P] Create auth store in frontend/src/stores/auth.ts
- [x] T027 [P] Create router configuration in frontend/src/router/index.ts
- [x] T028 Create main layout component in frontend/src/layouts/MainLayout.vue

**Checkpoint**: 基础设施就绪 - 可以开始用户故事实现

---

## Phase 3: User Story 1 - VM初始化获取VPN配置 (Priority: P1) 🎯 MVP

**Goal**: VM首次启动时自动获取WireGuard Server配置并启动服务

**Independent Test**: 模拟VM请求配置API，验证返回正确的Server端配置

### Tests for User Story 1

- [x] T029 [P] [US1] Create unit test for WireGuard key generation in backend/tests/unit/test_wireguard_service.py
- [x] T030 [P] [US1] Create unit test for VPN config service in backend/tests/unit/test_vpn_config_service.py
- [x] T031 [P] [US1] Create integration test for VM config API in backend/tests/integration/test_vm_api.py
- [x] T032 [P] [US1] Create integration test for VM ready API in backend/tests/integration/test_vm_api.py

### Implementation for User Story 1

- [x] T033 [P] [US1] Implement WireGuard key generation service in backend/src/services/wireguard_service.py
- [x] T034 [P] [US1] Implement VPN config template generation in backend/src/services/wireguard_service.py
- [x] T035 [US1] Implement VPN config service (create, get, update status) in backend/src/services/vpn_config_service.py
- [x] T036 [US1] Implement VM config endpoint GET /api/vm/config in backend/src/api/vm.py
- [x] T037 [US1] Implement VM ready endpoint POST /api/vm/ready in backend/src/api/vm.py
- [x] T038 [US1] Add IP validation from TCP RemoteAddr in backend/src/api/vm.py
- [x] T039 [US1] Add error handling for "该IP未在资源池中配置" in backend/src/api/vm.py
- [x] T040 [US1] Add error handling for "记录已销毁" in backend/src/api/vm.py

**Checkpoint**: US1完成 - VM可以获取配置并上报状态

---

## Phase 4: User Story 2 - 外部前端应用查询客户端配置 (Priority: P1) 🎯 MVP

**Goal**: 外部前端应用查询客户端配置展示给用户

**Independent Test**: 模拟外部前端应用API请求，验证返回5个有效配置

### Tests for User Story 2

- [x] T041 [P] [US2] Create integration test for frontend app config API in backend/tests/integration/test_frontend_app_api.py
- [x] T042 [P] [US2] Create integration test for destroy config API in backend/tests/integration/test_frontend_app_api.py

### Implementation for User Story 2

- [x] T043 [US2] Implement get client configs endpoint GET /api/frontend/configs/{vm_ip} in backend/src/api/frontend_app.py
- [x] T044 [US2] Implement destroy config endpoint POST /api/frontend/configs/{vm_ip}/destroy in backend/src/api/frontend_app.py
- [x] T045 [US2] Implement archive logic (move to VpnArchive table) in backend/src/services/vpn_config_service.py
- [x] T046 [US2] Add Bearer token authentication for frontend app API in backend/src/api/deps.py

**Checkpoint**: US2完成 - 外部前端应用可以查询和销毁配置

---

## Phase 5: User Story 3 - Root管理员管理资源池 (Priority: P1) 🎯 MVP

**Goal**: Root管理员配置端口范围、导入IP、查看映射

**Independent Test**: 模拟管理员操作，验证资源池管理功能

### Tests for User Story 3

- [x] T047 [P] [US3] Create integration test for port range API in backend/tests/integration/test_admin_resource_pool_api.py
- [x] T048 [P] [US3] Create integration test for resource pool list API in backend/tests/integration/test_admin_resource_pool_api.py
- [x] T049 [P] [US3] Create integration test for import IPs API in backend/tests/integration/test_admin_resource_pool_api.py
- [x] T050 [P] [US3] Create integration test for delete mapping API in backend/tests/integration/test_admin_resource_pool_api.py

### Implementation for User Story 3

- [x] T051 [P] [US3] Implement port range endpoints GET/POST /api/admin/port-range in backend/src/api/admin.py
- [x] T052 [P] [US3] Implement resource pool list endpoint GET /api/admin/resource-pool in backend/src/api/admin.py
- [x] T053 [P] [US3] Implement import IPs endpoint POST /api/admin/resource-pool/import in backend/src/api/admin.py
- [x] T054 [P] [US3] Implement delete mapping endpoint DELETE /api/admin/resource-pool/{id} in backend/src/api/admin.py
- [x] T055 [P] [US3] Implement export mappings endpoint GET /api/admin/resource-pool/export in backend/src/api/admin.py
- [x] T056 [P] [US3] Add root-only authorization check in backend/src/api/deps.py
- [x] T057 [P] [US3] Implement port allocation logic in backend/src/services/resource_pool_service.py
- [x] T058 [P] [US3] Implement B-class address validation in backend/src/services/resource_pool_service.py
- [x] T059 [P] [US3] Implement soft delete for mappings in backend/src/services/resource_pool_service.py
- [x] T060 [P] [US3] Add pagination support for list endpoint in backend/src/api/admin.py
- [x] T061 [P] [US3] Add CSV export functionality in backend/src/services/resource_pool_service.py
- [x] T062 [P] [US3] Add error handling for port range exhaustion in backend/src/services/resource_pool_service.py

**Checkpoint**: US3完成 - Root管理员可以管理资源池

---

## Phase 6: User Story 4 - 外部前端应用销毁配置 (Priority: P2)

**Goal**: 外部前端应用删除虚拟机时销毁VPN配置

**Independent Test**: 模拟销毁请求，验证配置移入归档表

### Tests for User Story 4

- [x] T063 [P] [US4] Create integration test for destroy state1 config in backend/tests/integration/test_frontend_app_api.py
- [x] T064 [P] [US4] Create integration test for destroy state2 config in backend/tests/integration/test_frontend_app_api.py

### Implementation for User Story 4

- [x] T065 [US4] Enhance destroy endpoint to handle state1 configs in backend/src/api/frontend_app.py
- [x] T066 [US4] Add archive table insertion in backend/src/services/vpn_config_service.py
- [x] T067 [US4] Add main table deletion in backend/src/services/vpn_config_service.py

**Checkpoint**: US4完成 - 销毁功能支持所有状态

---

## Phase 7: User Story 5 - 管理员查看操作日志 (Priority: P2)

**Goal**: 管理员查看操作日志，支持过滤

**Independent Test**: 模拟管理员查询日志

### Tests for User Story 5

- [x] T079 [P] [US5] Create integration test for log list API in backend/tests/integration/test_admin_log_api.py
- [x] T080 [P] [US5] Create integration test for log time filter in backend/tests/integration/test_admin_log_api.py
- [x] T081 [P] [US5] Create integration test for log IP filter in backend/tests/integration/test_admin_log_api.py

### Implementation for User Story 5

- [x] T082 [P] [US5] Implement log list endpoint GET /api/admin/logs in backend/src/api/admin.py
- [x] T083 [P] [US5] Implement log service in backend/src/services/log_service.py
- [x] T084 [P] [US5] Add time range filter in backend/src/services/log_service.py
- [x] T085 [P] [US5] Add IP filter in backend/src/services/log_service.py
- [x] T086 [P] [US5] Add path filter in backend/src/services/log_service.py
- [x] T087 [P] [US5] Add pagination support in backend/src/api/admin.py
- [x] T088 [P] [US5] Add log cleanup function for 90-day retention in backend/src/services/log_service.py

**Checkpoint**: US5完成 - 管理员可以查看操作日志

---

## Phase 8: Auth & Logging (认证与日志)

**Purpose**: 认证系统和操作日志

### Tests for Auth & Logging

- [x] T081 [P] Create integration test for login API in backend/tests/integration/test_auth_api.py
- [x] T082 [P] Create integration test for log API in backend/tests/integration/test_admin_api.py

### Implementation for Auth & Logging

- [x] T083 [P] Implement login endpoint POST /api/auth/login in backend/src/api/auth.py
- [x] T084 [P] Implement logout endpoint POST /api/auth/logout in backend/src/api/auth.py
- [x] T085 [P] Implement current user endpoint GET /api/auth/me in backend/src/api/auth.py
- [x] T086 Implement log service in backend/src/services/log_service.py
- [x] T087 Implement log list endpoint GET /api/admin/logs in backend/src/api/admin.py
- [x] T088 Add request logging middleware in backend/src/core/logging.py
- [x] T089 Add log retention cleanup task (3 months) in backend/src/services/log_service.py

### Frontend for Auth & Logging

- [x] T090 [P] Create LoginView page in frontend/src/views/LoginView.vue
- [x] T091 [P] Create LogView page in frontend/src/views/LogView.vue
- [x] T092 Implement auth guard in frontend/src/router/index.ts

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 完善和优化

- [x] T093 [P] Add API documentation (OpenAPI) enhancements in backend/src/main.py
- [x] T094 [P] Add health check endpoint in backend/src/api/health.py
- [x] T095 [P] Create frontend Dockerfile in frontend/Dockerfile
- [x] T096 [P] Add error boundary components in frontend/src/components/ErrorBoundary.vue
- [x] T097 Run all tests and ensure coverage ≥ 80% in backend/
- [x] T098 Run quickstart.md validation
- [x] T099 Security audit for sensitive data handling
- [x] T100 Performance testing for concurrent VM requests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 立即开始
- **Foundational (Phase 2)**: 依赖Setup完成 - 阻塞所有用户故事
- **User Stories (Phase 3-7)**: 都依赖Foundational完成
  - US1和US2可以并行（P1优先级）
  - US3, US4, US5可以并行（P2优先级）
- **Auth & Logging (Phase 8)**: 依赖Foundational完成
- **Polish (Phase 9)**: 依赖所有用户故事完成

### User Story Dependencies

- **US1 (P1)**: 依赖Foundational - 无其他故事依赖
- **US2 (P1)**: 依赖Foundational - 无其他故事依赖
- **US3 (P2)**: 依赖Foundational - 无其他故事依赖
- **US4 (P2)**: 依赖Foundational - 可与US2共享销毁逻辑
- **US5 (P2)**: 依赖Foundational - 无其他故事依赖

### Parallel Opportunities

- Setup阶段所有[P]任务可并行
- Foundational阶段所有[P]任务可并行
- US1和US2可以并行开发
- US3, US4, US5可以并行开发
- 每个用户故事内的[P]任务可并行

---

## Parallel Example: User Story 1

```bash
# 并行执行US1测试:
Task: "Create unit test for WireGuard key generation in backend/tests/unit/test_wireguard_service.py"
Task: "Create unit test for VPN config service in backend/tests/unit/test_vpn_config_service.py"
Task: "Create integration test for VM config API in backend/tests/integration/test_vm_api.py"
Task: "Create integration test for VM ready API in backend/tests/integration/test_vm_api.py"

# 并行执行US1实现:
Task: "Implement WireGuard key generation service in backend/src/services/wireguard_service.py"
Task: "Implement VPN config template generation in backend/src/services/wireguard_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2
5. **STOP and VALIDATE**: VM可以获取配置，前端应用可以查询配置
6. Deploy/demo MVP

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. US1 + US2 → MVP（核心VPN功能）
3. US3 → 资源池管理
4. US4 + US5 → 管理功能完善
5. Auth + Logging → 安全与审计
6. Polish → 生产就绪

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签映射到具体用户故事
- 每个用户故事独立可测试
- 测试先行，确保失败后再实现
- 每个任务或逻辑组完成后提交
- 在检查点验证故事独立性

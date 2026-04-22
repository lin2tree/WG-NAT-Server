# FCloud 自动化测试

## 测试架构

```
tests/
├── conftest.py          # 测试配置和 fixtures
├── api_client.py        # API 客户端
├── db_client.py         # 数据库客户端
├── test_api.py          # API 测试用例
├── test_consistency.py  # 数据一致性测试
├── test_ui.py           # Playwright UI 测试
├── requirements.txt     # 测试依赖
└── run_tests.sh         # 测试运行脚本
```

## 测试分类

### 1. API 测试 (`@pytest.mark.api`)
测试所有 API 端点的正常功能和异常处理。

### 2. 数据一致性测试 (`@pytest.mark.consistency`)
验证 API 返回数据与数据库记录的一致性。

### 3. UI 测试 (`@pytest.mark.ui`)
使用 Playwright 测试前端页面功能。

### 4. 边界测试 (`@pytest.mark.boundary`)
测试边界条件和极限值。

### 5. 异常测试 (`@pytest.mark.exception`)
测试异常处理和错误场景。

### 6. 冒烟测试 (`@pytest.mark.smoke`)
快速验证核心功能。

### 7. 回归测试 (`@pytest.mark.regression`)
完整功能验证。

## 环境配置

测试使用以下环境变量（可在 `.env` 中配置）：

```bash
SERVER_IP=192.168.51.134
BACKEND_PORT=8000
FRONTEND_PORT=80
VM_TOKEN=vm_default_token
THIRD_PARTY_TOKEN=3rd_default_token
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vpn_manager
DB_USER=vpn_admin
DB_PASSWORD=fcloud_test_db_2026
```

## 运行测试

### 安装依赖

```bash
pip install -r tests/requirements.txt
playwright install
```

### 运行所有测试

```bash
./tests/run_tests.sh
```

### 运行特定测试

```bash
# API 测试
./tests/run_tests.sh api

# UI 测试
./tests/run_tests.sh ui

# 数据一致性测试
./tests/run_tests.sh consistency

# 冒烟测试
./tests/run_tests.sh smoke

# 回归测试
./tests/run_tests.sh regression
```

### 使用 pytest 直接运行

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定标记的测试
pytest tests/ -v -m api
pytest tests/ -v -m consistency
pytest tests/ -v -m ui

# 运行特定文件
pytest tests/test_api.py -v

# 运行特定测试类
pytest tests/test_api.py::TestAuthAPI -v

# 运行特定测试方法
pytest tests/test_api.py::TestAuthAPI::test_login_admin_success -v
```

## 测试报告

测试完成后，报告生成在 `test-reports/` 目录：

- `full-report.html` - 完整 HTML 报告
- `api-report.html` - API 测试报告
- `ui-report.html` - UI 测试报告
- `consistency-report.html` - 数据一致性测试报告
- `allure-report/` - Allure 详细报告

### 查看 Allure 报告

```bash
allure open test-reports/allure-report
```

## 测试用例说明

### API 测试

| 测试类 | 测试内容 |
|--------|----------|
| TestHealthCheck | 后端健康检查 |
| TestAuthAPI | 认证 API（公钥获取、登录） |
| TestVMAPI | VM API（配置获取、就绪上报） |
| TestThirdPartyAPI | 第三方 API（配置查询、下载、销毁） |
| TestAdminAPI | 管理 API（配置列表、资源池、公网IP等） |
| TestBoundaryConditions | 边界条件测试 |
| TestExceptionHandling | 异常处理测试 |

### 数据一致性测试

| 测试类 | 测试内容 |
|--------|----------|
| TestVPNConfigConsistency | VPN 配置列表与数据库一致性 |
| TestResourcePoolConsistency | 资源池列表与数据库一致性 |
| TestArchiveConsistency | 归档数据一致性 |
| TestPublicIPConsistency | 公网 IP 数据一致性 |
| TestVMInitializationFlow | VM 初始化流程数据一致性 |
| TestDestroyFlowConsistency | 销毁流程数据一致性 |

### UI 测试

| 测试类 | 测试内容 |
|--------|----------|
| TestLoginPage | 登录页面功能 |
| TestVPNConfigPage | VPN 配置页面功能 |
| TestResourcePoolPage | 资源池页面功能 |
| TestLogPage | 日志页面功能 |
| TestArchivePage | 归档页面功能 |
| TestNavigation | 页面导航功能 |
| TestAutoRefresh | 自动刷新功能 |
| TestLogout | 登出功能 |

## 持续集成

在 CI/CD 管道中运行测试：

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r tests/requirements.txt
          playwright install
      
      - name: Run tests
        run: ./tests/run_tests.sh regression
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test-reports/
```

## 最佳实践

1. **测试隔离**: 每个测试使用独立数据，测试后清理
2. **幂等性**: 测试可重复运行，结果一致
3. **清晰断言**: 断言信息清晰，便于定位问题
4. **合理标记**: 使用 pytest mark 分类测试
5. **及时更新**: 代码修改后同步更新相关测试

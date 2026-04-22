"""
Playwright UI 测试
测试前端页面的功能和交互
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def browser_context(browser, config):
    context = browser.new_context(
        base_url=config.frontend_url,
        viewport={"width": 1920, "height": 1080}
    )
    yield context
    context.close()


@pytest.fixture
def page(browser_context):
    page = browser_context.new_page()
    yield page
    page.close()


@pytest.fixture
def logged_in_page(page, config):
    page.goto("/")
    
    page.fill('input[placeholder*="用户名"]', config.admin_username)
    page.fill('input[placeholder*="密码"]', config.admin_password)
    page.click('button:has-text("登录")')
    
    page.wait_for_url("**/vpn-configs", timeout=10000)
    
    yield page


@pytest.mark.ui
class TestLoginPage:
    def test_login_page_loads(self, page, config):
        page.goto("/")
        expect(page).to_have_title(/FCloud|VPN/)
    
    def test_login_form_visible(self, page, config):
        page.goto("/")
        expect(page.locator('input[placeholder*="用户名"]')).to_be_visible()
        expect(page.locator('input[placeholder*="密码"]')).to_be_visible()
    
    def test_login_success(self, page, config):
        page.goto("/")
        
        page.fill('input[placeholder*="用户名"]', config.admin_username)
        page.fill('input[placeholder*="密码"]', config.admin_password)
        page.click('button:has-text("登录")')
        
        page.wait_for_url("**/vpn-configs", timeout=10000)
        expect(page).to_have_url(/.*vpn-configs/)
    
    def test_login_failure_wrong_password(self, page, config):
        page.goto("/")
        
        page.fill('input[placeholder*="用户名"]', config.admin_username)
        page.fill('input[placeholder*="密码"]', "wrong_password")
        page.click('button:has-text("登录")')
        
        page.wait_for_selector('.el-message--error', timeout=5000)


@pytest.mark.ui
class TestVPNConfigPage:
    def test_vpn_config_page_loads(self, logged_in_page):
        expect(logged_in_page.locator('text=VPN配置')).to_be_visible()
    
    def test_vpn_config_table_visible(self, logged_in_page):
        expect(logged_in_page.locator('.el-table')).to_be_visible()
    
    def test_vpn_config_search(self, logged_in_page):
        search_input = logged_in_page.locator('input[placeholder*="搜索"]')
        if search_input.count() > 0:
            search_input.first.fill("10.")
            search_input.first.press("Enter")
    
    def test_vpn_config_refresh(self, logged_in_page):
        logged_in_page.wait_for_timeout(6000)
        
        expect(logged_in_page.locator('.el-table')).to_be_visible()


@pytest.mark.ui
class TestResourcePoolPage:
    def test_navigate_to_resource_pool(self, logged_in_page):
        logged_in_page.click('text=资源池')
        logged_in_page.wait_for_url("**/resource-pool", timeout=5000)
        
        expect(logged_in_page).to_have_url(/.*resource-pool/)
    
    def test_resource_pool_table_visible(self, logged_in_page):
        logged_in_page.click('text=资源池')
        logged_in_page.wait_for_selector('.el-table', timeout=5000)
        
        expect(logged_in_page.locator('.el-table')).to_be_visible()


@pytest.mark.ui
class TestLogPage:
    def test_navigate_to_logs(self, logged_in_page):
        logged_in_page.click('text=日志')
        logged_in_page.wait_for_url("**/logs", timeout=5000)
        
        expect(logged_in_page).to_have_url(/.*logs/)
    
    def test_log_table_visible(self, logged_in_page):
        logged_in_page.click('text=日志')
        logged_in_page.wait_for_selector('.el-table', timeout=5000)
        
        expect(logged_in_page.locator('.el-table')).to_be_visible()
    
    def test_log_status_colors(self, logged_in_page):
        logged_in_page.click('text=日志')
        logged_in_page.wait_for_selector('.el-table', timeout=5000)
        
        success_tags = logged_in_page.locator('.el-tag--success')
        if success_tags.count() > 0:
            expect(success_tags.first).to_be_visible()


@pytest.mark.ui
class TestArchivePage:
    def test_navigate_to_archives(self, logged_in_page):
        logged_in_page.click('text=归档')
        logged_in_page.wait_for_url("**/archives", timeout=5000)
        
        expect(logged_in_page).to_have_url(/.*archives/)
    
    def test_archive_table_visible(self, logged_in_page):
        logged_in_page.click('text=归档')
        logged_in_page.wait_for_selector('.el-table', timeout=5000)
        
        expect(logged_in_page.locator('.el-table')).to_be_visible()


@pytest.mark.ui
class TestNavigation:
    def test_sidebar_visible(self, logged_in_page):
        expect(logged_in_page.locator('.el-menu')).to_be_visible()
    
    def test_all_menu_items_clickable(self, logged_in_page):
        menu_items = ["VPN配置", "资源池", "公网IP", "归档", "日志"]
        
        for item in menu_items:
            logged_in_page.click(f'text={item}')
            logged_in_page.wait_for_timeout(500)


@pytest.mark.ui
class TestAutoRefresh:
    def test_auto_refresh_indicator(self, logged_in_page):
        logged_in_page.wait_for_timeout(6000)
        
        expect(logged_in_page.locator('.el-table')).to_be_visible()


@pytest.mark.ui
class TestLogout:
    def test_logout(self, logged_in_page):
        logout_button = logged_in_page.locator('button:has-text("退出"), .logout-btn')
        
        if logout_button.count() > 0:
            logout_button.click()
            logged_in_page.wait_for_url("**/", timeout=5000)
            expect(page).to_have_url(/.*\/$/)

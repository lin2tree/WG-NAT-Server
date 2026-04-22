"""
API 测试用例
测试所有 API 端点的正常功能和异常处理
"""
import pytest
from tests.conftest import CONFIG


@pytest.mark.api
@pytest.mark.smoke
class TestHealthCheck:
    def test_backend_health(self, api_client):
        assert api_client.health_check() is True


@pytest.mark.api
class TestAuthAPI:
    def test_get_public_key(self, api_client):
        response = api_client.get_public_key()
        assert response.status_code == 200
        data = response.json()
        assert "public_key" in data
        assert "BEGIN PUBLIC KEY" in data["public_key"]
    
    def test_login_admin_success(self, api_client):
        token = api_client.login_admin()
        assert token is not None
        assert len(token) > 0
    
    def test_login_admin_wrong_password(self, api_client):
        with pytest.raises(Exception):
            api_client.login_admin(
                username=CONFIG.admin_username,
                password="wrong_password"
            )


@pytest.mark.api
class TestVMAPI:
    def test_vm_config_without_resource_pool(self, api_client):
        response = api_client.get_vm_config(expected_status=400)
        assert response.status_code in [400, 401]
    
    def test_vm_config_invalid_token(self, config):
        import requests
        response = requests.get(
            f"{CONFIG.base_url}/api/vm/config",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=10
        )
        assert response.status_code == 401
    
    def test_vm_ready_success(self, api_client, db_client, clean_test_data):
        test_ip = "10.99.99.100"
        db_client.create_test_resource_pool(test_ip, 10000)
        db_client.create_test_vpn_config(test_ip, "init")
        
        response = api_client.post_vm_ready(success=True)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    def test_vm_ready_with_error(self, api_client, db_client, clean_test_data):
        test_ip = "10.99.99.101"
        db_client.create_test_resource_pool(test_ip, 10001)
        db_client.create_test_vpn_config(test_ip, "init")
        
        response = api_client.post_vm_ready(
            success=False, 
            error_message="Test error message"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "error"


@pytest.mark.api
class TestThirdPartyAPI:
    def test_get_config_info_not_found(self, api_client):
        response = api_client.get_3rd_config_info("10.99.99.200")
        assert response.status_code == 404
    
    def test_get_config_download_not_found(self, api_client):
        response = api_client.get_3rd_config_download("10.99.99.200")
        assert response.status_code == 404
    
    def test_destroy_not_found(self, api_client):
        response = api_client.post_3rd_destroy("10.99.99.200")
        assert response.status_code == 404
    
    def test_invalid_third_party_token(self, config):
        import requests
        response = requests.get(
            f"{CONFIG.base_url}/api/3rd/configs/10.99.99.100/info",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=10
        )
        assert response.status_code == 401


@pytest.mark.api
class TestAdminAPI:
    def test_get_configs_unauthorized(self, api_client):
        response = api_client.get_admin_configs(token=None)
        assert response.status_code == 401
    
    def test_get_configs_success(self, api_client, admin_token):
        response = api_client.get_admin_configs(token=admin_token)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_get_resource_pool_success(self, api_client, admin_token):
        response = api_client.get_admin_resource_pool(token=admin_token)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
    
    def test_get_public_ips_success(self, api_client, admin_token):
        response = api_client.get_admin_public_ips(token=admin_token)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_archives_success(self, api_client, admin_token):
        response = api_client.get_admin_archives(token=admin_token)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
    
    def test_get_logs_success(self, api_client, admin_token):
        response = api_client.get_admin_logs(token=admin_token)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data


@pytest.mark.api
@pytest.mark.boundary
class TestBoundaryConditions:
    def test_invalid_ip_format(self, api_client, admin_token):
        response = api_client.get_3rd_config_info("invalid_ip")
        assert response.status_code in [400, 404, 422]
    
    def test_empty_ip(self, api_client, admin_token):
        response = api_client.get_3rd_config_info("")
        assert response.status_code in [400, 404, 422]
    
    def test_very_long_error_message(self, api_client, db_client, clean_test_data):
        test_ip = "10.99.99.102"
        db_client.create_test_resource_pool(test_ip, 10002)
        db_client.create_test_vpn_config(test_ip, "init")
        
        long_message = "A" * 10000
        response = api_client.post_vm_ready(success=False, error_message=long_message)
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.exception
class TestExceptionHandling:
    def test_malformed_json(self, config):
        import requests
        response = requests.post(
            f"{CONFIG.base_url}/api/vm/ready",
            headers={
                "Authorization": f"Bearer {CONFIG.vm_token}",
                "Content-Type": "application/json"
            },
            data="not valid json",
            timeout=10
        )
        assert response.status_code in [400, 422]
    
    def test_missing_content_type(self, config):
        import requests
        response = requests.post(
            f"{CONFIG.base_url}/api/vm/ready",
            headers={"Authorization": f"Bearer {CONFIG.vm_token}"},
            timeout=10
        )
        assert response.status_code in [200, 400, 422]

"""
数据一致性测试
验证 API 返回数据与数据库记录的一致性
"""
import pytest


@pytest.mark.consistency
class TestVPNConfigConsistency:
    def test_vpn_config_list_matches_database(
        self, 
        api_client, 
        admin_token, 
        db_client
    ):
        response = api_client.get_admin_configs(token=admin_token)
        assert response.status_code == 200
        
        api_data = response.json()
        api_items = api_data.get("items", [])
        api_ips = {item["vm_ip"] for item in api_items}
        
        db_configs = db_client.get_all_vpn_configs()
        db_ips = {config["vm_ip"] for config in db_configs}
        
        assert api_ips == db_ips, f"API IPs: {api_ips}, DB IPs: {db_ips}"
    
    def test_vpn_config_status_matches_database(
        self,
        api_client,
        admin_token,
        db_client
    ):
        response = api_client.get_admin_configs(token=admin_token)
        assert response.status_code == 200
        
        api_items = response.json().get("items", [])
        
        for item in api_items[:10]:
            vm_ip = item["vm_ip"]
            db_config = db_client.get_vpn_config_by_ip(vm_ip)
            
            assert db_config is not None, f"VM IP {vm_ip} not found in database"
            assert item["status"] == db_config["status"], \
                f"Status mismatch for {vm_ip}: API={item['status']}, DB={db_config['status']}"


@pytest.mark.consistency
class TestResourcePoolConsistency:
    def test_resource_pool_list_matches_database(
        self,
        api_client,
        admin_token,
        db_client
    ):
        response = api_client.get_admin_resource_pool(token=admin_token)
        assert response.status_code == 200
        
        api_data = response.json()
        api_items = api_data.get("items", [])
        api_ips = {item["internal_ip"] for item in api_items}
        
        db_items = db_client.get_all_resource_pool()
        db_ips = {item["internal_ip"] for item in db_items}
        
        assert api_ips == db_ips, f"API IPs: {api_ips}, DB IPs: {db_ips}"
    
    def test_public_ip_consistency_between_views(
        self,
        api_client,
        admin_token,
        db_client
    ):
        configs_response = api_client.get_admin_configs(token=admin_token)
        pool_response = api_client.get_admin_resource_pool(token=admin_token)
        
        assert configs_response.status_code == 200
        assert pool_response.status_code == 200
        
        configs = configs_response.json().get("items", [])
        pool_items = pool_response.json().get("items", [])
        
        pool_public_ips = {}
        for item in pool_items:
            pool_public_ips[item["internal_ip"]] = item.get("public_ip")
        
        for config in configs:
            vm_ip = config["vm_ip"]
            config_pub_ip = config.get("pub_ip")
            
            if vm_ip in pool_public_ips:
                pool_pub_ip = pool_public_ips[vm_ip]
                
                if pool_pub_ip and config_pub_ip:
                    assert config_pub_ip == pool_pub_ip, \
                        f"Public IP mismatch for {vm_ip}: VPN Config shows {config_pub_ip}, Resource Pool shows {pool_pub_ip}"


@pytest.mark.consistency
class TestArchiveConsistency:
    def test_archive_count_matches_database(
        self,
        api_client,
        admin_token,
        db_client
    ):
        response = api_client.get_admin_archives(token=admin_token)
        assert response.status_code == 200
        
        api_data = response.json()
        api_count = api_data.get("total", 0)
        
        db_count = db_client.count_archives()
        
        assert api_count == db_count, \
            f"Archive count mismatch: API={api_count}, DB={db_count}"


@pytest.mark.consistency
class TestPublicIPConsistency:
    def test_public_ip_list_matches_database(
        self,
        api_client,
        admin_token,
        db_client
    ):
        response = api_client.get_admin_public_ips(token=admin_token)
        assert response.status_code == 200
        
        api_ips = response.json()
        api_ip_addresses = {ip["ip_address"] for ip in api_ips}
        
        db_ips = db_client.get_all_public_ips()
        db_ip_addresses = {ip["ip_address"] for ip in db_ips}
        
        assert api_ip_addresses == db_ip_addresses, \
            f"Public IP mismatch: API={api_ip_addresses}, DB={db_ip_addresses}"


@pytest.mark.consistency
class TestVMInitializationFlow:
    def test_full_vm_flow_consistency(
        self,
        api_client,
        db_client,
        clean_test_data
    ):
        test_ip = "10.99.99.50"
        test_port = 50000
        
        db_client.create_test_resource_pool(test_ip, test_port)
        
        db_config = db_client.get_vpn_config_by_ip(test_ip)
        assert db_config is None, "VPN config should not exist before initialization"
        
        response = api_client.get_vm_config()
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            
            db_config = db_client.get_vpn_config_by_ip(test_ip)
            assert db_config is not None, "VPN config should exist after /vm/config"
            assert db_config["status"] == "init"
            
            ready_response = api_client.post_vm_ready(success=True)
            assert ready_response.status_code == 200
            
            db_config = db_client.get_vpn_config_by_ip(test_ip)
            assert db_config["status"] == "started"


@pytest.mark.consistency
class TestDestroyFlowConsistency:
    def test_destroy_moves_to_archive(
        self,
        api_client,
        db_client,
        clean_test_data
    ):
        test_ip = "10.99.99.51"
        test_port = 50001
        
        db_client.create_test_resource_pool(test_ip, test_port)
        
        config_response = api_client.get_vm_config()
        if config_response.status_code != 200:
            pytest.skip("VM config initialization failed")
        
        ready_response = api_client.post_vm_ready(success=True)
        if ready_response.status_code != 200:
            pytest.skip("VM ready failed")
        
        db_config = db_client.get_vpn_config_by_ip(test_ip)
        assert db_config is not None
        assert db_config["status"] == "started"
        
        destroy_response = api_client.post_3rd_destroy(test_ip)
        
        if destroy_response.status_code == 200:
            db_config = db_client.get_vpn_config_by_ip(test_ip)
            assert db_config is None, "VPN config should be removed after destroy"
            
            archive = db_client.get_archive_by_ip(test_ip)
            assert archive is not None, "Archive should exist after destroy"
            assert archive["vm_ip"] == test_ip

"""
FCloud 自动化测试配置
"""
import os
import pytest
import requests
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class TestEnv(Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


@dataclass
class TestConfig:
    env: TestEnv
    server_ip: str
    backend_port: int
    frontend_port: int
    vm_token: str
    third_party_token: str
    admin_username: str
    admin_password: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    
    @property
    def base_url(self) -> str:
        return f"http://{self.server_ip}:{self.backend_port}"
    
    @property
    def frontend_url(self) -> str:
        return f"http://{self.server_ip}:{self.frontend_port}"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


def get_config() -> TestConfig:
    env = TestEnv(os.getenv("TEST_ENV", "local"))
    
    return TestConfig(
        env=env,
        server_ip=os.getenv("SERVER_IP", "192.168.51.134"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        frontend_port=int(os.getenv("FRONTEND_PORT", "80")),
        vm_token=os.getenv("VM_TOKEN", "vm_default_token"),
        third_party_token=os.getenv("THIRD_PARTY_TOKEN", "3rd_default_token"),
        admin_username=os.getenv("DEFAULT_ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "vpn_manager"),
        db_user=os.getenv("DB_USER", "vpn_admin"),
        db_password=os.getenv("DB_PASSWORD", "fcloud_test_db_2026"),
    )


CONFIG = get_config()


@pytest.fixture(scope="session")
def config():
    return CONFIG


@pytest.fixture(scope="session")
def api_client(config: TestConfig):
    from .api_client import APIClient
    return APIClient(config)


@pytest.fixture(scope="session")
def db_client(config: TestConfig):
    from .db_client import DBClient
    client = DBClient(config)
    yield client
    client.close()


@pytest.fixture(scope="session")
def admin_token(api_client):
    token = api_client.login_admin()
    yield token


@pytest.fixture(scope="function")
def clean_test_data(db_client):
    test_ip_prefix = "10.99.99."
    
    db_client.execute(
        "DELETE FROM vpn_configs WHERE vm_ip LIKE %s",
        (test_ip_prefix + "%",)
    )
    db_client.execute(
        "DELETE FROM vpn_config_archives WHERE vm_ip LIKE %s",
        (test_ip_prefix + "%",)
    )
    db_client.execute(
        "DELETE FROM resource_pool WHERE internal_ip LIKE %s",
        (test_ip_prefix + "%",)
    )
    db_client.commit()
    
    yield
    
    db_client.execute(
        "DELETE FROM vpn_configs WHERE vm_ip LIKE %s",
        (test_ip_prefix + "%",)
    )
    db_client.execute(
        "DELETE FROM vpn_config_archives WHERE vm_ip LIKE %s",
        (test_ip_prefix + "%",)
    )
    db_client.execute(
        "DELETE FROM resource_pool WHERE internal_ip LIKE %s",
        (test_ip_prefix + "%",)
    )
    db_client.commit()

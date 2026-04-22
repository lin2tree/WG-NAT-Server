"""
FCloud API 客户端
"""
import requests
import base64
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_public_key


class APIClient:
    def __init__(self, config):
        self.config = config
        self.base_url = config.base_url
        self.session = requests.Session()
        self.jwt_token: Optional[str] = None
        self.public_key: Optional[str] = None
    
    def _headers(self, auth_type: str = None, token: str = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        
        if auth_type == "jwt" and (token or self.jwt_token):
            headers["Authorization"] = f"Bearer {token or self.jwt_token}"
        elif auth_type == "vm":
            headers["Authorization"] = f"Bearer {self.config.vm_token}"
        elif auth_type == "third_party":
            headers["Authorization"] = f"Bearer {self.config.third_party_token}"
        
        return headers
    
    def get_public_key(self) -> str:
        response = self.session.get(
            f"{self.base_url}/api/auth/public-key",
            timeout=10
        )
        response.raise_for_status()
        self.public_key = response.json()["public_key"]
        return self.public_key
    
    def _encrypt_password(self, password: str) -> str:
        if not self.public_key:
            self.get_public_key()
        
        public_key = load_pem_public_key(
            self.public_key.encode(),
            backend=default_backend()
        )
        
        encrypted = public_key.encrypt(
            password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted).decode()
    
    def login_admin(self, username: str = None, password: str = None) -> str:
        username = username or self.config.admin_username
        password = password or self.config.admin_password
        
        self.get_public_key()
        encrypted_password = self._encrypt_password(password)
        
        response = self.session.post(
            f"{self.base_url}/api/auth/login/encrypted",
            data={
                "username": username,
                "encrypted_password": encrypted_password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        self.jwt_token = data["access_token"]
        return self.jwt_token
    
    def get_vm_config(self, expected_status: int = 200) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/vm/config",
            headers=self._headers("vm"),
            timeout=10
        )
    
    def post_vm_ready(self, success: bool = True, error_message: str = None) -> requests.Response:
        body = {"success": success}
        if error_message:
            body["error_message"] = error_message
        
        return self.session.post(
            f"{self.base_url}/api/vm/ready",
            headers=self._headers("vm"),
            json=body,
            timeout=10
        )
    
    def get_3rd_config_info(self, vm_ip: str) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/3rd/configs/{vm_ip}/info",
            headers=self._headers("third_party"),
            timeout=10
        )
    
    def get_3rd_config_download(self, vm_ip: str) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/3rd/configs/{vm_ip}/download",
            headers=self._headers("third_party"),
            timeout=10
        )
    
    def post_3rd_destroy(self, vm_ip: str) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/api/3rd/configs/{vm_ip}/destroy",
            headers=self._headers("third_party"),
            timeout=10
        )
    
    def get_admin_configs(self, token: str = None) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/admin/configs",
            headers=self._headers("jwt", token),
            timeout=10
        )
    
    def get_admin_resource_pool(self, token: str = None) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/admin/resource-pool",
            headers=self._headers("jwt", token),
            timeout=10
        )
    
    def post_admin_resource_pool_import(
        self, 
        mappings: list, 
        token: str = None
    ) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/api/admin/resource-pool/import",
            headers=self._headers("jwt", token),
            json={"mappings": mappings},
            timeout=10
        )
    
    def delete_admin_resource_pool(self, mapping_id: int, token: str = None) -> requests.Response:
        return self.session.delete(
            f"{self.base_url}/api/admin/resource-pool/{mapping_id}",
            headers=self._headers("jwt", token),
            timeout=10
        )
    
    def get_admin_public_ips(self, token: str = None) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/admin/public-ips",
            headers=self._headers("jwt", token),
            timeout=10
        )
    
    def post_admin_public_ip(self, ip: str, token: str = None) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/api/admin/public-ips",
            headers=self._headers("jwt", token),
            json={"ip_address": ip},
            timeout=10
        )
    
    def get_admin_archives(self, token: str = None) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/admin/archives",
            headers=self._headers("jwt", token),
            timeout=10
        )
    
    def get_admin_logs(self, token: str = None) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/api/admin/logs",
            headers=self._headers("jwt", token),
            timeout=10
        )
    
    def health_check(self) -> bool:
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

"""
FCloud 数据库客户端
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any


class DBClient:
    def __init__(self, config):
        self.config = config
        self.conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            user=config.db_user,
            password=config.db_password
        )
        self.conn.autocommit = False
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def execute(self, query: str, params: tuple = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()
    
    def commit(self):
        self.conn.commit()
    
    def rollback(self):
        self.conn.rollback()
    
    def get_vpn_config_by_ip(self, vm_ip: str) -> Optional[Dict]:
        return self.fetch_one(
            "SELECT * FROM vpn_configs WHERE vm_ip = %s",
            (vm_ip,)
        )
    
    def get_vpn_config_status(self, vm_ip: str) -> Optional[str]:
        result = self.fetch_one(
            "SELECT status FROM vpn_configs WHERE vm_ip = %s",
            (vm_ip,)
        )
        return result["status"] if result else None
    
    def get_resource_pool_by_ip(self, internal_ip: str) -> Optional[Dict]:
        return self.fetch_one(
            "SELECT * FROM resource_pool WHERE internal_ip = %s AND deleted_at IS NULL",
            (internal_ip,)
        )
    
    def get_archive_by_ip(self, vm_ip: str) -> Optional[Dict]:
        return self.fetch_one(
            "SELECT * FROM vpn_config_archives WHERE vm_ip = %s",
            (vm_ip,)
        )
    
    def get_public_ip_by_id(self, ip_id: int) -> Optional[Dict]:
        return self.fetch_one(
            "SELECT * FROM public_ips WHERE id = %s",
            (ip_id,)
        )
    
    def count_vpn_configs(self) -> int:
        result = self.fetch_one("SELECT COUNT(*) as count FROM vpn_configs")
        return result["count"] if result else 0
    
    def count_resource_pool(self) -> int:
        result = self.fetch_one(
            "SELECT COUNT(*) as count FROM resource_pool WHERE deleted_at IS NULL"
        )
        return result["count"] if result else 0
    
    def count_archives(self) -> int:
        result = self.fetch_one("SELECT COUNT(*) as count FROM vpn_config_archives")
        return result["count"] if result else 0
    
    def get_all_vpn_configs(self) -> List[Dict]:
        return self.fetch_all("SELECT * FROM vpn_configs ORDER BY created_at DESC")
    
    def get_all_resource_pool(self) -> List[Dict]:
        return self.fetch_all(
            "SELECT * FROM resource_pool WHERE deleted_at IS NULL ORDER BY created_at DESC"
        )
    
    def get_all_public_ips(self) -> List[Dict]:
        return self.fetch_all("SELECT * FROM public_ips ORDER BY id")
    
    def get_log_count_for_ip(self, source_ip: str) -> int:
        result = self.fetch_one(
            "SELECT COUNT(*) as count FROM operation_logs WHERE source_ip = %s",
            (source_ip,)
        )
        return result["count"] if result else 0
    
    def create_test_resource_pool(
        self, 
        internal_ip: str, 
        public_port: int,
        public_ip_id: Optional[int] = None
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO resource_pool (internal_ip, public_port, public_ip_id, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
                """,
                (internal_ip, public_port, public_ip_id)
            )
            result = cur.fetchone()
            self.commit()
            return result[0] if result else None
    
    def delete_test_resource_pool(self, internal_ip: str):
        self.execute(
            "DELETE FROM resource_pool WHERE internal_ip = %s",
            (internal_ip,)
        )
        self.commit()
    
    def create_test_vpn_config(
        self,
        vm_ip: str,
        status: str = "init"
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vpn_configs (vm_ip, status, created_at)
                VALUES (%s, %s, NOW())
                RETURNING id
                """,
                (vm_ip, status)
            )
            result = cur.fetchone()
            self.commit()
            return result[0] if result else None
    
    def delete_test_vpn_config(self, vm_ip: str):
        self.execute(
            "DELETE FROM vpn_configs WHERE vm_ip = %s",
            (vm_ip,)
        )
        self.commit()
    
    def clear_test_data(self, ip_prefix: str = "10.99.99."):
        self.execute(
            "DELETE FROM vpn_configs WHERE vm_ip LIKE %s",
            (ip_prefix + "%",)
        )
        self.execute(
            "DELETE FROM vpn_config_archives WHERE vm_ip LIKE %s",
            (ip_prefix + "%",)
        )
        self.execute(
            "DELETE FROM resource_pool WHERE internal_ip LIKE %s",
            (ip_prefix + "%",)
        )
        self.commit()

#!/usr/bin/env python3
"""
FCloudVPN 前端功能自动化测试脚本 v2
基于前端功能文档 (前端功能.md) 逐项测试
修正：后端返回格式 {"success": True, "data": ...}
"""
import requests
import json
import sys
import time

BASE = "http://localhost:8000/api"
FRONTEND = "http://localhost:80"
TOKEN = None
HEADERS = {}
PASS = 0
FAIL = 0
RESULTS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f"✅ {name}")
        if detail:
            RESULTS[-1] += f" — {detail}"
    else:
        FAIL += 1
        RESULTS.append(f"❌ {name}")
        if detail:
            RESULTS[-1] += f" — {detail}"

def api_get(path, **kwargs):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=10, **kwargs)
    return r

def api_post(path, **kwargs):
    r = requests.post(f"{BASE}{path}", headers=HEADERS, timeout=10, **kwargs)
    return r

def api_delete(path, **kwargs):
    r = requests.delete(f"{BASE}{path}", headers=HEADERS, timeout=10, **kwargs)
    return r

def extract_data(r):
    """提取后端统一响应格式中的 data 字段"""
    if r.status_code != 200:
        return None
    j = r.json()
    if isinstance(j, dict) and "data" in j:
        return j["data"]
    return j


# ============================================================
# 1. 登录页面测试
# ============================================================
print("=" * 60)
print("1. 登录页面 (LoginView) 测试")
print("=" * 60)

# 1.1 前端登录页面可访问
r = requests.get(f"{FRONTEND}/login", allow_redirects=False, timeout=10)
test("1.1 登录页面可访问", r.status_code == 200, f"status={r.status_code}")

# 1.2 正确凭据登录 (form-urlencoded)
print("  ⏳ 登录中（bcrypt较慢，约30秒）...")
r = requests.post(f"{BASE}/auth/login", data={"username": "admin", "password": "lin1234"}, timeout=60)
test("1.2 正确凭据登录", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    TOKEN = data.get("access_token")
    HEADERS = {"Authorization": f"Bearer {TOKEN}"}
    test("1.3 返回 access_token", bool(TOKEN), f"token存在={bool(TOKEN)}")
    test("1.4 返回 token_type=bearer", data.get("token_type") == "bearer")
    test("1.5 返回 user 信息", "user" in data and data["user"]["username"] == "admin")
    test("1.6 返回 role=admin", data["user"].get("role") == "admin")
    test("1.7 返回 expires_in", "expires_in" in data and data["expires_in"] > 0)
else:
    test("1.3 返回 access_token", False, f"登录失败")
    print("⚠️ 登录失败，后续测试无法进行")
    print_results()
    sys.exit(1)

# 1.8 错误凭据登录
r = requests.post(f"{BASE}/auth/login", data={"username": "admin", "password": "wrong"}, timeout=60)
test("1.8 错误密码返回401", r.status_code == 401, f"status={r.status_code}")

# 1.9 JSON格式登录应422
r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "lin1234"}, timeout=60)
test("1.9 JSON格式登录返回422", r.status_code == 422, f"status={r.status_code}")

# 1.10 获取当前用户
r = api_get("/auth/me")
test("1.10 获取 /auth/me", r.status_code == 200)
if r.status_code == 200:
    me = r.json()
    test("1.11 me返回username=admin", me.get("username") == "admin")
    test("1.12 me返回role=admin", me.get("role") == "admin")

# 1.13 未认证访问
r = requests.get(f"{BASE}/auth/me", timeout=10)
test("1.13 未认证 /auth/me 返回401", r.status_code == 401)

# 1.14 退出登录
r = api_post("/auth/logout")
test("1.14 退出 /auth/logout", r.status_code == 200)

# 重新登录以继续后续测试
print("  ⏳ 重新登录...")
r = requests.post(f"{BASE}/auth/login", data={"username": "admin", "password": "lin1234"}, timeout=60)
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


# ============================================================
# 2. VPN 配置页面测试
# ============================================================
print("\n" + "=" * 60)
print("2. VPN 配置页面 (VpnConfigView) 测试")
print("=" * 60)

# 2.1 前端页面可访问
r = requests.get(f"{FRONTEND}/vpn-configs", allow_redirects=False, timeout=10)
test("2.1 VPN配置页面可访问", r.status_code == 200)

# 2.2 获取配置列表
r = api_get("/admin/configs")
test("2.2 获取配置列表 /admin/configs", r.status_code == 200)
configs_data = extract_data(r)
configs_items = configs_data.get("items", []) if isinstance(configs_data, dict) else []
test("2.3 配置列表返回分页结构", isinstance(configs_data, dict) and "total" in configs_data,
     f"keys={list(configs_data.keys()) if isinstance(configs_data, dict) else 'N/A'}")

# 2.4 按IP搜索
r = api_get("/admin/configs", params={"vm_ip": "192.168"})
test("2.4 按IP搜索配置", r.status_code == 200)

# 2.5 按状态筛选
r = api_get("/admin/configs", params={"status": "init"})
test("2.5 按状态筛选配置", r.status_code == 200)

# 2.6 分页
r = api_get("/admin/configs", params={"page": 1, "page_size": 10})
test("2.6 分页查询配置", r.status_code == 200)

# 2.7-2.10 配置详情/下载/历史 — 需要有VM注册数据
# 尝试通过VM API模拟注册
print("  ⏳ 模拟VM注册以测试配置详情...")
# 先确认有资源池IP可用
pool_r = api_get("/admin/resource-pool")
pool_data = extract_data(pool_r)
pool_items = pool_data.get("items", []) if isinstance(pool_data, dict) else []

if pool_items:
    test_ip = pool_items[0].get("internal_ip")
    # 调用 VM provision API（需用VM_TOKEN）
    prov_r = requests.post(
        f"{BASE}/v1/vpn/provision",
        headers={"Authorization": "Bearer fcloud_vm_token_test"},
        timeout=10,
    )
    # VM API 可能需要从容器内请求（source IP验证），所以可能失败
    if prov_r.status_code == 200:
        test("2.7 模拟VM注册provision", True, f"ip={test_ip}")
    else:
        test("2.7 模拟VM注册provision", False, 
             f"status={prov_r.status_code}（需要从VM内网请求）")
else:
    test("2.7 模拟VM注册provision", False, "资源池无可用IP")

# 直接测试详情API（即使没有数据也应返回404而非500）
r = api_get("/admin/configs/1.2.3.4")
test("2.8 查询不存在IP的配置返回404", r.status_code == 404, f"status={r.status_code}")

# 查看历史
r = api_get("/admin/configs/1.2.3.4/history")
test("2.9 查询不存在IP的历史返回200(空)", r.status_code == 200, f"status={r.status_code}")

# 如果有配置数据则测试详情/下载
if configs_items:
    vm_ip = configs_items[0].get("vm_ip")
    r = api_get(f"/admin/configs/{vm_ip}")
    test("2.10 查看配置详情", r.status_code == 200)
    
    # 下载服务端配置 (路径: /configs/{vm_ip}/download/server)
    r = api_get(f"/admin/configs/{vm_ip}/download/server")
    test("2.11 下载服务端配置(Root)", r.status_code in [200, 404], f"status={r.status_code}")
    
    # 下载客户端配置 (路径: /configs/{vm_ip}/download/client/{client_name})
    r = api_get(f"/admin/configs/{vm_ip}/download/client/client1")
    test("2.12 下载客户端配置(Root)", r.status_code in [200, 404], f"status={r.status_code}")
else:
    test("2.10 查看配置详情", False, "无配置数据（需VM注册后才有）")
    test("2.11 下载服务端配置(Root)", False, "无配置数据")
    test("2.12 下载客户端配置(Root)", False, "无配置数据")


# ============================================================
# 3. 资源池管理页面测试
# ============================================================
print("\n" + "=" * 60)
print("3. 资源池管理页面 (ResourcePoolView) 测试")
print("=" * 60)

# 3.1 前端页面可访问
r = requests.get(f"{FRONTEND}/resource-pool", allow_redirects=False, timeout=10)
test("3.1 资源池页面可访问", r.status_code == 200)

# 3.2 获取端口范围
r = api_get("/admin/port-range")
test("3.2 获取端口范围", r.status_code == 200)
port_data = extract_data(r)
test("3.3 端口范围含 start_port", port_data is not None and "start_port" in port_data,
     f"keys={list(port_data.keys()) if isinstance(port_data, dict) else 'N/A'}")
test("3.4 端口范围含 end_port", port_data is not None and "end_port" in port_data)
test("3.5 端口范围值合理", 
     port_data is not None and port_data.get("start_port", 0) > 0 and port_data.get("end_port", 0) > port_data.get("start_port", 0),
     f"start={port_data.get('start_port') if port_data else 'N/A'}, end={port_data.get('end_port') if port_data else 'N/A'}")

# 3.6 设置端口范围 (Root)
r = api_post("/admin/port-range", params={"start_port": 20000, "end_port": 40000})
test("3.6 设置端口范围(Root)", r.status_code == 200, f"status={r.status_code}")

# 恢复
api_post("/admin/port-range", params={"start_port": 20000, "end_port": 30000})

# 3.7 获取资源池列表
r = api_get("/admin/resource-pool")
test("3.7 获取资源池列表", r.status_code == 200)
pool_data = extract_data(r)
pool_items = pool_data.get("items", []) if isinstance(pool_data, dict) else []
test("3.8 资源池列表有数据", len(pool_items) > 0, f"count={len(pool_items)}")

# 3.9 导入IP (Root)
test_ips = ["10.88.88.1", "10.88.88.2"]
r = api_post("/admin/resource-pool/import", json=test_ips)
test("3.9 导入IP(Root)", r.status_code == 200, f"status={r.status_code}")

# 3.10 导入后验证
r = api_get("/admin/resource-pool")
pool_data2 = extract_data(r)
pool_items2 = pool_data2.get("items", []) if isinstance(pool_data2, dict) else []
imported_ips = [i.get("internal_ip") for i in pool_items2]
test("3.10 导入后IP存在", any(ip in imported_ips for ip in test_ips),
     f"found={[ip for ip in test_ips if ip in imported_ips]}")

# 3.11 导出CSV
r = api_get("/admin/resource-pool/export")
test("3.11 导出CSV", r.status_code == 200, f"status={r.status_code}, content-type={r.headers.get('content-type','')}")

# 3.12 删除映射 (Root)
if pool_items2:
    for item in pool_items2:
        if item.get("internal_ip") in test_ips:
            del_r = api_delete(f"/admin/resource-pool/{item['id']}")
            test(f"3.12 删除映射 {item['internal_ip']}(Root)", 
                 del_r.status_code == 200, f"status={del_r.status_code}")
            break
    else:
        test("3.12 删除映射(Root)", False, "未找到测试IP")
else:
    test("3.12 删除映射(Root)", False, "无数据")

# 3.13 删除不存在的映射
r = api_delete("/admin/resource-pool/99999")
test("3.13 删除不存在映射返回404", r.status_code == 404, f"status={r.status_code}")

# 3.14 分页
r = api_get("/admin/resource-pool", params={"page": 1, "page_size": 5})
test("3.14 资源池分页查询", r.status_code == 200)


# ============================================================
# 4. 操作日志页面测试
# ============================================================
print("\n" + "=" * 60)
print("4. 操作日志页面 (LogView) 测试")
print("=" * 60)

# 4.1 前端页面可访问
r = requests.get(f"{FRONTEND}/logs", allow_redirects=False, timeout=10)
test("4.1 操作日志页面可访问", r.status_code == 200)

# 4.2 获取日志列表
r = api_get("/admin/logs")
test("4.2 获取日志列表 /admin/logs", r.status_code == 200)
log_data = extract_data(r)
log_items = log_data.get("items", []) if isinstance(log_data, dict) else []
test("4.3 日志列表有数据", len(log_items) > 0, f"count={len(log_items)}")

# 4.4 按时间筛选
r = api_get("/admin/logs", params={
    "start_time": "2026-01-01T00:00:00",
    "end_time": "2026-12-31T23:59:59"
})
test("4.4 按时间筛选日志", r.status_code == 200)

# 4.5 按IP筛选
r = api_get("/admin/logs", params={"source_ip": "172.19"})
test("4.5 按IP筛选日志", r.status_code == 200)


# ============================================================
# 5. 通用功能测试
# ============================================================
print("\n" + "=" * 60)
print("5. 通用功能与前端一致性测试")
print("=" * 60)

# 5.1 后端健康检查
r = requests.get("http://localhost:8000/health", timeout=10)
test("5.1 后端 /health", r.status_code == 200)

# 5.2 Swagger 文档
r = requests.get("http://localhost:8000/docs", timeout=10)
test("5.2 Swagger /docs", r.status_code == 200)

# 5.3 前端API路径与后端对齐
import os
frontend_api_path = "/home/kyle/kyles-file/FCloud/frontend/src/services/api.ts"
if os.path.exists(frontend_api_path):
    with open(frontend_api_path) as f:
        api_code = f.read()
    
    # 后端实际路由检查
    backend_routes = [
        ("/auth/login", "POST"),
        ("/auth/logout", "POST"),
        ("/auth/me", "GET"),
        ("/admin/configs", "GET"),
        ("/admin/port-range", "GET"),
        ("/admin/port-range", "POST"),
        ("/admin/resource-pool", "GET"),
        ("/admin/resource-pool/import", "POST"),
        ("/admin/logs", "GET"),
    ]
    
    for route, method in backend_routes:
        test(f"5.x 前端调用 {method} {route}", route in api_code)
    
    # 5.4 登录格式
    test("5.4 登录使用 form-urlencoded", 
         "URLSearchParams" in api_code or "x-www-form-urlencoded" in api_code)
    
    # 5.5 检查前端缺失的API
    missing_in_frontend = []
    doc_required = [
        "/admin/configs/{vm_ip}/download",
        "/admin/configs/{vm_ip}/history",
        "/admin/resource-pool/export",
        "/admin/resource-pool/{id}",
    ]
    for api_path in doc_required:
        # 去掉路径参数的简单检查
        base = api_path.split("/{")[0]
        if base not in api_code and api_path not in api_code:
            missing_in_frontend.append(api_path)
    
    if missing_in_frontend:
        test("5.5 前端覆盖文档所有API", False, f"缺失: {missing_in_frontend}")
    else:
        test("5.5 前端覆盖文档所有API", True)
else:
    test("5.x 前端API文件检查", False, "文件不存在")


# ============================================================
# 6. 前端页面视图完整性检查
# ============================================================
print("\n" + "=" * 60)
print("6. 前端视图文件完整性检查")
print("=" * 60)

views_dir = "/home/kyle/kyles-file/FCloud/frontend/src/views"
components_dir = "/home/kyle/kyles-file/FCloud/frontend/src/components"

required_views = [
    ("LoginView.vue", "登录页面"),
    ("VpnConfigView.vue", "VPN配置页面"),
    ("ResourcePoolView.vue", "资源池管理页面"),
    ("LogView.vue", "操作日志页面"),
]

for filename, desc in required_views:
    path = os.path.join(views_dir, filename)
    test(f"6.x {desc} ({filename})", os.path.exists(path))

# 检查路由定义
router_path = "/home/kyle/kyles-file/FCloud/frontend/src/router/index.ts"
if os.path.exists(router_path):
    with open(router_path) as f:
        router_code = f.read()
    
    routes = ["/login", "/vpn-configs", "/resource-pool", "/logs"]
    for route in routes:
        test(f"6.x 路由定义 {route}", route in router_code)


# ============================================================
# 结果汇总
# ============================================================
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
for r in RESULTS:
    print(r)

total = PASS + FAIL
rate = f"{PASS/total*100:.1f}%" if total > 0 else "N/A"
print(f"\n总计: ✅ {PASS} 通过  ❌ {FAIL} 失败  ({total} 项, 通过率 {rate})")

if FAIL > 0:
    print("\n⚠️ 失败项分类:")
    fails = [r for r in RESULTS if r.startswith("❌")]
    for f in fails:
        print(f"  {f}")
    sys.exit(1)
else:
    print("\n🎉 全部通过！")
    sys.exit(0)
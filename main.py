# main.py

from fastapi import FastAPI, HTTPException
from mobbin_client import MobbinClient
from pydantic import BaseModel, EmailStr
import os

# --- 从环境中读取启动时必需的配置 ---
MOBBIN_API_KEY = os.getenv("MOBBIN_API_KEY")

if not MOBBIN_API_KEY:
    raise RuntimeError("启动失败：请在 .env 文件中或作为环境变量设置 MOBBIN_API_KEY！")

# --- 在服务启动时，创建一个全局的、可复用的客户端实例 ---
client = MobbinClient(api_key=MOBBIN_API_KEY)

app = FastAPI(
    title="Python Mobbin API (动态登录版)",
    description="提供 API 接口来动态登录并获取数据"
)


# --- 定义用于接收请求数据的模型 ---
class OtpRequest(BaseModel):
    email: EmailStr

class VerifyRequest(BaseModel):
    email: EmailStr
    otp: str

# --- 新增：用于密码登录的请求模型 ---
class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- API 路由定义 ---
@app.get("/", summary="服务健康检查")
def read_root():
    """访问根路径，确认服务正在运行。"""
    return {"status": "ok", "message": "Mobbin API Service is running."}

@app.post("/api/login/send-otp", summary="【方式一】第一步：发送登录验证码")
def send_otp(request_data: OtpRequest):
    """向指定邮箱发送一次性登录密码 (OTP)。适用于所有账户类型。"""
    success = client.send_login_otp(request_data.email)
    if not success:
        raise HTTPException(status_code=500, detail="发送验证码失败，请检查邮箱地址或查看服务日志。")
    return {"message": f"验证码已成功发送至 {request_data.email}，请查收。"}

@app.post("/api/login/verify", summary="【方式一】第二步：验证并完成登录")
def verify_and_login(request_data: VerifyRequest):
    """使用邮箱和收到的 OTP 验证码来登录，并获取会话凭证。"""
    session_data = client.verify_otp_and_login(request_data.email, request_data.otp)
    if not session_data:
        raise HTTPException(status_code=401, detail="验证失败，验证码错误或已过期。")
    return {"message": "登录成功！服务现在已认证，可以开始请求数据。"}

# --- 新增：密码登录接口 ---
@app.post("/api/login/password", summary="【方式二】使用密码登录")
def login_via_password(request_data: PasswordLoginRequest):
    """
    使用邮箱和密码直接登录。
    注意：仅适用于在 Mobbin 网站上单独设置过密码的账户。
    """
    session_data = client.login_with_password(request_data.email, request_data.password)
    if not session_data:
        raise HTTPException(status_code=401, detail="登录失败，请检查邮箱和密码是否正确。")
    return {"message": "密码登录成功！服务现在已认证，可以开始请求数据。"}


@app.get("/api/search", summary="搜索 App (需要先登录)")
def search_for_apps(q: str):
    """根据关键词搜索 App。必须在调用此接口前，先完成登录。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="禁止访问：客户端未登录或登录已过期，请先调用登录接口。")
    
    results = client.search_apps(q)
    if results is None:
        raise HTTPException(status_code=500, detail="搜索失败或上游服务器（Mobbin）错误。")
    return results

@app.get("/api/list-sample-apps", summary="列出示例应用")
def list_sample_apps(limit: int = 10, offset: int = 0):
    """列出一些示例应用，用于了解数据结构和可搜索的内容。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    import requests
    
    url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
    headers = client._headers.copy()
    
    # 获取一些示例数据
    params = {
        "select": "*",
        "limit": str(limit),
        "offset": str(offset),
        "order": "updatedAt.desc"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        if resp.ok:
            apps = resp.json()
            # 简化输出，只显示关键字段
            simplified_apps = []
            for app in apps:
                simplified_apps.append({
                    "appName": app.get("appName"),
                    "companyName": app.get("companyName"),
                    "platform": app.get("platform"),
                    "id": app.get("id"),
                    "updatedAt": app.get("updatedAt")
                })
            
            return {
                "total_returned": len(simplified_apps),
                "offset": offset,
                "apps": simplified_apps,
                "sample_full_record": apps[0] if apps else None
            }
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/latest-apps", summary="获取最新 App 列表")
def get_latest_apps(limit: int = 20):
    """获取最新的应用列表。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    # 使用新的 Mobbin API
    import requests
    
    url = "https://mobbin.com/api/browse/ios/apps"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {client.access_token}",
        "Origin": "https://mobbin.com",
        "Referer": "https://mobbin.com/",
        "User-Agent": client._headers["User-Agent"]
    }
    
    params = {
        "pageSize": str(limit),
        "sortBy": "publishedAt"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        if resp.ok:
            return resp.json()
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/browse/categories", summary="浏览应用类别")
def browse_by_category(category: str, platform: str = "ios", page_size: int = 20):
    """按类别浏览应用。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    apps = client.browse_apps_by_category(category, platform, page_size)
    if apps is None:
        raise HTTPException(status_code=500, detail="获取应用失败")
    return apps

@app.get("/api/test/mobbin-api", summary="测试 Mobbin 直接 API")
def test_mobbin_api():
    """直接测试 mobbin.com 的 API"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    import requests
    
    # 测试直接调用 Mobbin API
    test_results = []
    
    # 基础 URL
    base_url = "https://mobbin.com/api/browse/ios/apps"
    
    # 准备请求头
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {client.access_token}",
        "Origin": "https://mobbin.com",
        "Referer": "https://mobbin.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 测试1: 按类别获取
    params1 = {
        "filterOperator": "and",
        "appCategories[]": "Travel & Transportation",
        "pageSize": "5",
        "sortBy": "publishedAt"
    }
    
    try:
        resp = requests.get(base_url, headers=headers, params=params1)
        test_results.append({
            "test": "Browse by category",
            "url": base_url,
            "params": params1,
            "status": resp.status_code,
            "response": resp.json() if resp.ok else resp.text[:200]
        })
    except Exception as e:
        test_results.append({"test": "Browse by category", "error": str(e)})
    
    # 测试2: 尝试搜索
    search_params = [
        {"q": "uber", "pageSize": "5"},
        {"query": "uber", "pageSize": "5"},
        {"search": "uber", "pageSize": "5"},
        {"keyword": "uber", "pageSize": "5"},
        {"name": "uber", "pageSize": "5"}
    ]
    
    for params in search_params:
        try:
            resp = requests.get(base_url, headers=headers, params=params)
            test_results.append({
                "test": f"Search with {list(params.keys())[0]}",
                "params": params,
                "status": resp.status_code,
                "has_results": bool(resp.ok and resp.json())
            })
            if resp.ok and resp.json():
                break
        except:
            pass
    
    # 测试3: 获取所有应用（不带过滤）
    params3 = {
        "pageSize": "10",
        "sortBy": "publishedAt"
    }
    
    try:
        resp = requests.get(base_url, headers=headers, params=params3)
        test_results.append({
            "test": "Get all apps",
            "params": params3,
            "status": resp.status_code,
            "count": len(resp.json()) if resp.ok else 0
        })
    except Exception as e:
        test_results.append({"test": "Get all apps", "error": str(e)})
    
    return {
        "api_endpoint": base_url,
        "test_results": test_results,
        "note": "Check which parameters work for searching"
    }

@app.get("/api/test/table-info", summary="获取表结构信息")
def get_table_info():
    """获取 apps 表的结构信息，找出正确的字段名。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    import requests
    
    url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
    headers = client._headers.copy()
    
    # 获取一条记录来查看所有字段
    params = {
        "select": "*",
        "limit": "1"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        if resp.ok and resp.json():
            record = resp.json()[0]
            
            # 分析字段
            field_info = {}
            for key, value in record.items():
                field_info[key] = {
                    "type": type(value).__name__,
                    "sample": str(value)[:100] if value else None
                }
            
            # 查找可能用于搜索的字段
            searchable_fields = []
            for field in field_info:
                if any(keyword in field.lower() for keyword in ['name', 'title', 'app', 'company']):
                    searchable_fields.append(field)
            
            return {
                "total_fields": len(field_info),
                "fields": field_info,
                "searchable_fields": searchable_fields,
                "sample_record": record
            }
        else:
            return {"error": f"Failed to get table info: {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug/headers", summary="调试：查看当前客户端的请求头")
def debug_headers():
    """用于调试的端点，显示当前客户端使用的请求头。"""
    headers_copy = client._headers.copy()
    # 隐藏敏感信息
    if "Authorization" in headers_copy and headers_copy["Authorization"]:
        headers_copy["Authorization"] = headers_copy["Authorization"][:20] + "..."
    if "apikey" in headers_copy and headers_copy["apikey"]:
        headers_copy["apikey"] = headers_copy["apikey"][:10] + "..."
    
    return {
        "headers": headers_copy,
        "has_access_token": bool(client.access_token),
        "api_key_set": bool(client.api_key)
    }

@app.get("/api/test/direct-search", summary="测试：直接调用 Mobbin API")
def test_direct_search(q: str):
    """直接测试 Mobbin API，不经过客户端封装。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    import requests
    
    # 测试不同的搜索参数组合
    test_results = []
    
    # 测试1: 使用 ilike
    url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
    headers = client._headers.copy()
    
    params1 = {
        "select": "*",
        "platform": "eq.ios",
        "appName": f"ilike.%{q}%",
        "limit": "10"
    }
    
    try:
        resp1 = requests.get(url, headers=headers, params=params1)
        test_results.append({
            "test": "ilike search",
            "status": resp1.status_code,
            "params": params1,
            "count": len(resp1.json()) if resp1.ok else 0,
            "sample": resp1.json()[:2] if resp1.ok and resp1.json() else None
        })
    except Exception as e:
        test_results.append({"test": "ilike search", "error": str(e)})
    
    # 测试2: 不带任何过滤条件
    params2 = {
        "select": "*",
        "platform": "eq.ios",
        "limit": "5"
    }
    
    try:
        resp2 = requests.get(url, headers=headers, params=params2)
        test_results.append({
            "test": "no filter",
            "status": resp2.status_code,
            "params": params2,
            "count": len(resp2.json()) if resp2.ok else 0,
            "sample": resp2.json()[:2] if resp2.ok and resp2.json() else None
        })
    except Exception as e:
        test_results.append({"test": "no filter", "error": str(e)})
    
    return {"query": q, "test_results": test_results}

@app.get("/api/test/explore-tables", summary="探索所有可用的表")
def explore_tables():
    """探索 Supabase 中所有可用的表和视图。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    import requests
    
    headers = client._headers.copy()
    base_url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/"
    
    # 可能的表名
    possible_tables = [
        "apps", "applications", "app", "mobile_apps", "ios_apps", "android_apps",
        "screens", "flows", "patterns", "collections", "categories",
        "companies", "developers", "users", "projects",
        "search", "search_results", "app_search",
        "mobbin_apps", "mobbin_screens", "mobbin_flows"
    ]
    
    results = {}
    
    for table in possible_tables:
        url = f"{base_url}{table}"
        params = {"select": "*", "limit": "1"}
        
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    results[table] = {
                        "status": "success",
                        "record_count": len(data),
                        "sample": data[0] if data else None,
                        "fields": list(data[0].keys()) if data and len(data) > 0 else []
                    }
                else:
                    results[table] = {
                        "status": "success",
                        "type": type(data).__name__,
                        "data": data
                    }
            elif resp.status_code == 404:
                # 表不存在，跳过
                pass
            else:
                results[table] = {
                    "status": "error",
                    "code": resp.status_code,
                    "error": resp.text[:100]
                }
        except Exception as e:
            results[table] = {"status": "exception", "error": str(e)}
    
    # 尝试获取表的元数据
    metadata_url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/"
    try:
        resp = requests.options(metadata_url, headers=headers)
        if resp.status_code == 200:
            results["_metadata"] = {
                "headers": dict(resp.headers),
                "options_response": resp.text[:200] if resp.text else None
            }
    except:
        pass
    
    return {
        "found_tables": [k for k, v in results.items() if v.get("status") == "success" and v.get("record_count", 0) > 0],
        "empty_tables": [k for k, v in results.items() if v.get("status") == "success" and v.get("record_count") == 0],
        "details": results
    }

@app.get("/api/test/check-permissions", summary="检查API权限")
def check_permissions():
    """检查当前用户的API权限。"""
    if not client.access_token:
        raise HTTPException(status_code=403, detail="需要先登录")
    
    import requests
    import jwt
    
    # 解析 JWT token 查看权限信息（不验证签名）
    try:
        decoded = jwt.decode(client.access_token, options={"verify_signature": False})
        token_info = {
            "user_id": decoded.get("sub"),
            "email": decoded.get("email"),
            "role": decoded.get("role"),
            "exp": decoded.get("exp"),
            "aud": decoded.get("aud"),
            "app_metadata": decoded.get("app_metadata", {}),
            "user_metadata": decoded.get("user_metadata", {})
        }
    except Exception as e:
        token_info = {"error": str(e)}
    
    # 测试不同的 API 操作
    headers = client._headers.copy()
    base_url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/"
    
    permission_tests = {}
    
    # 测试读取权限
    test_endpoints = [
        ("apps", "读取应用列表"),
        ("screens", "读取屏幕列表"),
        ("flows", "读取流程列表"),
        ("rpc/get_apps", "调用RPC函数"),
    ]
    
    for endpoint, description in test_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            resp = requests.get(url, headers=headers, params={"limit": "1"})
            permission_tests[endpoint] = {
                "description": description,
                "status_code": resp.status_code,
                "has_permission": resp.status_code in [200, 404],  # 404表示表不存在，但有权限访问
                "response": resp.text[:100] if resp.status_code != 200 else "OK"
            }
        except Exception as e:
            permission_tests[endpoint] = {
                "description": description,
                "error": str(e)
            }
    
    return {
        "token_info": token_info,
        "permission_tests": permission_tests,
        "headers_used": {k: v[:20] + "..." if len(v) > 20 else v for k, v in headers.items()}
    }

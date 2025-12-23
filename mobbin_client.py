# mobbin_client.py

import requests

class MobbinClient:
    """
    最终版 Mobbin API 客户端。
    通过 API Key 初始化，并提供程序化登录和数据获取功能。
    支持“邮箱+验证码”和“邮箱+密码”两种登录方式。
    """
    def __init__(self, api_key: str, access_token: str = None):
        """
        使用公开的 API Key 和可选的 Access Token 初始化客户端。
        :param api_key: 从浏览器网络请求中找到的公开匿名 Key。
        :param access_token: 登录后获取到的个人身份凭证。
        """
        if not api_key:
            raise ValueError("客户端初始化时必须提供 API Key！")
        
        self.api_key = api_key
        self.access_token = access_token
        
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "apikey": self.api_key
        }
        if self.access_token:
            self._update_authorization_header()

    def _update_authorization_header(self):
        """私有方法，用于更新或添加 Authorization 头。"""
        if self.access_token:
            self._headers["Authorization"] = f"Bearer {self.access_token}"

    def _make_request(self, method: str, url: str, headers: dict, params: dict = None, json_data: dict = None):
        """统一的私有请求方法，用于捕获和打印错误。"""
        try:
            # 打印请求详情用于调试
            print(f"请求方法: {method}")
            print(f"请求URL: {url}")
            if params:
                print(f"请求参数: {params}")
            
            response = requests.request(method, url, headers=headers, params=params, json=json_data, timeout=20)
            
            # 打印响应状态
            print(f"响应状态码: {response.status_code}")
            
            # 处理非 200 状态码
            if response.status_code == 404:
                print("404 错误：端点不存在")
                return None
            elif response.status_code >= 400:
                print(f"错误响应: {response.text[:200]}")
                return None
                
            response.raise_for_status()
            
            # 尝试解析 JSON
            result = response.json()
            print(f"响应数据条数: {len(result) if isinstance(result, list) else 'N/A'}")
            
            return result
        except requests.exceptions.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print(f"原始响应内容: {response.text[:500]}...")  # 只打印前500字符
            return None
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应详情: {e.response.status_code} - {e.response.text}")
            return None

    def send_login_otp(self, email: str):
        """【登录方式一】第一步：向指定邮箱发送一次性登录密码 (OTP)。"""
        print(f"正在向邮箱 {email} 发送登录验证码...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/auth/v1/otp"
        payload = {"email": email, "create_user": False}
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        response_json = self._make_request("POST", url, headers=headers, json_data=payload)
        return response_json is not None

    def verify_otp_and_login(self, email: str, otp: str):
        """【登录方式一】第二步：使用邮箱和 OTP 验证，并获取 access_token。"""
        print(f"正在使用邮箱 {email} 和验证码进行验证...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/auth/v1/verify"
        payload = {"type": "email", "email": email, "token": otp}
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        data = self._make_request("POST", url, headers=headers, json_data=payload)
        if data and data.get("access_token"):
            self.access_token = data["access_token"]
            self._update_authorization_header()
            print("OTP 登录成功！Access Token 已获取并设置到客户端。")
            return data
        else:
            print("OTP 验证失败或响应中未找到 access_token。")
            return None

    # --- 新增的密码登录方法 ---
    def login_with_password(self, email: str, password: str):
        """
        【登录方式二】使用邮箱和密码进行登录。
        注意：仅适用于在 Mobbin 上单独设置过密码的账户。
        """
        print(f"正在尝试使用邮箱 {email} 和密码登录...")
        
        # Supabase 用于密码登录的 API endpoint
        url = "https://ujasntkfphywizsdaapi.supabase.co/auth/v1/token?grant_type=password"
        
        payload = {
            "email": email,
            "password": password
        }
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        data = self._make_request("POST", url, headers=headers, json_data=payload)
        
        if data and data.get("access_token"):
            self.access_token = data["access_token"]
            self._update_authorization_header()
            print("密码登录成功！Access Token 已获取并设置到客户端。")
            return data
        else:
            print("密码登录失败，请检查邮箱和密码。")
            return None

    def search_apps(self, query: str, platform: str = "ios"):
        """
        搜索 App - 使用 Supabase 数据库直接查询
        """
        print(f"正在搜索 App: '{query}'...")
        
        # 使用 Supabase REST API 进行数据库查询
        url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
        
        # 构建查询参数 - 使用 ilike 进行模糊匹配
        params = {
            "select": "*",
            "platform": f"eq.{platform}",
            "appName": f"ilike.%{query}%",
            "limit": "50",
            "order": "updatedAt.desc"
        }
        
        result = self._make_request("GET", url, headers=self._headers, params=params)
        
        # 如果 appName 搜索没有结果，尝试搜索 companyName
        if result is not None and isinstance(result, list) and len(result) == 0:
            print(f"appName 搜索无结果，尝试搜索 companyName...")
            params_company = {
                "select": "*",
                "platform": f"eq.{platform}",
                "companyName": f"ilike.%{query}%",
                "limit": "50",
                "order": "updatedAt.desc"
            }
            result = self._make_request("GET", url, headers=self._headers, params=params_company)
        
        return result
    
    def _build_cookie(self):
        """构建 Cookie 字符串，包含认证 token"""
        import urllib.parse
        import json
        
        # 构建 Supabase auth token cookie
        auth_data = {
            "access_token": self.access_token,
            "refresh_token": "placeholder",  # 实际需要时替换
            "user": {
                "id": "placeholder",
                "email": "placeholder"
            },
            "token_type": "bearer",
            "expires_in": 3600,
            "expires_at": 9999999999  # 未来的时间戳
        }
        
        # URL 编码 JSON 数据
        auth_cookie_value = urllib.parse.quote(json.dumps(auth_data))
        
        # 构建基本的 cookie 字符串
        cookies = [
            f"sb-ujasntkfphywizsdaapi-auth-token={auth_cookie_value}",
            "mobbin#last_browsed_platform=ios",
            "mobbin#last_browsed_experience=apps"
        ]
        
        return "; ".join(cookies)
    
    def browse_apps_by_category(self, category: str, platform: str = "ios", page_size: int = 20):
        """
        按类别浏览应用
        """
        print(f"浏览类别 '{category}' 的应用...")
        
        base_url = "https://mobbin.com/api/browse"
        url = f"{base_url}/{platform}/apps"
        
        params = {
            "filterOperator": "and",
            "appCategories[]": category,
            "pageSize": str(page_size),
            "sortBy": "publishedAt"
        }
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://mobbin.com",
            "Referer": "https://mobbin.com/",
            "User-Agent": self._headers["User-Agent"],
            "Cookie": self._build_cookie()
        }
        
        return self._make_request("GET", url, headers=headers, params=params)

    def get_latest_apps(self, limit: int = 20, platform: str = "ios"):
        """
        获取最新的 App 列表 - 使用 Mobbin 的实际 API
        """
        print(f"正在获取最新的 {limit} 个 App...")
        
        base_url = "https://mobbin.com/api/browse"
        url = f"{base_url}/{platform}/apps"
        
        params = {
            "pageSize": str(limit),
            "sortBy": "publishedAt"
        }
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://mobbin.com",
            "Referer": "https://mobbin.com/",
            "User-Agent": self._headers["User-Agent"],
            "Cookie": self._build_cookie()
        }
        
        return self._make_request("GET", url, headers=headers, params=params)

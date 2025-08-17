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
            response = requests.request(method, url, headers=headers, params=params, json=json_data, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            if e.response is not None:
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
        搜索 App (需要先登录)。
        此为最终验证版，使用 PostgREST 的数据表过滤方式进行搜索。
        """
        print(f"正在使用【最终验证版数据表过滤】接口搜索 App: '{query}'...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
        # 使用 websearch_to_tsquery (wfts) 来实现更符合用户预期的搜索功能。
        # wfts 会自动处理空格，并将它们解释为 AND 连接符，但为了明确，我们手动替换。
        # 例如，搜索 "time schedule" 会被转换为 "time & schedule"，
        # 这意味着会查找同时包含 "time" 和 "schedule" 的应用。
        # Use " & " between terms so Supabase interprets it as a logical AND
        processed_query = " & ".join(query.split())
        params = {
            "select": "*",
            "platform": f"eq.{platform}",
            "appName": f"wfts.{processed_query}"
        }
        return self._make_request("GET", url, headers=self._headers, params=params)

    def get_latest_apps(self, limit: int = 20, platform: str = "ios"):
        """
        获取最新的 App 列表，不进行搜索。
        """
        print(f"正在获取最新的 {limit} 个 App...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
        params = {
            "select": "*",
            "platform": f"eq.{platform}",
            "order": "updatedAt.desc",
            "limit": str(limit)
        }
        return self._make_request("GET", url, headers=self._headers, params=params)

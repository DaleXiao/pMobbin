# mobbin_client.py

import requests

class MobbinClient:
    """
    最终版 Mobbin API 客户端。
    通过 API Key 初始化，并提供程序化登录和数据获取功能。
    所有请求都统一发往 Supabase 的真实后端地址，以绕过所有网络问题。
    """
    def __init__(self, api_key: str, access_token: str = None):
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
        if self.access_token:
            self._headers["Authorization"] = f"Bearer {self.access_token}"

    def _make_request(self, method: str, url: str, headers: dict, params: dict = None, json_data: dict = None):
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
        print(f"正在向邮箱 {email} 发送登录验证码...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/auth/v1/otp"
        payload = {"email": email, "create_user": False}
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        response_json = self._make_request("POST", url, headers=headers, json_data=payload)
        return response_json is not None

    def verify_otp_and_login(self, email: str, otp: str):
        print(f"正在使用邮箱 {email} 和验证码进行验证...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/auth/v1/verify"
        payload = {"type": "email", "email": email, "token": otp}
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        data = self._make_request("POST", url, headers=headers, json_data=payload)
        if data and data.get("access_token"):
            self.access_token = data["access_token"]
            self._update_authorization_header()
            print("登录成功！Access Token 已获取并设置到客户端。")
            return data
        else:
            print("验证失败或响应中未找到 access_token。")
            return None

    def search_apps(self, query: str, platform: str = "ios"):
        print(f"正在使用【最终验证版数据表过滤】接口搜索 App: '{query}'...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
        processed_query = query.replace(' ', '|')
        params = {
            "select": "*",
            "platform": f"eq.{platform}",
            "appName": f"fts.{processed_query}"
        }
        return self._make_request("GET", url, headers=self._headers, params=params)

    # --- 新增的测试方法 ---
    def get_latest_apps(self, limit: int = 20, platform: str = "ios"):
        """
        获取最新的 App 列表，不进行搜索。
        """
        print(f"正在获取最新的 {limit} 个 App...")
        url = "https://ujasntkfphywizsdaapi.supabase.co/rest/v1/apps"
        params = {
            "select": "*",
            "platform": f"eq.{platform}",
            "order": "updatedAt.desc",  # 按更新时间降序排序
            "limit": str(limit)
        }
        return self._make_request("GET", url, headers=self._headers, params=params)

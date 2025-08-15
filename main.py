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

# --- API 路由定义 ---
@app.get("/", summary="服务健康检查")
def read_root():
    return {"status": "ok", "message": "Mobbin API Service is running."}

@app.post("/api/login/send-otp", summary="第一步：发送登录验证码")
def send_otp(request_data: OtpRequest):
    success = client.send_login_otp(request_data.email)
    if not success:
        raise HTTPException(status_code=500, detail="发送验证码失败，请检查邮箱地址或查看服务日志。")
    return {"message": f"验证码已成功发送至 {request_data.email}，请查收。"}

@app.post("/api/login/verify", summary="第二步：验证并完成登录")
def verify_and_login(request_data: VerifyRequest):
    session_data = client.verify_otp_and_login(request_data.email, request_data.otp)
    if not session_data:
        raise HTTPException(status_code=401, detail="验证失败，验证码错误或已过期。")
    return {"message": "登录成功！服务现在已认证，可以开始请求数据。"}

@app.get("/api/search", summary="搜索 App (需要先登录)")
def search_for_apps(q: str):
    if not client.access_token:
        raise HTTPException(status_code=403, detail="禁止访问：客户端未登录或登录已过期，请先调用 /api/login/* 接口。")
    
    results = client.search_apps(q)
    if results is None:
        raise HTTPException(status_code=500, detail="搜索失败或上游服务器（Mobbin）错误。")
    return results

# --- 新增的测试接口 ---
@app.get("/api/latest-apps", summary="获取最新 App 列表 (需要先登录)")
def get_latest_apps(limit: int = 20):
    """
    不进行搜索，只获取最新更新的 App 列表，用于测试基础数据权限。
    """
    if not client.access_token:
        raise HTTPException(status_code=403, detail="禁止访问：客户端未登录或登录已过期，请先调用 /api/login/* 接口。")

    apps = client.get_latest_apps(limit)
    if apps is None:
        raise HTTPException(status_code=500, detail="获取最新列表失败或上游服务器（Mobbin）错误。")
    return apps

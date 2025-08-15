# Dockerfile

# 使用一个轻量的 Python 官方镜像作为基础
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制并安装依赖
# 先只复制 requirements.txt 文件以利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有应用代码到工作目录
COPY . .

# 声明服务将要监听的端口
EXPOSE 8000

# 定义容器启动时要执行的命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

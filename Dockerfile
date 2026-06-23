FROM python:3.10-slim

# 安装依赖
RUN apt-get update && apt-get install -y wget supervisor

# 下载 DeepLX
WORKDIR /app
RUN wget https://github.com/OwO-Network/DeepLX/releases/latest/download/deeplx_linux_amd64 -O /app/DeepLX && chmod +x /app/DeepLX

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY app.py .
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 启动
CMD ["/usr/bin/supervisord"]

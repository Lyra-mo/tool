FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY app.py .

# 启动
CMD streamlit run app.py --server.port=10000 --server.address=0.0.0.0

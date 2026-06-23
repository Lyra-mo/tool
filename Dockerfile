FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY app.py .

# 使用 exec 形式，并绑定到 Render 的 PORT 环境变量
CMD exec streamlit run app.py --server.port=$PORT --server.address=0.0.0.0

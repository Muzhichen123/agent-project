FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目
COPY . .

# Streamlit 端口
EXPOSE 8501

# 启动
CMD ["streamlit", "run", "utils/app_web.py", "--server.address=0.0.0.0"]

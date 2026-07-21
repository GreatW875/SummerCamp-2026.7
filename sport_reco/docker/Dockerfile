# 运动分析 Web 应用 - Docker 镜像
FROM python:3.10-slim

LABEL maintainer="sport_reco" \
      description="运动分析Web应用"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY environment.yml .

# 安装 Python 依赖（非 conda 环境使用 pip）
RUN pip install --no-cache-dir -r <(grep -A100 "pip:" environment.yml | grep "^\s\+-" | sed 's/^\s\+- //') && \
    pip install --no-cache-dir \
    flask==3.0 \
    flask-socketio==5.3 \
    gevent==24.2 \
    gevent-websocket==0.10 \
    numpy==1.26 \
    pandas==2.2 \
    scipy==1.12 \
    scikit-learn==1.5 \
    matplotlib==3.8 \
    pyyaml==6.0 \
    joblib==1.4

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p logs data/raw data/processed ssl

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "-m", "src.app", "--host", "0.0.0.0", "--port", "5000"]

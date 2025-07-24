# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

# 构建参数：是否使用国内镜像
ARG USE_CN_MIRROR=false

# 设置清华镜像源（可选）
RUN if [ "$USE_CN_MIRROR" = "true" ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        chromium \
        fonts-noto-cjk \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -c /usr/local \
    && ln -s /usr/local/bin/uv /usr/bin/uv

# 设置工作目录
WORKDIR /app

# 复制依赖定义文件
COPY pyproject.toml poetry.lock* ./

# 安装依赖（根据是否使用国内源）
RUN if [ "$USE_CN_MIRROR" = "true" ]; then \
        uv pip install --system --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple; \
    else \
        uv pip install --system --no-cache-dir; \
    fi

# 复制项目代码
COPY . .

# ---- 运行阶段 ----
FROM python:3.11-slim

# 构建参数再次声明
ARG USE_CN_MIRROR=false

# 使用清华 APT 源（运行镜像）
RUN if [ "$USE_CN_MIRROR" = "true" ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -ms /bin/bash appuser

# 复制构建产物
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    DRISSIONPAGE_BROWSER_PATH=/usr/bin/chromium \
    DRISSIONPAGE_DOWNLOAD_PATH=/usr/bin

# 切换工作目录和用户
WORKDIR /app
USER appuser

# 启动命令
CMD ["python", "main.py"]

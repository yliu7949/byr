# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

# 镜像元数据
LABEL org.opencontainers.image.source=https://github.com/yliu7949/byr
LABEL org.opencontainers.image.description="Automates latest free-torrent discovery from byr.pt and hands them off to qBittorrent."
LABEL org.opencontainers.image.licenses=GPL-3.0

# 安装基本工具
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# 复制依赖定义文件
COPY pyproject.toml ./

# 使用官方源安装依赖
RUN uv pip install --system --compile -e . \
    --index-url https://pypi.org/simple

# 复制业务代码
COPY . .

# ---- 运行阶段 ----
FROM python:3.11-slim

# 安装 Chromium + 字体
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -ms /bin/bash appuser

# 拷贝已安装好的 Python 运行环境和代码
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

ENV PYTHONUNBUFFERED=1 \
    DRISSIONPAGE_BROWSER_PATH=/usr/bin/chromium \
    DRISSIONPAGE_DOWNLOAD_PATH=/usr/bin

WORKDIR /app
USER appuser

CMD ["python", "main.py"]
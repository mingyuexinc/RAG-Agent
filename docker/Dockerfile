# uv 官方 slim 镜像（含 uv 二进制 + CPython 3.10）。
# 从 alpine 切换到 bookworm-slim：alpine(musl) 与 uv 存在已知兼容问题
# (gnu/musl 不匹配、musl wheel 缺失导致 Pillow/faiss-cpu 源码编译失败)。
FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

WORKDIR /app

# 系统编译依赖：faiss-cpu / Pillow 等在部分平台无预编译 wheel 时需源码编译。
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# uv 性能优化：预编译字节码 + 复制模式（避免硬链接跨设备问题）。
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# 先拷依赖清单（pyproject.toml + uv.lock），利用层缓存加速重建。
# 构建上下文为项目根（见 docker-compose.yml 的 build: ..）。
COPY pyproject.toml uv.lock ./
# --frozen: 严格按 lock 安装，不重新解析；--no-dev: 跳过开发工具链；
# --no-install-project: 项目本身 package=false，无需安装自身。
RUN uv sync --frozen --no-dev --no-install-project

# 再拷源码（变更频率高于依赖，单独一层）。
COPY . .

EXPOSE 8000

# app/main.py 中 uvicorn.run("api.routes:app", ...) 要求工作目录包含 app/ 子目录。
# 方案 A（改工作目录）：
# CMD ["uv", "run", "--directory", "app", "uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
# 方案 B（加 --pythonpath）：
CMD ["uv", "run", "uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000", "--pythonpath", "app"]

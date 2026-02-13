# ============================================================
# AutoControl-Scientist API — Multi-stage Docker Build
# ============================================================

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements-api.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-api.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim

LABEL maintainer="AutoControl-Scientist Team"
LABEL description="AutoControl-Scientist API Server"

WORKDIR /app

# 安装 curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖
COPY --from=builder /install /usr/local

# 复制应用代码（排除 GUI 和不需要的文件）
COPY core/ ./core/
COPY agents/ ./agents/
COPY prompts/ ./prompts/
COPY api/ ./api/
COPY api_main.py .
COPY llm_client.py .
COPY global_context.py .
COPY config_manager.py .
COPY output_manager.py .

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 创建输出目录并设置权限
RUN mkdir -p /app/output /app/config && chown -R appuser:appuser /app

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]

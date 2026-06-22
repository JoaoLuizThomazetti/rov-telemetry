FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY telemetry/pyproject.toml telemetry/uv.lock* ./
COPY helpers/ /helpers/
RUN uv sync --frozen --no-dev
COPY telemetry/main.py .
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]

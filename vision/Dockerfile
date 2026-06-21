FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY vision/pyproject.toml vision/uv.lock* ./
RUN uv sync --frozen --no-dev
COPY helpers/ ./helpers/
COPY vision/samples/ ./samples/
COPY vision/main.py vision/marine.pt ./
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
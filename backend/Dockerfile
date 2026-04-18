FROM python:3.11-slim as builder

WORKDIR /app

RUN pip install --no-cache-dir hatch

COPY pyproject.toml ./

RUN hatch env create

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wireguard-tools \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local/share/hatch/env/virtual /root/.local/share/hatch/env/virtual
ENV PATH="/root/.local/share/hatch/env/virtual/backend/lib/python3.11/bin:$PATH"

COPY src ./src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

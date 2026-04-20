FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wireguard-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "sqlalchemy>=2.0.0" \
    "asyncpg>=0.29.0" \
    "psycopg2-binary>=2.9.9" \
    "alembic>=1.13.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "bcrypt>=4.0.0,<4.1.0" \
    "python-multipart>=0.0.6" \
    "jinja2>=3.1.2" \
    "httpx>=0.26.0" \
    "cryptography>=42.0.0" \
    "apscheduler>=3.10.0"

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000

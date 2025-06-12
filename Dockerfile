FROM python:3.12.2-slim-bookworm AS builder

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gcc \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel
RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock /app/

RUN uv sync --no-dev --extra prod

FROM python:3.12.2-slim-bookworm

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

RUN apt-get update && apt-get install -y --no-install-recommends \
        libxext6 \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local /usr/local
# Assuming uv installs packages in a standard site-packages location within the Python installation
# If uv uses a different location, you might need to adjust this.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY . /app

CMD ["uv", "run", "manage.py", "runserver", "8000"]
# =============================================================================
# Stage 1: System dependencies (Firefox + geckodriver)
# =============================================================================
FROM python:3.11-slim AS system-deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG GECKODRIVER_VERSION=v0.35.0

# install Firefox and geckodriver with apt cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    firefox-esr \
    && wget -q "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" -O /tmp/geckodriver.tar.gz \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin \
    && rm /tmp/geckodriver.tar.gz \
    && chmod +x /usr/local/bin/geckodriver

# =============================================================================
# Stage 2: Python dependencies (cached by requirements.txt hash)
# =============================================================================
FROM system-deps AS python-deps

WORKDIR /usr/src/app

COPY requirements.txt ./

# pip cache persists between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt

# =============================================================================
# Stage 3: Runtime
# =============================================================================
FROM python-deps AS runtime

WORKDIR /usr/src/app
ENV PYTHONPATH=/usr/src/app

COPY alembic.ini ./
COPY alembic ./alembic
COPY main.py ./
COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

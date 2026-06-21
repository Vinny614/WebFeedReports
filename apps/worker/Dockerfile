# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install third-party deps first for better layer caching.
COPY apps/worker/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Install local packages without re-resolving their deps.
COPY packages/shared /packages/shared
COPY packages/platform /packages/platform
COPY packages/domain /packages/domain
RUN pip install --no-deps /packages/shared /packages/platform /packages/domain

# App source.
COPY apps/worker/app /app/app

CMD ["python", "-m", "app.main"]

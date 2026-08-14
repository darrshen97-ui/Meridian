# Meridian Financial — container image for Google Cloud Run.
# The React interface is prebuilt into app/static and committed, so this image
# needs no Node toolchain.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_DIR=/tmp/meridian \
    DATABASE_URL=sqlite:////tmp/meridian/meridian.db \
    COOKIE_SECURE=true

WORKDIR /app

# Dependencies first so application edits don't invalidate the layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini serve.py ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY sample_data ./sample_data

# Run as a non-root user; /tmp holds the ephemeral database.
RUN useradd --create-home --uid 1001 meridian \
    && mkdir -p /tmp/meridian \
    && chown -R meridian:meridian /app /tmp/meridian
USER meridian

EXPOSE 8080
CMD ["python", "serve.py"]

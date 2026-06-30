# API-only backend image. The frontend is now its own nginx container, so this
# image ships no React build — main.py only serves the SPA when frontend/dist
# exists, which it does NOT here, so this serves the API alone.
#
# NOTE: the root ./Dockerfile (combined FE+BE image) is kept for Railway.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install Python deps first so this layer caches unless deps change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code. frontend/dist and node_modules are excluded via
# .dockerignore, so no SPA is bundled — this stays an API-only image.
COPY . .

EXPOSE 8000

# Railway provides $PORT; default to 8000 locally
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# ---- Stage 1: build the React SPA ----
FROM node:20-bookworm-slim AS frontend

WORKDIR /app/frontend

# Install JS deps first so this layer caches unless deps change
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the production bundle into /app/frontend/dist
COPY frontend/ ./
RUN npm run build


# ---- Stage 2: Python app that serves the API + built SPA ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install Python deps first so this layer caches unless deps change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Bring in the compiled SPA from the frontend stage. main.py serves this
# from frontend/dist when the directory exists.
COPY --from=frontend /app/frontend/dist ./frontend/dist

EXPOSE 8000

# Railway provides $PORT; default to 8000 locally
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

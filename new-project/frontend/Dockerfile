# ---- Stage 1: build the React SPA ----
FROM node:20-bookworm-slim AS build

WORKDIR /app

# Install JS deps first so this layer caches unless deps change
COPY package.json package-lock.json ./
RUN npm ci

# Build the production bundle into /app/dist
COPY . .
RUN npm run build


# ---- Stage 2: serve the static build with nginx ----
FROM nginx:1.27-alpine

# SPA-aware config: unknown paths fall back to index.html for client-side routing.
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

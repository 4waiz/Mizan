# Multi-stage build for the Mizan React (Vite) workflow UI.
# Stage 1 builds the static bundle; stage 2 serves it via nginx and
# proxies /api -> the backend service (same-origin, mirroring the dev proxy).

# --- build ---
FROM node:20-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# VITE_API_BASE stays empty: the bundle calls /api same-origin and nginx proxies it.
RUN npm run build

# --- serve ---
FROM nginx:1.27-alpine AS serve
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

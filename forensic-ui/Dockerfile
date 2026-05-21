# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
# Use npm install until package-lock.json is committed; switch to npm ci after.
RUN npm install --prefer-offline

COPY . .
RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:alpine AS final

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

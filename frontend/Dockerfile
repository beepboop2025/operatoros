# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# ── Development stage ─────────────────────────────────────────────────────────
FROM node:20-alpine AS development

WORKDIR /app

# VITE_API_URL is consumed by vite.config.ts at runtime in dev mode.
ENV VITE_API_URL=${VITE_API_URL:-http://localhost:8000}

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── Production stage ─────────────────────────────────────────────────────────
FROM nginx:alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Custom nginx config for SPA
COPY --from=build /app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

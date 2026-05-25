# Multi-stage Dockerfile for Watchfy (Optimized)
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --frozen-lockfile

# Copy source
COPY . .

# Build for production
RUN npm run build

# Production stage
FROM nginx:alpine

# Create non-root user
RUN addgroup -g 1001 -S nginx && \
    adduser -u 1001 -S nginx -G nginx

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy optimized nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 555 /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

USER nginx

CMD ["nginx", "-g", "daemon off;"]
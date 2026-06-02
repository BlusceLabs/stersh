# Watchfy frontend — production multi-stage build.
# Build the Astro SSR bundle, then ship only the production deps
# + dist/ in a slim runtime image.

# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests first so this layer caches when only source changes.
COPY package.json package-lock.json ./
COPY packages/animations/package.json ./packages/animations/
COPY packages/design-tokens/package.json ./packages/design-tokens/
COPY packages/shared-types/package.json ./packages/shared-types/
COPY packages/ui-primitives/package.json ./packages/ui-primitives/

RUN npm ci

# Now copy the rest of the source.
COPY astro.config.mjs tailwind.config.mjs tsconfig.json tsconfig.svelte-check.json ./
COPY src ./src
COPY packages ./packages

ENV NODE_ENV=production
RUN npm run build

# ── Stage 2: runtime ───────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    PORT=4321 \
    HOST=0.0.0.0

# Copy production-only node_modules from the builder.
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules

# Copy the build output.
COPY --from=builder /app/dist ./dist

# Run as the unprivileged "node" user that ships with the base image.
USER node

EXPOSE 4321

# Health-check hits the SSR server; works without a backend.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:4321/health || exit 1

CMD ["node", "./dist/server/entry.mjs"]

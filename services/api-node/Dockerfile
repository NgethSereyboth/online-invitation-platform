# Node service image (S2). Separate from deploy/Dockerfile, which builds the
# Python backend. Pinned to the repo's .nvmrc major (22).
FROM node:22-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json ./
# No lifecycle scripts: the lockfile is the only thing that decides what runs.
RUN npm ci --ignore-scripts --omit=dev --no-audit --no-fund

FROM node:22-alpine

WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080 \
    HOST=0.0.0.0 \
    EINVITE_WEB_ROOT=/web
# The mirror is mounted read-only at /web; it is the same tree Python serves,
# so both runtimes must see one copy of the built pages.
COPY --from=deps /app/node_modules ./node_modules
COPY package.json app.mjs server.mjs ./
COPY lib ./lib

USER node
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||8080)+'/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.mjs"]

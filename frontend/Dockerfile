FROM node:22-alpine AS builder

WORKDIR /app/frontend

ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/frontend/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

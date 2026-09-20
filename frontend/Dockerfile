# Três estágios:
#   dev     -> vite dev server com hot reload (usado pelo docker-compose.override.yml)
#   build   -> gera o dist/
#   runtime -> nginx servindo o dist/ (imagem final, padrão)

FROM node:22-alpine AS dev

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM node:22-alpine AS build

ARG GIT_COMMIT=unknown
ARG BUILD_TIME
ENV GIT_COMMIT=${GIT_COMMIT} \
    BUILD_TIME=${BUILD_TIME}

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --spider -q http://127.0.0.1/ || exit 1

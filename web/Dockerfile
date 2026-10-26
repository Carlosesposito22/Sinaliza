# Contexto de build: a raiz do repositório (ver docker-compose.yml), porque o
# download dos sinais do VLibras lê data/vocabulary.json.
FROM node:22-alpine AS build

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

# Sinais do vocabulário, do dicionário do VLibras (precisa de internet só aqui).
# Camada própria: só refaz quando o vocabulário, a tabela de glosas ou o script mudam.
COPY data/vocabulary.json /app/data/vocabulary.json
COPY web/scripts ./scripts
COPY web/src/vlibras-glosses.json ./src/vlibras-glosses.json
RUN npm run signs

COPY web/ .

ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/web/dist /usr/share/nginx/html

EXPOSE 80

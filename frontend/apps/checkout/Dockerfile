FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
COPY apps ./apps
COPY shared ./shared
RUN npm ci
RUN npm run build --workspace=@base-grid/checkout
FROM nginx:1.28-alpine
COPY nginx/app.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/checkout/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1

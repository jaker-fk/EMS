# ---------- 构建阶段 ----------
FROM node:20-alpine AS build
WORKDIR /app

# 国内网络可换成官方源：--build-arg NPM_REGISTRY=https://registry.npmjs.org
ARG NPM_REGISTRY=https://registry.npmmirror.com

# 只先拷贝依赖清单；npm ci 严格按 lock 文件安装，保证构建可复现
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --registry=${NPM_REGISTRY}

COPY . .
RUN npm run build

# ---------- 运行阶段 ----------
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

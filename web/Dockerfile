FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_PUBLIC_API_SECRET=AIRVIP
ENV NEXT_PUBLIC_API_BASE=https://air-api-43va3skqta-uc.a.run.app
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/out ./out
CMD ["serve", "out", "-l", "tcp://0.0.0.0:8080"]

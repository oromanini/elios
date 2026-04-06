FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Recebe a URL do workflow
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
ENV REACT_APP_BACKEND_URL=$VITE_API_URL

# Agora o build vai ler a variável acima
RUN npm run build

FROM node:20-alpine

WORKDIR /app
RUN npm install -g serve

COPY --from=builder /app/build ./build

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "serve -s build -l ${PORT}"]

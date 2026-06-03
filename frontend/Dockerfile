FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --ignore-engines
COPY . .
ARG VITE_TURN_URL
ARG VITE_TURN_USER
ARG VITE_TURN_PASS
ENV VITE_TURN_URL=$VITE_TURN_URL
ENV VITE_TURN_USER=$VITE_TURN_USER
ENV VITE_TURN_PASS=$VITE_TURN_PASS
RUN yarn build
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
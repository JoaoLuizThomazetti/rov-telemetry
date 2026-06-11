FROM rust:slim AS builder
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN CARGO_HTTP_MULTIPLEXING=false cargo build --release

FROM debian:bookworm-slim
WORKDIR /data
COPY --from=builder /app/target/release/mavlink-bridge /usr/local/bin/mavlink-bridge
CMD ["mavlink-bridge"]
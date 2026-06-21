FROM rust:slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main(){}" > src/main.rs \
    && cargo build --release \
    && rm -rf src

COPY src/ ./src/
RUN touch src/main.rs && CARGO_HTTP_MULTIPLEXING=false cargo build --release

FROM debian:bookworm-slim
WORKDIR /data
COPY --from=builder /app/target/release/recorder /usr/local/bin/recorder
CMD ["recorder"]
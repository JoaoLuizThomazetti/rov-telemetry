FROM rust:slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /data
COPY --from=builder /app/target/release/simulator /usr/local/bin/simulator
CMD ["simulator"]
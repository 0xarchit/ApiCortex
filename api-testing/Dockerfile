FROM rust:1.94-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY Cargo.toml Cargo.lock ./
RUN mkdir -p src && echo 'pub mod executor; pub mod models;' > src/lib.rs \
    && echo 'fn main() {}' > src/main.rs \
    && touch src/executor.rs src/models.rs \
    && cargo build --release \
    && rm -rf src

COPY src ./src
RUN touch src/main.rs src/lib.rs && cargo build --release

FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libssl3 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --no-create-home appuser

WORKDIR /app

COPY --from=builder /build/target/release/api-testing ./api-testing

RUN chown appuser:appuser ./api-testing && chmod 500 ./api-testing

USER appuser

ENV BIND_ADDR=0.0.0.0:9090

EXPOSE 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["sh", "-c", "port=${BIND_ADDR##*:}; curl -sf http://127.0.0.1:${port}/health || exit 1"]

ENTRYPOINT ["./api-testing"]

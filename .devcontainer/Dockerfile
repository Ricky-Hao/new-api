FROM golang:1.26.10-bookworm@sha256:5de7c99eb78ca5e515a4c340235d0955ec5964a5071c492c15503d7c267da473 AS go
FROM oven/bun:1.4.4-debian@sha256:93d5032fe06d163427822dc1598f420363759bb18155c9cc90eb1be05a64a19e AS bun
FROM node:24-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS node
FROM mcr.microsoft.com/devcontainers/base:1-bookworm@sha256:ce2e9e611939e611b737362c045bb6d3449bb3efb84898525d724aace1737b90

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash build-essential ca-certificates curl git openssh-client \
        pkg-config python3 python3-venv ripgrep sqlite3 tar xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=go /usr/local/go /usr/local/go
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun
COPY --from=node /usr/local/bin/node /usr/local/bin/node

# /workspaces is the persistent project volume in Coder.
ENV PATH="/usr/local/go/bin:${PATH}" \
    GOCACHE="/workspaces/.cache/new-api/go-build" \
    GOMODCACHE="/workspaces/.cache/new-api/go-mod" \
    BUN_INSTALL_CACHE_DIR="/workspaces/.cache/new-api/bun"

USER vscode

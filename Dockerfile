# Force x86_64 — PyATS/unicon only ships x86 wheels
# Runs under Rosetta on Apple Silicon Macs
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies (no lock file, so no --locked)
RUN uv sync --all-extras --no-dev

# Runtime stage
FROM --platform=linux/amd64 python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1

# openssh-client needed for pexpect SSH to CML console server
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

# CML connection (override at runtime)
ENV CML_URL=https://cml.host.internal
ENV CML_VERIFY_SSL=false

# Device credentials for console access — pass at runtime:
#   -e DEVICE_USERNAME=cisco -e DEVICE_PASSWORD=cisco -e DEVICE_ENABLE_PASSWORD=cisco

# HTTP transport config — server.py reads these from env
ENV TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=9001

EXPOSE 9001

ENTRYPOINT ["/app/entrypoint.sh"]

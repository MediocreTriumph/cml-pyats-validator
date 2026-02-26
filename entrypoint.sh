#!/bin/bash
set -e

# Transport defaults to stdio; set TRANSPORT=streamable-http for Docker/HTTP mode
# Host/port read from env vars HOST and PORT (defaults: 0.0.0.0:9001)
# server.py reads these from env if not passed as CLI args
exec cml-pyats-validator "$@"

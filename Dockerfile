FROM ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 AS uv-bin
FROM ghcr.io/obot-platform/mmmcp:v0.1.3@sha256:b014e3678fd9f24130119bcfb774f44e913a729ca6d42d21463cad690f17910c AS mmmcp-bin

FROM cgr.dev/chainguard/wolfi-base:latest

USER root

RUN apk upgrade --no-cache && \
    apk add --no-cache python3 && \
    mkdir -p /home/user && chown 1000:1000 /home/user

COPY --from=uv-bin /uv /uvx /usr/local/bin/
COPY --from=mmmcp-bin /usr/local/bin/mmmcp /usr/local/bin/mmmcp

WORKDIR /app
ENV HOME=/home/user

RUN mkdir -p /app/src && chown -R 1000:1000 /app

COPY src/ ./src
COPY LICENSE .
COPY main.py .
COPY pyproject.toml uv.lock ./

ENV UV_CACHE_DIR=/app/.cache/uv

USER 1000

RUN uv sync --frozen --python /usr/bin/python3 --no-cache

USER root

RUN cat > /mmmcp.yaml <<'CONFIG'
servers:
  - name: WordPress
    command: /app/.venv/bin/python
    args: [/app/main.py]
    env:
      HOME: /home/user
      WORDPRESS_SITE: ${WORDPRESS_SITE}
      WORDPRESS_USERNAME: ${WORDPRESS_USERNAME}
      WORDPRESS_PASSWORD: ${WORDPRESS_PASSWORD}
CONFIG
RUN chown 1000:1000 /mmmcp.yaml

USER 1000

# mmmcp serves MCP requests at both / and /mcp; existing clients use /mcp.
ENTRYPOINT ["mmmcp"]

CMD ["--listen", ":8099", "--config", "/mmmcp.yaml"]

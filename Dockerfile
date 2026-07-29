# Keep the Python build environment, package manager, and Nanobot runtime independently patched.
FROM cgr.dev/chainguard/python@sha256:7406826ac06aa5e5b9b010c82b3f56aed62946c7fb5c7d4dfba012b88a6570c5

COPY --from=ghcr.io/obot-platform/nanobot@sha256:2cdc20cff957ecfe4a0409209a78a2f1968849cf4f61ee59c60862d55b33e4ff /usr/local/bin/nanobot /usr/local/bin/nanobot
COPY --from=ghcr.io/astral-sh/uv@sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105 /uv /uvx /usr/local/bin/

WORKDIR /app

USER root

RUN mkdir -p /app/src && chown -R 65532:65532 /app

COPY src/ ./src
COPY .python-version .
COPY LICENSE .
COPY main.py .
COPY pyproject.toml .

USER 65532

RUN uv sync

USER root

RUN cat > /nanobot.yaml <<'EOF'
publish:
  mcpServers: [server]

mcpServers:
  server:
    command: uv
    args: [run, python, /app/main.py]
    env:
      UV_PROJECT: /app
      WORDPRESS_SITE: ${WORDPRESS_SITE}
      WORDPRESS_USERNAME: ${WORDPRESS_USERNAME}
      WORDPRESS_PASSWORD: ${WORDPRESS_PASSWORD}
EOF

RUN chown 65532:65532 /nanobot.yaml

ENTRYPOINT ["nanobot"]

CMD ["run", "--listen-address", ":8099", "-e", "WORDPRESS_SITE", "-e", "WORDPRESS_USERNAME", "-e", "WORDPRESS_PASSWORD", "/nanobot.yaml"]

USER 65532

FROM ghcr.io/obot-platform/nanobot:v0.0.91@sha256:2cdc20cff957ecfe4a0409209a78a2f1968849cf4f61ee59c60862d55b33e4ff

WORKDIR /app

USER root

RUN mkdir -p /app/src && chown -R 1000:1000 /app

COPY src/ ./src
COPY .python-version .
COPY LICENSE .
COPY main.py .
COPY pyproject.toml .

USER 1000

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

RUN chown 1000:1000 /nanobot.yaml

ENTRYPOINT ["nanobot"]

CMD ["run", "--listen-address", ":8099", "-e", "WORDPRESS_SITE", "-e", "WORDPRESS_USERNAME", "-e", "WORDPRESS_PASSWORD", "/nanobot.yaml"]

USER 1000

FROM ghcr.io/obot-platform/mcp-images-phat:main

WORKDIR /app

RUN mkdir /app/src

COPY src/ ./src
COPY .python-version .
COPY LICENSE .
COPY main.py .
COPY pyproject.toml .

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

RUN chown 1000 /nanobot.yaml

ENTRYPOINT ["nanobot"]

CMD ["run", "--listen-address", ":8099", "-e", "WORDPRESS_SITE", "-e", "WORDPRESS_USERNAME", "-e", "WORDPRESS_PASSWORD", "/nanobot.yaml"]

USER 1000

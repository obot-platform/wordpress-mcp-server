FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM ghcr.io/obot-platform/mmmcp:v0.2.0@sha256:4ecdceee76e6066e00bf023ae4c1fb3b80551669ee127d39418dceeace963caf AS python-base

USER root
# Release images pin OS packages; allow patched versions when adding Python.
RUN sed -i -E 's/^([^=<>~]+)=.*/\1/' /etc/apk/world && \
    apk upgrade --no-cache && \
    apk add --no-cache python-3.11
WORKDIR /app

FROM python-base AS dependencies
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-cache --python /usr/bin/python3.11

FROM python-base
COPY --from=dependencies /app/.venv /app/.venv
COPY src/ ./src/
COPY main.py LICENSE mmmcp.yaml ./

EXPOSE 8099
USER 1000:1000
ENTRYPOINT ["/usr/local/bin/mmmcp"]
CMD ["-config", "/app/mmmcp.yaml", "-transport", "http"]

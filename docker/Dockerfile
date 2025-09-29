FROM python:3.12-slim

# Set SHELL with pipefail for safer pipe operations
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 必要なフォントをインストール（存在するパッケージを自動選択し、Candidate にピン留め）
# hadolint は式展開を解釈できない場合がありますが、実際には =version で固定しています
# hadolint ignore=DL3008
RUN set -eux; \
    apt-get update; \
    PKG="fonts-noto-cjk"; \
    CANDIDATE=$(apt-cache policy "$PKG" | sed -n 's/\s\+Candidate: //p'); \
    if [ -z "$CANDIDATE" ] || [ "$CANDIDATE" = "(none)" ]; then \
        PKG="fonts-noto-cjk-extra"; \
        CANDIDATE=$(apt-cache policy "$PKG" | sed -n 's/\s\+Candidate: //p'); \
    fi; \
    test -n "$CANDIDATE"; \
    apt-get install -y --no-install-recommends "$PKG=$CANDIDATE"; \
    rm -rf /var/lib/apt/lists/*

# This makes print statements show up in the logs API
ENV PYTHONUNBUFFERED=1

# This allows code to access ~ and not default to /, which may not be accessible
ENV HOME=/opt/code

WORKDIR /opt/code

EXPOSE 8080

FROM python:3.12-slim

# 必要なフォントをインストール
# hadolint ignore=DL3008
# バージョン固定はしない運用のため
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# This makes print statements show up in the logs API
ENV PYTHONUNBUFFERED=1

# This allows code to access ~ and not default to /, which may not be accessible
ENV HOME=/opt/code

WORKDIR /opt/code

EXPOSE 8080

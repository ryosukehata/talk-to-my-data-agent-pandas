FROM datarobot/mirror_chainguard_datarobot.com_python-fips:3.12-dev

USER root

RUN apk add --no-cache fontconfig font-noto-cjk \
    && fc-cache -f

# This makes print statements show up in the logs API
ENV PYTHONUNBUFFERED=1

# This allows code to access ~ and not default to /, which may not be accessible
ENV HOME=/opt/code

# Add .local/bin to PATH for user-installed packages (gunicorn, flask, etc.)
ENV PATH=/opt/code/.local/bin:$PATH

WORKDIR /opt/code

# Install 'uv' for fast package resolution and 'poetry' for dependency management.
# This enables support for pyproject.toml based configurations as part of APP-5254.
RUN python -m pip install --no-cache poetry uv

EXPOSE 8080

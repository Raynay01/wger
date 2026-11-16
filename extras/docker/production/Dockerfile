#
# Docker image for wger
#
# Please consult the README for usage
#
# Note: you MUST build this image from the project's root!
# docker build -f extras/docker/production/Dockerfile --tag wger/server .
#
# To run the container consult https://github.com/wger-project/docker

##########
# Builder
##########
# Pinned by date and digest, so a rebuild gets the same system packages
ARG BASE_IMAGE=wger/base:2026-11-01@sha256:c3c1be750620478f93f16deb7c2d0f3dce9d08e5c3d820ecc7adff6468ae41e3

# Node for the CSS and JS build, from the official image instead of a remote
# setup script: Node 24 LTS, glibc build, pinned by version and digest
ARG NODE_IMAGE=node:24.22.3-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54

FROM ${NODE_IMAGE} AS node

FROM ${BASE_IMAGE} AS builder
ARG DEBIAN_FRONTEND=noninteractive

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && apt update \
    && apt install --no-install-recommends -y \
      build-essential \
      python3-dev \
      python3-wheel \
      pkg-config \
      libcairo2-dev \
      libjpeg8-dev \
      libwebp-dev \
      libpq-dev \
      rustc \
      cargo \
      unzip \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/src/wger/core/static


#
# Build the python wheels
#
WORKDIR /root/src

# Build the application
COPY pyproject.toml uv.lock README.md /root/src/
COPY wger/version.py wger/__init__.py /root/src/wger/

# NB: this was a workound for https://github.com/rust-lang/cargo/issues/8719
# which was needed when building rust dependencies for arm/v7. If we re-enable
# the arch, we will probably need to add it again (same for demo, etc).
# --mount=type=tmpfs,target=/root/.cargo
# Exactly the versions of uv.lock, checked against their hashes. A proxy that
# re-signs HTTPS needs its CA as the optional build secret build_ca
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then \
      export PIP_CERT=/run/secrets/build_ca SSL_CERT_FILE=/run/secrets/build_ca NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; \
    fi \
    && pip3 install --break-system-packages --no-cache-dir uv==0.11.32 \
    && uv export --frozen --format requirements-txt --group docker --no-emit-project --no-dev \
      > /root/requirements.txt \
    && pip3 wheel \
      --no-cache-dir \
      --require-hashes \
      --wheel-dir /wheels \
      -r /root/requirements.txt \
    && pip3 wheel --no-cache-dir --no-deps --wheel-dir /wheels . \
    && npm install -g sass@1.108.2

# Fetch the JS and CSS files.
# For the react-components npm package, we fetch it manually, extract it and move
# it into node_modules to keep the size of the docker image small(er). Yes, this
# is hacky and there's probably a better way.
COPY package.json package-lock.json ./
COPY wger/core/static /root/src/wger/core/static
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then \
      export PIP_CERT=/run/secrets/build_ca SSL_CERT_FILE=/run/secrets/build_ca NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; \
    fi \
    && npm ci --production \
    && npm run build:css:sass \
    && PACKAGE_NAME="@wger-project/react-components" \
    && PACKAGE_VERSION=$(node -p "require('./package.json').devDependencies['$PACKAGE_NAME']") \
    && TARBALL=$(npm pack ${PACKAGE_NAME}@${PACKAGE_VERSION}) \
    && mkdir -p node_modules/${PACKAGE_NAME} \
    && tar -xzf ${TARBALL} -C node_modules/${PACKAGE_NAME} --strip-components=1

########
# Final
########
FROM ${BASE_IMAGE} AS final
LABEL org.opencontainers.image.authors="wger team <hello@wger.de>"
ARG DOCKER_DIR=./extras/docker/production
ARG BUILD_COMMIT
ARG BUILD_DATE

ENV PATH="/home/wger/.local/bin:$PATH"
ENV APP_BUILD_COMMIT=$BUILD_COMMIT
ENV APP_BUILD_DATE=$BUILD_DATE
ENV PYTHONPATH=/home/wger/src
ENV DJANGO_SETTINGS_MODULE=settings.main

WORKDIR /home/wger/src
EXPOSE 8000

# Set up the application
COPY --chown=wger:wger . /home/wger/src
COPY --chown=wger:wger --from=builder /root/src/node_modules /home/wger/src/node_modules
COPY --chown=wger:wger --from=builder /root/src/wger/core/static/bootstrap-compiled.css /home/wger/src/wger/core/static/bootstrap-compiled.css
COPY --chown=wger:wger --from=builder /root/src/wger/core/static/bootstrap-compiled.css.map /home/wger/src/wger/core/static/bootstrap-compiled.css.map
COPY ${DOCKER_DIR}/entrypoint.sh /home/wger/entrypoint.sh
COPY ${DOCKER_DIR}/celery/start-beat /start-beat
COPY ${DOCKER_DIR}/celery/start-worker /start-worker
COPY ${DOCKER_DIR}/celery/start-flower /start-flower
RUN chmod +x /home/wger/entrypoint.sh \
    && chmod +x /start-beat \
    && chmod +x /start-worker \
    && chmod +x /start-flower \
    && chown wger:wger /home/wger/src

USER wger

# Note: unsetting DJANGO_SETTINGS_MODULE here since we only need django to
#        compile the message files
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip3 install --break-system-packages --no-cache-dir --user /wheels/* \
    && pip3 install --break-system-packages --user . \
    && mkdir -p ~/media ~/private-media ~/static ~/beat ~/db \
    && cd wger \
    && env -u DJANGO_SETTINGS_MODULE django-admin compilemessages

CMD ["/home/wger/entrypoint.sh"]

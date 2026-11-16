# ClamAV for servers the official image does not cover: clamav/clamav is built
# for amd64 only, this one also runs on arm64 (e.g. the Ampere servers of
# Oracle Cloud Always Free). Same port (3310) and database volume.
FROM docker.io/ubuntu:24.04@sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8

RUN apt-get update \
    && apt-get install -y --no-install-recommends clamav-daemon clamav-freshclam ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    # Listen on TCP for the server, stay in the foreground for Docker
    && sed -i -e '/^LocalSocket/d' -e '/^LocalSocketGroup/d' -e '/^LocalSocketMode/d' \
        -e '/^Foreground/d' -e '/^TCPSocket/d' -e '/^TCPAddr/d' /etc/clamav/clamd.conf \
    && printf 'TCPSocket 3310\nTCPAddr 0.0.0.0\nForeground true\n' >> /etc/clamav/clamd.conf \
    # The limits of the official image: chat videos go up to 50 MB
    && sed -i -e '/^StreamMaxLength/d' -e '/^MaxFileSize/d' -e '/^MaxScanSize/d' /etc/clamav/clamd.conf \
    && printf 'StreamMaxLength 100M\nMaxFileSize 100M\nMaxScanSize 400M\n' >> /etc/clamav/clamd.conf \
    && mkdir -p /run/clamav && chown clamav:clamav /run/clamav /var/lib/clamav

COPY entrypoint.sh /usr/local/bin/clamav-entrypoint
COPY healthcheck.sh /usr/local/bin/clamdcheck.sh

EXPOSE 3310
ENTRYPOINT ["clamav-entrypoint"]

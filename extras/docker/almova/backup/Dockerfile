# Backup tools: pg_dump of the same PostgreSQL version as the database, and age
# (built from source at a pinned version; Go checks the module against sum.golang.org).
# Runs extras/backup/backup.sh (see extras/backup/README.md).
ARG GO_IMAGE=golang:1.27.4-alpine@sha256:0a5f7fe796599ff487605987432e7619ae45beeb2fba4c2ce0b907879932aebf
ARG POSTGRES_IMAGE=postgres:18.7-alpine@sha256:b6972e1115a4ff8eba5d7f7d19184926d1e16d7d1136ae1e1a7ebf286da0f015

FROM ${GO_IMAGE} AS age
# A proxy that re-signs HTTPS needs its CA as the optional build secret build_ca
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi \
    && CGO_ENABLED=0 GOBIN=/out go install filippo.io/age/cmd/...@v1.3.2

FROM ${POSTGRES_IMAGE}
COPY --from=age /out/age /out/age-keygen /usr/local/bin/
COPY extras/backup/backup.sh extras/backup/restore.sh extras/backup/test-restore.sh /usr/local/bin/
USER postgres
WORKDIR /backups
ENTRYPOINT ["/usr/local/bin/backup.sh"]

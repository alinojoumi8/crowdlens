ARG CADDY_BASE
FROM ${CADDY_BASE}
# The upstream binary requests NET_BIND_SERVICE. This stage uses high ports only.
RUN setcap -r /usr/bin/caddy && chown 1000:1000 /data /config
USER 1000:1000

#!/bin/sh
# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Punto de entrada: si hay CAs corporativas montadas en $EXTRA_CA_CERTS_DIR
# (por defecto /certs), las anexa al bundle de certifi (lo usa httpx/LiteLLM/
# Anthropic) y al almacén del sistema (openssl/requests). Luego ejecuta el
# comando recibido. Así los certificados se montan como volumen y no se hornean
# en la imagen.
set -e

CERT_DIR="${EXTRA_CA_CERTS_DIR:-/certs}"

if [ -d "$CERT_DIR" ]; then
    CERTIFI_PATH="$(python -c 'import certifi; print(certifi.where())' 2>/dev/null || true)"
    found=0
    for f in "$CERT_DIR"/*.pem "$CERT_DIR"/*.crt; do
        [ -e "$f" ] || continue
        found=1
        # certifi (bundle que usa httpx por defecto)
        if [ -n "$CERTIFI_PATH" ]; then
            cat "$f" >> "$CERTIFI_PATH"
        fi
        # almacén del sistema (openssl / requests)
        base="$(basename "$f")"
        cp "$f" "/usr/local/share/ca-certificates/${base%.*}.crt"
    done
    if [ "$found" -eq 1 ]; then
        update-ca-certificates >/dev/null 2>&1 || true
        echo "[entrypoint] CAs adicionales cargadas desde $CERT_DIR"
    fi
fi

exec "$@"

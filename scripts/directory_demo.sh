#!/usr/bin/env bash
# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Demo del Agent Directory de AGNTCY: publica los registros OASF de los dos
# agentes (supervisor y detector) en un directorio local y muestra cómo un
# agente puede DESCUBRIR a otro por sus capacidades (skill / dominio / nombre).
#
# Uso:
#   ./scripts/directory_demo.sh
#
# Requisitos: Docker. No necesitas instalar dirctl: se usa la imagen
# ghcr.io/agntcy/dir-ctl vía docker compose (perfil "directory").

set -euo pipefail

DIR_SVC="directory"
DIRCTL="/dirctl"
ADDR="localhost:8888"
RECORDS_DIR="/oasf/agents"
COMPOSE="docker compose"

# Ejecuta dirctl dentro del contenedor del directorio.
dirctl() { $COMPOSE exec -T "$DIR_SVC" "$DIRCTL" "$@" --server-addr "$ADDR"; }

echo "==> 1) Arrancando el Agent Directory (perfil 'directory')..."
$COMPOSE --profile directory up -d "$DIR_SVC"

echo "==> Esperando a que el directorio esté listo..."
for _ in $(seq 1 30); do
    if $COMPOSE exec -T "$DIR_SVC" "$DIRCTL" info --server-addr "$ADDR" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo
echo "==> 2) Publicando (push) los registros OASF de cada agente..."
DET_CID="$(dirctl push "$RECORDS_DIR/noc-detector-agent.json" 2>&1 | awk -F': ' '/CID/{print $2}')"
SUP_CID="$(dirctl push "$RECORDS_DIR/noc-supervisor-agent.json" 2>&1 | awk -F': ' '/CID/{print $2}')"
echo "    Detector   -> CID: ${DET_CID:-<error>}"
echo "    Supervisor -> CID: ${SUP_CID:-<error>}"

echo
echo "==> 3) DESCUBRIMIENTO por capacidades (así un agente encuentra a otro):"

echo
echo "    [a] ¿Quién sabe monitorear la red?  (skill: performance_monitoring)"
dirctl search --skill "*performance_monitoring*" 2>&1 | sed 's/^/        /'

echo
echo "    [b] ¿Quién orquesta/coordina agentes? (skill: agent_coordination)"
dirctl search --skill "*agent_coordination*" 2>&1 | sed 's/^/        /'

echo
echo "    [c] ¿Qué agentes operan en el dominio de red? (domain: network_operations)"
dirctl search --domain "*network_operations*" 2>&1 | sed 's/^/        /'

echo
echo "==> 4) Detalle de un registro descubierto (pull por CID):"
if [ -n "${DET_CID:-}" ]; then
    dirctl pull "$DET_CID" 2>&1 | head -c 600 | sed 's/^/        /'
    echo
fi

echo
echo "==> Listo. Para apagar el directorio:"
echo "    docker compose --profile directory down"

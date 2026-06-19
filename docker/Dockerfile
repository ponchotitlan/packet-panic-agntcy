# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY common ./common
COPY config ./config
COPY detector ./detector
COPY supervisor ./supervisor
# Registros OASF: fuente del Agent Directory para descubrir agentes en runtime.
COPY oasf ./oasf

RUN pip install --no-cache-dir .

# Entrypoint: anexa CAs corporativas montadas (volumen) al bundle de certifi y
# al almacén del sistema en tiempo de ejecución, sin hornearlas en la imagen.
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# El comando se define en docker-compose por servicio (detector / supervisor).
CMD ["python", "-m", "supervisor.main"]

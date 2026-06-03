FROM python:3.10-slim

# Instalace potřebných nástrojů
RUN apt-get update && apt-get install -y \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Nastavení pracovní složky
WORKDIR /hasici_app

# Kopírování requirements a instalace závislostí
COPY ./scripts/hasici_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování celé aplikace
COPY ./scripts/hasici_app /hasici_app

# Zkopírování entrypoint skriptu
COPY ./scripts/hasici_app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

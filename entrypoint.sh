#!/bin/bash

cd /hasici_app

case "$ROLE" in
  hasici_app)
    echo "[entrypoint] Adding Git server to known_hosts..."
    mkdir -p ~/.ssh
    ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null

    echo "[entrypoint] Pulling latest code from Git..."
    if git pull --quiet; then
        echo "[entrypoint] Git pull successful."
    else
        echo "[entrypoint] Git pull failed – continuing anyway."
    fi

    echo "[entrypoint] Installing Python package (editable)..."
    pip install -e . || echo "Editable install failed – continuing anyway"
    ;;

  *)
    echo "[entrypoint] Unknown ROLE: $ROLE – continuing anyway"
    ;;
esac

echo "[entrypoint] Starting Flask app on port 5100..."
exec flask run --host=0.0.0.0 --port=5100

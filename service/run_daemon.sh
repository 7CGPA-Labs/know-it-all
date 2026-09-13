#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=5055

echo "[*] Initializing AI Web Research Daemon..."

if command -v podman &> /dev/null; then
    ENGINE="podman"
elif command -v docker &> /dev/null; then
    ENGINE="docker"
else
    ENGINE="venv"
fi

if [ "$ENGINE" = "podman" ] || [ "$ENGINE" = "docker" ]; then
    echo "[*] Using container engine: $ENGINE"
    IMAGE_NAME="gedit-research-daemon:latest"
    
    echo "[*] Building container image..."
    $ENGINE build -t "$IMAGE_NAME" "$SCRIPT_DIR"
    
    echo "[*] Launching container daemon on port $PORT..."
    $ENGINE run -d --rm \
        --name gedit-research-daemon \
        -p "127.0.0.1:$PORT:5055" \
        "$IMAGE_NAME"
        
    echo "[+] Daemon running in container via $ENGINE on http://localhost:$PORT"
else
    echo "[!] No container engine found (docker/podman). Using venv micro-daemon fallback."
    VENV_DIR="$SCRIPT_DIR/venv"
    if [ ! -d "$VENV_DIR" ]; then
        if python3 -m venv "$VENV_DIR" 2>/dev/null; then
            echo "[*] Created venv using python3 -m venv"
        elif python3 -m virtualenv "$VENV_DIR" 2>/dev/null; then
            echo "[*] Created venv using python3 -m virtualenv"
        else
            echo "[!] Failed to create virtualenv"
            exit 1
        fi
    fi
    
    echo "[*] Installing/verifying daemon dependencies..."
    "$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt" || true
    
    echo "[*] Launching Python daemon server..."
    "$VENV_DIR/bin/python" "$SCRIPT_DIR/server.py" &
    echo "[+] Daemon running via venv micro-daemon on http://localhost:$PORT"
fi

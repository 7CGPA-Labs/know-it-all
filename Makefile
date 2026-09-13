.PHONY: all build-container download-model install-plugin clean-legacy test help

PLUGIN_DIR ?= $(HOME)/.local/share/gedit/plugins
PYTHON := $(shell which python3)

all: help

build-container:
	@echo "[*] Building AI Research Daemon container..."
	@if command -v podman > /dev/null; then \
		podman build -t gedit-research-daemon:latest service/; \
	elif command -v docker > /dev/null; then \
		docker build -t gedit-research-daemon:latest service/; \
	else \
		echo "[!] Neither docker nor podman found."; exit 1; \
	fi

download-model:
	@echo "[*] Downloading Qwen 2.5 0.5B ONNX Model..."
	$(PYTHON) service/download_model.py --output service/models/qwen2.5-0.5b-onnx

install-plugin:
	@echo "[*] Installing Gedit plugin to $(PLUGIN_DIR)..."
	mkdir -p $(PLUGIN_DIR)
	cp -f plugin/research_copilot.plugin $(PLUGIN_DIR)/
	cp -f plugin/research_copilot.py $(PLUGIN_DIR)/
	@echo "[+] Plugin successfully installed! Restart Gedit and enable 'AI Web Research & Markdown Copilot' in Preferences -> Plugins."

clean-legacy:
	@echo "[*] Cleaning up legacy code..."
	rm -rf backend frontends packaging build_output knowitall.deb

test:
	@echo "[*] Running service unit tests..."
	@if [ -f service/venv/bin/python ]; then \
		PYTHONPATH=. service/venv/bin/python service/tests/test_server.py; \
	else \
		PYTHONPATH=. $(PYTHON) -m unittest service/tests/test_server.py; \
	fi

help:
	@echo "Gedit AI Web Research & Markdown Copilot - Build Tooling"
	@echo "Available targets:"
	@echo "  build-container   Build Docker/Podman daemon container image"
	@echo "  download-model    Download Qwen-2.5-0.5B ONNX model weights"
	@echo "  install-plugin    Install Gedit side panel plugin to ~/.local/share/gedit/plugins/"
	@echo "  clean-legacy      Remove obsolete legacy codebase directories"
	@echo "  test              Run unit tests"

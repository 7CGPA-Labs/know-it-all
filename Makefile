.PHONY: all build-container download-model build-plugin install-plugin clean-legacy test help

PLUGIN_DIR ?= $(HOME)/.local/share/gedit/plugins
PYTHON := $(shell which python3)
VALAC ?= valac
CC ?= gcc

CFLAGS ?= -O2 -Wall
VALA_PKGS := --pkg gtk+-3.0 --pkg libpeas-1.0 --pkg libsoup-3.0
GTK_CFLAGS := $(shell pkg-config --cflags gtk+-3.0 libpeas-1.0 libsoup-3.0 gmodule-2.0)
GTK_LIBS := $(shell pkg-config --libs gtk+-3.0 libpeas-1.0 libsoup-3.0 gmodule-2.0)

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
	$(PYTHON) service/download_model.py --output service/models/qwen2.5-0.5b-onnx --quant q4

build-plugin:
	@echo "[*] Compiling Vala plugin research_copilot.vala to C..."
	$(VALAC) -C $(VALA_PKGS) plugin/research_copilot.vala
	@echo "[*] Compiling C source into shared library libresearch_copilot.so..."
	$(CC) -shared -fPIC $(CFLAGS) $(GTK_CFLAGS) -o plugin/libresearch_copilot.so plugin/research_copilot.c $(GTK_LIBS)
	@echo "[+] Vala plugin build successful!"

install-plugin: build-plugin
	@echo "[*] Installing Gedit plugin to $(PLUGIN_DIR)..."
	mkdir -p $(PLUGIN_DIR)
	cp -f plugin/research_copilot.plugin $(PLUGIN_DIR)/
	cp -f plugin/libresearch_copilot.so $(PLUGIN_DIR)/
	@echo "[+] Vala plugin successfully installed! Restart Gedit and enable 'AI Web Research & Markdown Copilot' in Preferences -> Plugins."

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
	@echo "  build-plugin      Compile Vala plugin to native shared library libresearch_copilot.so"
	@echo "  build-container   Build Docker/Podman daemon container image"
	@echo "  download-model    Download Qwen-2.5-0.5B INT4 ONNX model weights"
	@echo "  install-plugin    Install Vala plugin to ~/.local/share/gedit/plugins/"
	@echo "  clean-legacy      Remove obsolete legacy codebase directories"
	@echo "  test              Run unit tests"

.PHONY: all build-daemon build-plugin download-model install-plugin deb clean test help

VALAC ?= valac
CC ?= gcc

CFLAGS ?= -O2 -Wall
VALA_PKGS := --pkg gtk+-3.0 --pkg libpeas-1.0 --pkg libsoup-3.0
GTK_CFLAGS := $(shell pkg-config --cflags gtk+-3.0 libpeas-1.0 libsoup-3.0 gmodule-2.0)
GTK_LIBS := $(shell pkg-config --libs gtk+-3.0 libpeas-1.0 libsoup-3.0 gmodule-2.0)

SOUP_CFLAGS := $(shell pkg-config --cflags glib-2.0 libsoup-3.0)
SOUP_LIBS := $(shell pkg-config --libs glib-2.0 libsoup-3.0)

PLUGIN_DIR ?= $(HOME)/.local/share/gedit/plugins

all: help

build-daemon:
	@echo "[*] Compiling Native C AI Research Daemon..."
	@mkdir -p service/bin
	$(CC) $(CFLAGS) $(SOUP_CFLAGS) -o service/bin/daemon service/src/daemon.c $(SOUP_LIBS)
	@echo "[+] Native C Daemon build successful! (service/bin/daemon)"

build-plugin:
	@echo "[*] Compiling Vala plugin research_copilot.vala to C..."
	$(VALAC) -C $(VALA_PKGS) plugin/research_copilot.vala
	@echo "[*] Compiling C source into shared library libresearch_copilot.so..."
	$(CC) -shared -fPIC $(CFLAGS) $(GTK_CFLAGS) -o plugin/libresearch_copilot.so plugin/research_copilot.c $(GTK_LIBS)
	@echo "[+] Vala plugin build successful! (plugin/libresearch_copilot.so)"

download-model:
	@echo "[*] Triggering POSIX model downloader script..."
	bash service/download_model.sh service/models/qwen2.5-0.5b-onnx

install-plugin: build-plugin
	@echo "[*] Installing Gedit plugin to $(PLUGIN_DIR)..."
	mkdir -p $(PLUGIN_DIR)
	cp -f plugin/research_copilot.plugin $(PLUGIN_DIR)/
	cp -f plugin/libresearch_copilot.so $(PLUGIN_DIR)/
	@echo "[+] Vala plugin successfully installed! Restart Gedit and enable 'AI Web Research & Markdown Copilot' in Preferences -> Plugins."

deb:
	@echo "[*] Generating Debian (.deb) package..."
	bash packaging/build_deb.sh

test: build-daemon
	@echo "[*] Compiling and running native C daemon test suite..."
	$(CC) $(CFLAGS) $(SOUP_CFLAGS) -o service/tests/test_runner service/tests/test_daemon.c $(SOUP_LIBS)
	./service/tests/test_runner

clean:
	@echo "[*] Cleaning build artifacts..."
	rm -rf service/bin plugin/libresearch_copilot.so plugin/research_copilot.c service/tests/test_runner packaging/deb_build knowitall.deb

help:
	@echo "Gedit AI Web Research & Markdown Copilot (100% C/Vala & OpenVINO iGPU)"
	@echo "Available targets:"
	@echo "  build-daemon      Compile native C daemon binary (service/bin/daemon)"
	@echo "  build-plugin      Compile Vala plugin to shared library libresearch_copilot.so"
	@echo "  download-model    Fetch Qwen-2.5-0.5B INT4 ONNX model weights"
	@echo "  install-plugin    Install Vala plugin to ~/.local/share/gedit/plugins/"
	@echo "  deb               Build Debian package knowitall.deb"
	@echo "  test              Compile and execute native C unit test suite"
	@echo "  clean             Remove compiled binaries and package build outputs"

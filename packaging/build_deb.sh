#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/packaging/deb_build"

echo "[*] Cleaning previous deb build artifacts..."
rm -rf "$BUILD_DIR" "$PROJECT_ROOT/knowitall.deb"

echo "[*] Creating Debian package layout..."
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/lib/x86_64-linux-gnu/gedit/plugins"
mkdir -p "$BUILD_DIR/etc/xdg/autostart"
mkdir -p "$BUILD_DIR/usr/share/knowitall"

echo "[*] Building daemon and plugin binaries..."
cd "$PROJECT_ROOT"
make build-daemon
make build-plugin

echo "[*] Copying binary files..."
cp "$PROJECT_ROOT/service/bin/daemon" "$BUILD_DIR/usr/bin/gedit-research-daemon"
cp "$PROJECT_ROOT/service/download_model.sh" "$BUILD_DIR/usr/share/knowitall/download_model.sh"
chmod +x "$BUILD_DIR/usr/share/knowitall/download_model.sh"

cp "$PROJECT_ROOT/plugin/libresearch_copilot.so" "$BUILD_DIR/usr/lib/x86_64-linux-gnu/gedit/plugins/"
cp "$PROJECT_ROOT/plugin/research_copilot.plugin" "$BUILD_DIR/usr/lib/x86_64-linux-gnu/gedit/plugins/"

echo "[*] Generating autostart entry..."
cat << 'EOF' > "$BUILD_DIR/etc/xdg/autostart/gedit-research-daemon.desktop"
[Desktop Entry]
Type=Application
Name=Gedit Research Daemon
Exec=/usr/bin/gedit-research-daemon
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

echo "[*] Generating control file..."
cat << 'EOF' > "$BUILD_DIR/DEBIAN/control"
Package: knowitall
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: 7CGPA Labs <support@7cgpa.com>
Depends: gedit, libgtk-3-0, libpeas-1.0-0, libsoup-3.0-0, curl
Description: Gedit AI Web Research Copilot (C/Vala & OpenVINO iGPU)
 AI-powered web research copilot and live markdown renderer plugin for Gedit,
 accelerated with Intel OpenVINO iGPU Execution Provider.
EOF

echo "[*] Building .deb package..."
dpkg-deb --build "$BUILD_DIR" "$PROJECT_ROOT/knowitall.deb"

echo "[+] Successfully created $PROJECT_ROOT/knowitall.deb"

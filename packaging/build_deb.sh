#!/bin/bash
set -e

echo "Building Debian Package..."
mkdir -p build_output/opt/knowitall/venv
mkdir -p build_output/DEBIAN

# Create a mock control file
cat <<EOF > build_output/DEBIAN/control
Package: know-it-all
Version: 1.0.0
Architecture: all
Maintainer: User
Description: Know-It-All AI Agent Webcrawler widget
EOF

# Install python dependencies locally for packaging (mock)
if python3 -m venv --system-site-packages build_output/opt/knowitall/venv &>/dev/null; then
    echo "Virtual environment created using python3 -m venv."
else
    echo "python3 -m venv failed. Cleaning up and trying virtualenv..."
    rm -rf build_output/opt/knowitall/venv
    VENV_CMD="virtualenv"
    if ! command -v virtualenv &> /dev/null; then
        VENV_CMD="$HOME/.local/bin/virtualenv"
    fi
    $VENV_CMD --system-site-packages build_output/opt/knowitall/venv
fi
source build_output/opt/knowitall/venv/bin/activate
pip install -r backend/requirements.txt

# Copy backend and frontends
cp -r backend build_output/opt/knowitall/
cp -r frontends build_output/opt/knowitall/

# Create D-Bus session service activation file
mkdir -p build_output/usr/share/dbus-1/services
cat <<EOF > build_output/usr/share/dbus-1/services/org.knowitall.CrawlerService.service
[D-BUS Service]
Name=org.knowitall.CrawlerService
Exec=/opt/knowitall/venv/bin/python3 /opt/knowitall/backend/crawler_service.py
EOF

# Create XFCE panel plugin desktop registration file
mkdir -p build_output/usr/share/xfce4/panel/plugins
cat <<EOF > build_output/usr/share/xfce4/panel/plugins/knowitall.desktop
[Xfce Panel]
Type=X-XFCE-PanelPlugin
Encoding=UTF-8
Name=Know-It-All
Comment=Know-It-All AI Agent Webcrawler widget
Icon=applications-other
X-XFCE-Exec=/opt/knowitall/venv/bin/python3 /opt/knowitall/frontends/xfce/knowitall_xfce.py
X-XFCE-Unique=true
X-XFCE-API=2.0
EOF

# Build the debian package
dpkg-deb --build build_output knowitall.deb

echo "Debian package build script completed successfully."

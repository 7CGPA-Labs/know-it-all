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
Description: Semi-AI NLP Webcrawler widget
EOF

# Install python dependencies locally for packaging (mock)
python3 -m venv build_output/opt/knowitall/venv
source build_output/opt/knowitall/venv/bin/activate
pip install -r backend/requirements.txt

# Copy backend
cp -r backend build_output/opt/knowitall/

echo "Debian package build script completed successfully."

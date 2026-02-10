#!/bin/bash
# Install system dependencies for IntelliPal on Ubuntu/Debian Linux
# Run with: sudo ./tools/install_linux_deps.sh

set -e

echo "Installing IntelliPal dependencies for Linux..."

# Detect package manager
if command -v apt-get &> /dev/null; then
    echo "Using apt package manager..."
    apt-get update
    apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        xdotool \
        libxcb-cursor0 \
        libgl1 \
        libxkbcommon0 \
        libegl1 \
        libfontconfig1 \
        libdbus-1-3
elif command -v dnf &> /dev/null; then
    echo "Using dnf package manager..."
    dnf install -y \
        python3 \
        python3-pip \
        xdotool \
        libxcb \
        mesa-libGL \
        libxkbcommon \
        mesa-libEGL \
        fontconfig \
        dbus-libs
elif command -v pacman &> /dev/null; then
    echo "Using pacman package manager..."
    pacman -Sy --noconfirm \
        python \
        python-pip \
        xdotool \
        libxcb \
        mesa \
        libxkbcommon \
        fontconfig \
        dbus
else
    echo "Unsupported package manager. Please install manually:"
    echo "  - python3, python3-venv, python3-pip"
    echo "  - xdotool (for window embedding)"
    echo "  - libxcb, libgl, libxkbcommon, libegl, fontconfig, dbus (for PySide6)"
    exit 1
fi

echo ""
echo "System dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Create a virtual environment: python3 -m venv .venv"
echo "  2. Activate it: source .venv/bin/activate"
echo "  3. Install Python packages: pip install -r requirements.txt"
echo "  4. Run the app: python -m intellipal.main"

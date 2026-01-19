#!/bin/bash

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
LINK_NAME="incode"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=========================================="
echo "   🚀 incode-cli Installer & Fixer"
echo "=========================================="
echo "Project Directory: $PROJECT_DIR"
echo ""

# 1. Update Global Symlink
echo ">>> 🔗 Updating global symlink..."
mkdir -p "$BIN_DIR"
rm -f "$BIN_DIR/$LINK_NAME" # Remove existing symlink or file
ln -s "$PROJECT_DIR/incode" "$BIN_DIR/$LINK_NAME"

if [ -L "$BIN_DIR/$LINK_NAME" ]; then
    echo "✅ Symlink created: $BIN_DIR/$LINK_NAME -> $PROJECT_DIR/incode"
else
    echo "❌ Failed to create symlink!"
    exit 1
fi

# 2. Re-create Virtual Environment
echo ""
echo ">>> 🐍 Re-creating internal virtual environment..."

if [ -d "$VENV_DIR" ]; then
    echo "Removing stale .venv..."
    rm -rf "$VENV_DIR"
fi

echo "Creating new .venv..."
python3.14 -m venv "$VENV_DIR"
# Fallback if python3.14 is not in path, try python3 or python
if [ ! -d "$VENV_DIR" ]; then
    echo "python3.14 not found, trying python3..."
    python3 -m venv "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
   echo "❌ Failed to create virtual environment."
   exit 1
fi

# 3. Install Dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    echo "✅ Dependencies installed."
else
    echo "⚠️  requirements.txt not found! Skipping dependency install."
fi

echo ""
echo "=========================================="
echo "   🎉 Fix Complete! Try running: $LINK_NAME"
echo "=========================================="

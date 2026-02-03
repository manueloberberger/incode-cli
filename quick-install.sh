#!/bin/bash
# One-liner install script for incode-cli
# Usage: curl -sSL https://raw.githubusercontent.com/manueloberberger/incode-cli/main/quick-install.sh | bash

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/manueloberberger/incode-cli.git"
INSTALL_DIR="$HOME/.local/share/incode-cli"

echo ""
echo -e "${BOLD}${BLUE}🚀 Quick Install: incode-cli${NC}"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed"
    exit 1
fi

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo ">>> Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --ff-only --quiet
else
    echo ">>> Cloning repository..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Run installer
echo ">>> Running installer..."
bash install.sh

echo ""
echo -e "${GREEN}${BOLD}✅ Installation complete!${NC}"
echo ""
echo -e "Run with: ${BOLD}incode${NC}"
echo ""

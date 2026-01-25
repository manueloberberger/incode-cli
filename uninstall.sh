#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
LINK_NAME="incode"
VENV_DIR="$PROJECT_DIR/.venv"

echo ""
echo -e "${BOLD}=========================================="
echo "   🗑️  incode-cli Uninstaller"
echo -e "==========================================${NC}"
echo ""

# Remove symlink
if [ -L "$BIN_DIR/$LINK_NAME" ]; then
    echo -e "${YELLOW}>>> Removing global symlink...${NC}"
    rm -f "$BIN_DIR/$LINK_NAME"
    echo -e "${GREEN}✅ Symlink removed${NC}"
else
    echo -e "${YELLOW}⚠️  No symlink found at $BIN_DIR/$LINK_NAME${NC}"
fi

# Remove virtual environment
if [ -d "$VENV_DIR" ]; then
    echo ""
    echo -e "${YELLOW}>>> Removing virtual environment...${NC}"
    rm -rf "$VENV_DIR"
    echo -e "${GREEN}✅ Virtual environment removed${NC}"
else
    echo -e "${YELLOW}⚠️  No virtual environment found${NC}"
fi

# Remove credentials (optional)
echo ""
read -p "Remove credentials and database? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    [ -f "$PROJECT_DIR/.credentials.json" ] && rm -f "$PROJECT_DIR/.credentials.json" && echo -e "${GREEN}✅ Credentials removed${NC}"
    [ -f "$PROJECT_DIR/incode.db" ] && rm -f "$PROJECT_DIR/incode.db" && echo -e "${GREEN}✅ Database removed${NC}"
fi

echo ""
echo -e "${BOLD}${GREEN}=========================================="
echo "   ✅ Uninstallation Complete!"
echo -e "==========================================${NC}"
echo ""
echo -e "To remove the project entirely:"
echo -e "${BOLD}rm -rf $PROJECT_DIR${NC}"
echo ""

#!/bin/bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
LINK_NAME="incode"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_MIN_VERSION="3.9"

# Banner
echo ""
echo -e "${BOLD}${BLUE}=========================================="
echo "   🚀 incode-cli Installer"
echo -e "==========================================${NC}"
echo -e "Project: ${PROJECT_DIR}"
echo ""

# Function to compare version numbers (cross-platform)
version_ge() {
    # Usage: version_ge version1 version2
    # Returns 0 (true) if version1 >= version2
    [ "$1" = "$2" ] && return 0
    
    local IFS=.
    local i ver1=($1) ver2=($2)
    
    # Fill empty positions with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++)); do
        # Fill empty positions with zeros
        if [[ -z ${ver2[i]} ]]; then
            ver2[i]=0
        fi
        # Compare versions
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 0
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 1
        fi
    done
    return 0
}

# Check Python version
echo -e "${BOLD}>>> 🐍 Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    echo -e "   Found: Python ${PYTHON_VERSION}"
    
    # Extract major.minor version
    PYTHON_VER_MAJOR_MINOR=$(echo $PYTHON_VERSION | cut -d. -f1,2)
    
    if ! version_ge $PYTHON_VER_MAJOR_MINOR $PYTHON_MIN_VERSION; then
        echo -e "${RED}❌ Python ${PYTHON_MIN_VERSION}+ required, found ${PYTHON_VERSION}${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Python version OK${NC}"
else
    echo -e "${RED}❌ Python 3 not found. Please install Python ${PYTHON_MIN_VERSION}+${NC}"
    exit 1
fi

# Check if ~/.local/bin is in PATH
echo ""
echo -e "${BOLD}>>> 🔍 Checking PATH configuration...${NC}"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}⚠️  $BIN_DIR is not in your PATH${NC}"
    echo ""
    echo -e "   Add this line to your shell config (~/.zshrc or ~/.bashrc):"
    echo -e "   ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""
    echo -e "   Then reload: ${BOLD}source ~/.zshrc${NC} (or ~/.bashrc)"
    echo ""
    read -p "   Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ PATH configured correctly${NC}"
fi

# Create .local/bin if needed
mkdir -p "$BIN_DIR"

# Create or update symlink
echo ""
echo -e "${BOLD}>>> 🔗 Creating global symlink...${NC}"
if [ -L "$BIN_DIR/$LINK_NAME" ]; then
    OLD_TARGET=$(readlink "$BIN_DIR/$LINK_NAME")
    echo "   Removing old symlink: $OLD_TARGET"
    rm -f "$BIN_DIR/$LINK_NAME"
elif [ -f "$BIN_DIR/$LINK_NAME" ]; then
    echo "   Removing existing file: $BIN_DIR/$LINK_NAME"
    rm -f "$BIN_DIR/$LINK_NAME"
fi

ln -s "$PROJECT_DIR/incode" "$BIN_DIR/$LINK_NAME"

if [ -L "$BIN_DIR/$LINK_NAME" ]; then
    echo -e "${GREEN}✅ Symlink created: $BIN_DIR/$LINK_NAME${NC}"
else
    echo -e "${RED}❌ Failed to create symlink!${NC}"
    exit 1
fi

# Make wrapper script executable
chmod +x "$PROJECT_DIR/incode"

# Create virtual environment
echo ""
echo -e "${BOLD}>>> 🌍 Setting up virtual environment...${NC}"

if [ -d "$VENV_DIR" ]; then
    echo "   Removing existing .venv..."
    rm -rf "$VENV_DIR"
fi

echo "   Creating new .venv..."
$PYTHON_CMD -m venv "$VENV_DIR"

if [ ! -d "$VENV_DIR" ]; then
   echo -e "${RED}❌ Failed to create virtual environment${NC}"
   exit 1
fi

echo -e "${GREEN}✅ Virtual environment created${NC}"

# Install dependencies
echo ""
echo -e "${BOLD}>>> 📦 Installing dependencies...${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --quiet
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    exit 1
fi

# Success message
echo ""
echo -e "${BOLD}${GREEN}=========================================="
echo "   🎉 Installation Complete!"
echo -e "==========================================${NC}"
echo ""
echo -e "Run the application with: ${BOLD}${BLUE}$LINK_NAME${NC}"
echo ""
echo -e "Or use the local wrapper: ${BOLD}${BLUE}./incode${NC}"
echo ""

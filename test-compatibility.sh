#!/bin/bash
# Test script to verify cross-platform compatibility

echo "🧪 Testing incode-cli installation scripts..."
echo ""

# Test 1: Bash syntax
echo "1️⃣  Testing bash syntax..."
for script in install.sh uninstall.sh quick-install.sh; do
    if bash -n "$script" 2>/dev/null; then
        echo "   ✅ $script: Syntax OK"
    else
        echo "   ❌ $script: Syntax error"
        exit 1
    fi
done
echo ""

# Test 2: Check required commands
echo "2️⃣  Checking required commands..."
REQUIRED_CMDS=("bash" "python3" "git" "curl" "ln" "mkdir" "rm")
for cmd in "${REQUIRED_CMDS[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "   ✅ $cmd: Found"
    else
        echo "   ⚠️  $cmd: Not found (may be required)"
    fi
done
echo ""

# Test 3: Detect platform
echo "3️⃣  Platform detection..."
OS="Unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="Windows"
fi
echo "   Platform: $OS"
echo ""

# Test 4: Python version
echo "4️⃣  Python version check..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "   Found: Python $PYTHON_VERSION"
    
    # Check if 3.9+
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
        echo "   ✅ Version OK (3.9+ required)"
    else
        echo "   ⚠️  Version too old (3.9+ required)"
    fi
else
    echo "   ❌ Python 3 not found"
fi
echo ""

# Test 5: Check PATH
echo "5️⃣  PATH configuration..."
BIN_DIR="$HOME/.local/bin"
if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
    echo "   ✅ $BIN_DIR is in PATH"
else
    echo "   ⚠️  $BIN_DIR is NOT in PATH"
    echo "   Add this to your shell config:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo ""

# Test 6: Color support
echo "6️⃣  Terminal color support..."
if [ -t 1 ]; then
    echo -e "   \033[32m✅ Colors supported\033[0m"
else
    echo "   ⚠️  Colors may not be supported"
fi
echo ""

echo "=========================================="
echo "✅ Compatibility check complete!"
echo "=========================================="

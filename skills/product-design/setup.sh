#!/bin/bash
#
# Navigator Product Design Skill - Setup Script
#
# Automatically installs Python dependencies and verifies Figma MCP connection.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh

set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUNCTIONS_DIR="$SKILL_DIR/functions"

echo "=========================================="
echo "Navigator Product Design Skill - Setup"
echo "=========================================="
echo ""

# Step 1: Check Python version
echo "[1/5] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"
echo ""

# Step 2: Create virtual environment (optional but recommended)
echo "[2/5] Setting up Python environment..."
if [ ! -d "$SKILL_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SKILL_DIR/venv"
    echo "✅ Virtual environment created at $SKILL_DIR/venv"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
source "$SKILL_DIR/venv/bin/activate"
echo ""

# Step 3: Install dependencies
echo "[3/5] Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$SKILL_DIR/requirements.txt"
echo "✅ Dependencies installed (mcp>=1.2.1)"
echo ""

# Step 4: Verify Figma Desktop is running
echo "[4/5] Checking Figma Desktop status..."
if command -v lsof &> /dev/null; then
    if lsof -i :3845 &> /dev/null; then
        echo "✅ Figma MCP server detected (port 3845)"
    else
        echo "⚠️  Figma MCP server not detected"
        echo "    Please ensure:"
        echo "    1. Figma Desktop app is running"
        echo "    2. MCP server enabled: Figma → Preferences → Enable local MCP Server"
        echo "    3. You are logged into Figma"
        echo ""
        echo "    Setup will continue, but MCP features won't work until Figma is running."
    fi
else
    echo "⚠️  Cannot check port (lsof not available)"
    echo "    Please manually verify Figma Desktop is running"
fi
echo ""

# Step 5: Test MCP connection
echo "[5/5] Testing Figma MCP connection..."
python3 "$FUNCTIONS_DIR/check_mcp_connection.py" 2>&1
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Ensure Figma Desktop is running"
echo "  2. Enable MCP: Figma → Preferences → Enable local MCP Server"
echo "  3. Try the skill: \"Review this Figma design: [URL]\""
echo ""
echo "To activate the virtual environment manually:"
echo "  source $SKILL_DIR/venv/bin/activate"
echo ""
echo "Documentation:"
echo "  - SKILL.md: Skill usage guide"
echo "  - functions/figma_mcp_client.py: MCP client API"
echo ""

# Navigator Product Design Skill - Installation Guide

Quick setup guide for the product-design skill with Figma MCP integration.

---

## Prerequisites

### Required

1. **Python 3.10+**
   ```bash
   python3 --version  # Should be 3.10 or higher
   ```

2. **Figma Desktop App**
   - Download: https://www.figma.com/downloads/
   - Must be running during design reviews

3. **Figma Account**
   - Free or paid account
   - Logged into Figma Desktop

### Optional (Enhanced Features)

- **Figma Enterprise** - For Code Connect mappings (automatic component detection)
- **Tailwind CSS** - For design token integration
- **Storybook** - For visual regression testing

---

## Installation Methods

### Method 1: Automatic Setup (Recommended)

Run the automated setup script:

```bash
cd skills/product-design
./setup.sh
```

This will:
1. ✅ Check Python version (3.10+ required)
2. ✅ Create virtual environment
3. ✅ Install dependencies (`mcp>=1.2.1`)
4. ✅ Verify Figma Desktop is running
5. ✅ Test MCP connection

**Expected output**:
```
==========================================
Navigator Product Design Skill - Setup
==========================================

[1/5] Checking Python version...
✅ Python 3.13.7

[2/5] Setting up Python environment...
✅ Virtual environment created

[3/5] Installing Python dependencies...
✅ Dependencies installed (mcp>=1.2.1)

[4/5] Checking Figma Desktop status...
✅ Figma MCP server detected (port 3845)

[5/5] Testing Figma MCP connection...
✅ Successfully connected to Figma MCP server
   Found 6 tools:
     - get_design_context
     - get_variable_defs
     - get_code_connect_map
     - get_screenshot
     - get_metadata
     - create_design_system_rules

==========================================
✅ Setup Complete!
==========================================
```

---

### Method 2: Manual Installation

If the automatic script fails or you prefer manual setup:

#### Step 1: Install Python Dependencies

```bash
cd skills/product-design

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Enable Figma MCP Server

1. Open **Figma Desktop** app
2. Go to **Figma → Preferences** (macOS) or **File → Settings** (Windows/Linux)
3. Find "**Enable local MCP Server**" option
4. Toggle **ON**
5. You should see confirmation: "MCP server running at http://127.0.0.1:3845/mcp"

#### Step 3: Verify Connection

```bash
cd functions
python3 check_mcp_connection.py
```

**Expected output**:
```
✅ Successfully connected to Figma MCP server
   Found 6 tools:
     - get_design_context
     - get_variable_defs
     - ...
```

---

## Troubleshooting

### "Figma Desktop not running or MCP not enabled"

**Symptoms**:
```
❌ Figma Desktop not running or MCP not enabled
   Could not connect to Figma Desktop MCP server.
```

**Solutions**:

1. **Check Figma is running**:
   ```bash
   # macOS
   ps aux | grep Figma

   # Should show Figma processes
   ```

2. **Enable MCP server**:
   - Figma → Preferences → Enable local MCP Server
   - Look for confirmation message

3. **Verify port is open**:
   ```bash
   curl http://127.0.0.1:3845/mcp

   # Should return JSON response (even if error)
   # Example: {"jsonrpc":"2.0","error":{"code":-32001,"message":"Invalid sessionId"},"id":null}
   ```

4. **Check Figma version**:
   - MCP requires Figma Desktop v116.0.0+
   - Update if necessary: Figma → Help → Check for Updates

---

### "MCP SDK not installed"

**Symptoms**:
```
ImportError: MCP SDK not installed. Install with: pip install mcp
```

**Solutions**:

1. **Activate virtual environment** (if using):
   ```bash
   source skills/product-design/venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python3 -c "import mcp; print(mcp.__version__)"
   # Should print: 1.2.1 or higher
   ```

---

### "Python 3.10+ required"

**Symptoms**:
```
❌ Python 3.10+ required (found 3.9.6)
```

**Solutions**:

1. **Install Python 3.10+**:
   ```bash
   # macOS (Homebrew)
   brew install python@3.13

   # Ubuntu/Debian
   sudo apt install python3.13

   # Windows
   # Download from python.org
   ```

2. **Use specific Python version**:
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate
   ```

---

### "Port 3845 already in use"

**Symptoms**:
- Figma MCP server won't start
- Connection errors

**Solutions**:

1. **Check what's using port 3845**:
   ```bash
   lsof -i :3845
   ```

2. **Kill conflicting process**:
   ```bash
   # If another process is using the port
   kill -9 <PID>
   ```

3. **Restart Figma Desktop**:
   - Quit Figma completely
   - Restart app
   - Re-enable MCP server

---

## Verifying Installation

### Quick Test

```bash
cd skills/product-design/functions
python3 -c "
import asyncio
from figma_mcp_client import get_figma_variables

async def test():
    try:
        # This will use currently selected node in Figma
        vars = await get_figma_variables()
        print(f'✅ Connected! Found {len(vars)} variables')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"
```

### Full Test

```bash
cd skills/product-design
./setup.sh
```

---

## What Gets Installed

### Python Packages

```txt
mcp>=1.2.1          # Official MCP SDK for Figma integration
anyio>=4.0.0        # Async I/O (transitive dependency)
httpx>=0.25.0       # HTTP client (transitive dependency)
pydantic>=2.0.0     # Data validation (transitive dependency)
```

### File Structure After Installation

```
skills/product-design/
├── venv/                           # Virtual environment (created)
│   ├── bin/
│   ├── lib/
│   └── ...
├── functions/
│   ├── figma_mcp_client.py        # MCP client wrapper ✨ NEW
│   ├── check_mcp_connection.py     # Connection test ✨ NEW
│   ├── design_analyzer.py         # Existing functions (to be refactored)
│   └── ...
├── requirements.txt                # Dependencies ✨ NEW
├── setup.sh                        # Setup script ✨ NEW
├── INSTALL.md                      # This file ✨ NEW
└── SKILL.md                        # Skill documentation
```

---

## Next Steps

After successful installation:

1. **Try the skill**:
   ```
   User: "Review this Figma design: https://figma.com/file/..."
   ```

2. **Read documentation**:
   - `SKILL.md` - Complete skill guide
   - `functions/figma_mcp_client.py` - API documentation

3. **Set up design system** (optional):
   ```bash
   mkdir -p .agent/design-system/reviews
   touch .agent/design-system/design-tokens.json
   touch .agent/design-system/ui-kit-inventory.json
   ```

---

## Uninstalling

To remove the skill:

```bash
cd skills/product-design

# Remove virtual environment
rm -rf venv

# Disable MCP server in Figma
# Figma → Preferences → Disable local MCP Server
```

---

## Support

### Documentation

- **Skill Guide**: `SKILL.md`
- **MCP Client API**: `functions/figma_mcp_client.py`
- **Figma MCP Docs**: https://help.figma.com/hc/en-us/articles/32132100833559

### Common Issues

- **Connection errors**: Ensure Figma Desktop running and MCP enabled
- **Import errors**: Activate virtual environment: `source venv/bin/activate`
- **Version errors**: Upgrade Python to 3.10+

### Reporting Issues

Open issue at: https://github.com/navigator-plugin/navigator/issues

Include:
- Python version: `python3 --version`
- Figma version: Figma → Help → About Figma
- Error message and full stack trace
- Output from: `python3 functions/check_mcp_connection.py`

---

**Last Updated**: 2025-10-22
**Navigator Version**: 3.3.1
**Skill Version**: 1.0.0
**MCP SDK Version**: 1.2.1+

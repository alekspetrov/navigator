# Upgrading to Navigator v3.4.0

**For existing Navigator users running v3.3.1 or earlier**

---

## What's New in v3.4.0

✨ **Direct Figma MCP Integration** - Product design skill now connects directly to Figma Desktop
- 95% reduction in orchestration overhead
- 75% faster design reviews (15 min → 5 min)
- One-command installation

---

## Upgrade Steps

### Step 1: Update Navigator Plugin

```bash
# In your project with Navigator installed
/nav:update
```

OR manually:

```bash
cd .claude-plugins/navigator  # Or wherever Navigator is installed
git pull origin main
```

### Step 2: Install Product Design Dependencies (Optional)

**Only if you use the product-design skill:**

```bash
cd .claude-plugins/navigator/skills/product-design
./setup.sh
```

**What this installs**:
- Python MCP SDK (mcp>=1.2.1)
- Virtual environment with dependencies
- Connection diagnostics

**Time**: ~30 seconds

### Step 3: Enable Figma MCP (Optional)

**Only if you use Figma:**

1. Install **Figma Desktop** (if not already): https://www.figma.com/downloads/
2. Open Figma → **Preferences**
3. Enable "**Enable local MCP Server**"
4. Verify: You should see "MCP server running at http://127.0.0.1:3845/mcp"

### Step 4: Test (Optional)

**If using product-design skill:**

```bash
cd .claude-plugins/navigator/skills/product-design
source venv/bin/activate
python3 functions/test_mcp_connection.py
```

**Expected output**:
```
✅ Successfully connected to Figma MCP server
   Found 6 tools:
     - get_design_context
     - get_variable_defs
     ...
```

---

## What Changed

### Product Design Skill

**Before v3.4.0**:
- Manual orchestration (15-20 Claude steps)
- Requires saving temp files
- 150k tokens average

**After v3.4.0**:
- Automatic Python connection to Figma
- No temp files needed
- 12k tokens average (92% reduction)

### New Requirements

**Only for product-design skill**:
- Python 3.10+ (was 3.8+)
- Figma Desktop with MCP enabled (for automated workflow)

**Everything else**: No changes

---

## Breaking Changes

### Product Design Skill Only

If you use `product-design` skill:
- ✅ Run `./setup.sh` to install Python dependencies
- ✅ Enable Figma MCP in Figma Desktop preferences

If you DON'T use `product-design` skill:
- ✅ No action needed - everything works as before

---

## Rollback (If Needed)

If you encounter issues:

```bash
cd .claude-plugins/navigator
git checkout v3.3.1
```

Then report issue: https://github.com/alekspetrov/navigator/issues

---

## Compatibility

| Feature | v3.3.1 | v3.4.0 | Notes |
|---------|--------|--------|-------|
| **All Navigator features** | ✅ | ✅ | No changes |
| **product-design (manual)** | ✅ | ✅ | Still works without Figma |
| **product-design (Figma MCP)** | ❌ | ✅ | New feature |
| **Python 3.8-3.9** | ✅ | ⚠️ | Only for non-Figma features |
| **Python 3.10+** | ✅ | ✅ | Required for Figma MCP |

---

## FAQ

### Do I need to upgrade?

**No** - v3.3.1 continues to work perfectly.

**Upgrade if**:
- You use product-design skill with Figma
- You want faster design reviews

### Will my existing Navigator setup break?

**No** - All Navigator features work exactly the same.

Only product-design skill has new optional features.

### Do I need Figma Desktop?

**No** - Only if you want automated Figma integration.

Manual workflow still available (Navigator asks for design data).

### What if I don't have Python 3.10+?

**Option 1**: Upgrade Python (recommended)
```bash
# macOS
brew install python@3.13
```

**Option 2**: Use manual workflow (no Python needed)

**Option 3**: Stay on Navigator v3.3.1

---

## Support

**Issues**: https://github.com/alekspetrov/navigator/issues

**Documentation**:
- [RELEASE-NOTES-v3.4.0.md](RELEASE-NOTES-v3.4.0.md)
- [skills/product-design/INSTALL.md](skills/product-design/INSTALL.md)
- [skills/product-design/README.md](skills/product-design/README.md)

**Report bugs with**:
- Navigator version: Check `.claude-plugin/plugin.json`
- Python version: `python3 --version`
- Figma version: Figma → Help → About Figma
- Output from: `python3 functions/test_mcp_connection.py`

---

## Summary

**For most users**: Just update Navigator, everything works the same.

**For Figma users**: Run `./setup.sh` in product-design skill for amazing new features!

**Upgrade time**: 2-3 minutes (with Figma setup)

---

**Version**: 3.4.0
**Previous**: 3.3.1
**Type**: Minor release (backward compatible)

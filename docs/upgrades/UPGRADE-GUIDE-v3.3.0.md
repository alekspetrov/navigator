# Upgrade Guide: Navigator v3.3.0

**For users upgrading from v3.0, v3.1, or v3.2 to v3.3.0**

---

## Quick Upgrade (2 minutes)

### Step 1: Update Navigator Plugin

```bash
/plugin update navigator
```

Expected output:
```
✅ Navigator updated to v3.3.0
```

### Step 2: Verify Update

```bash
/plugin list
```

Look for:
```
navigator (v3.3.0) - Self-improving Claude Code plugin
```

### Step 3: Update Your Project's CLAUDE.md

```
"Update my CLAUDE.md to latest Navigator version"
```

This preserves your customizations while updating to v3.3.0 patterns.

### Step 4: Verify New Skills Available

The `visual-regression` skill should now auto-invoke. Test it:

```
"Set up visual regression for [ComponentName]"
```

**Done!** Your project is now on v3.3.0.

---

## What's New in v3.3.0

### New Skill: visual-regression

Automates Storybook + Chromatic/Percy/BackstopJS setup.

**Natural Language Invocation:**
- "Set up visual regression for ProfileCard"
- "Add Chromatic to this component"
- "Configure visual regression testing"
- "Create visual tests for Button component"

**What It Does:**
1. Validates project setup (framework, Storybook)
2. Generates Storybook stories with all component variants
3. Creates Chromatic/Percy/BackstopJS configuration
4. Sets up CI/CD workflows (GitHub Actions, GitLab CI, CircleCI)
5. Provides step-by-step setup instructions

**Time Savings:** 2-3 hours → 5 minutes (96% reduction)

---

## Complete Setup After Upgrade

### If You Have Figma Integration (v3.2)

You now have the complete design-to-production pipeline:

**Step 1: Design Handoff** (v3.2 product-design skill)
```
"Review this design from Figma"
```
→ Extracts tokens, maps components, generates plan

**Step 2: Implementation**
→ Build components following plan

**Step 3: Visual Regression** (v3.3 visual-regression skill - NEW)
```
"Set up visual regression for Button, Input, Card"
```
→ Auto-generates stories, configures Chromatic, sets up CI

**Step 4: Continuous Testing**
→ Every PR shows visual diffs automatically

### If You Don't Have Figma Integration

You can still use visual-regression independently:

1. Ensure Storybook is installed:
   ```bash
   npx storybook init  # If not already installed
   ```

2. Use the skill:
   ```
   "Set up visual regression for [ComponentName]"
   ```

---

## Troubleshooting

### Issue: "visual-regression skill not found"

**Cause:** Plugin not fully updated or Claude Code needs restart.

**Fix:**
1. Restart Claude Code completely
2. Verify version:
   ```bash
   /plugin list
   ```
3. Should show `navigator (v3.3.0)`

### Issue: Skill invokes but says "Storybook not found"

**Cause:** Storybook not installed in project.

**Fix:**
```bash
npx storybook init
```

Then retry:
```
"Set up visual regression for [Component]"
```

### Issue: CLAUDE.md update fails

**Cause:** Custom modifications conflict with auto-updater.

**Fix:**
1. Backup your CLAUDE.md:
   ```bash
   cp CLAUDE.md CLAUDE.md.backup
   ```

2. Manually update version references:
   - Find: `v3.2.0` or `3.2.0`
   - Replace with: `v3.3.0` or `3.3.0`

3. Add visual-regression mention after product-design section:
   ```markdown
   **Recommended**: After implementation, set up visual regression testing:
     "Set up visual regression for {{components}}"
   ```

### Issue: "I updated but still see v3.2.0 in /plugin list"

**Cause:** Plugin cache or update didn't complete.

**Fix:**
1. Remove and reinstall:
   ```bash
   /plugin uninstall navigator
   /plugin marketplace add alekspetrov/navigator
   /plugin install navigator
   ```

2. Restart Claude Code

3. Verify:
   ```bash
   /plugin list
   ```

---

## What Changed Under the Hood

### New Files in Navigator Plugin

```
skills/visual-regression/
├── SKILL.md                          # Skill documentation
├── functions/
│   ├── vr_setup_validator.py        # Project validation
│   ├── story_generator.py           # Storybook story generation
│   ├── chromatic_config_generator.py # Config generation
│   └── ci_workflow_generator.py     # CI/CD workflow generation
├── templates/
│   ├── story-template.tsx.j2
│   ├── chromatic-config.json.j2
│   ├── github-workflow.yml.j2
│   ├── gitlab-ci.yml.j2
│   └── storybook-main.js.j2
└── examples/
    ├── simple-component-vr.md
    ├── design-system-vr.md
    └── existing-storybook-vr.md
```

### Updated Files

- `.claude-plugin/plugin.json` → Added visual-regression to skills array
- `skills/product-design/SKILL.md` → Now suggests VR setup after implementation
- `.agent/sops/testing/visual-regression-setup.md` → New SOP for VR workflow

### Template Updates (in your project after CLAUDE.md update)

Your project's CLAUDE.md will include:
- Visual regression skill auto-invocation patterns
- Integration with product-design workflow
- Updated skills count (17 total)

---

## Using Visual Regression After Upgrade

### Example 1: Single Component

```
"Set up visual regression for ProfileCard component"
```

**Generated files:**
- `ProfileCard.stories.tsx` (with all variants)
- `chromatic.config.json`
- `.storybook/main.js` (updated with addon)
- `package.json` (scripts added)
- `.github/workflows/chromatic.yml`

**Next steps (from output):**
```bash
npm install --save-dev chromatic @chromatic-com/storybook
npm run chromatic
```

### Example 2: Multiple Components

```
"Set up visual regression for Button, Input, Card, Modal, Avatar"
```

**Generated:**
- 5 story files (one per component)
- Single shared Chromatic config
- CI workflow optimized for multiple components

### Example 3: After Figma Design Handoff

```
# Step 1: Design handoff (v3.2)
"Review this design from Figma"

# Step 2: Implement components
[Build components following plan]

# Step 3: Visual regression (v3.3 - NEW)
"Set up visual regression for the components from the Figma design"
```

Navigator remembers component names from design handoff context.

---

## Configuration Options

### Choose Your Visual Regression Tool

**Chromatic (default, recommended):**
```
"Set up visual regression with Chromatic"
```

**Percy:**
```
"Set up visual regression with Percy"
```

**BackstopJS (self-hosted):**
```
"Set up visual regression with BackstopJS"
```

Navigator generates appropriate configs for each.

### Choose Your CI Platform

Navigator auto-detects your CI platform from existing files:
- `.github/workflows/` → GitHub Actions
- `.gitlab-ci.yml` → GitLab CI
- `.circleci/config.yml` → CircleCI

To force a specific platform:
```
"Set up visual regression with GitHub Actions"
```

---

## Migration Notes

### Breaking Changes

**None.** v3.3.0 is fully backward compatible with v3.0-3.2.

### Deprecated Features

**None.** All v3.2 features continue to work.

### New Features

- ✅ visual-regression skill
- ✅ Integration with product-design workflow
- ✅ Multi-tool support (Chromatic/Percy/BackstopJS)
- ✅ Multi-framework support (React/Vue/Svelte)
- ✅ Multi-CI support (GitHub/GitLab/CircleCI)

---

## Rollback Instructions

If you need to rollback to v3.2.0:

```bash
/plugin uninstall navigator
/plugin marketplace add alekspetrov/navigator@3.2.0
/plugin install navigator
```

**Note:** You'll lose access to visual-regression skill but all other features remain.

---

## Getting Help

### Documentation

- **Release Notes:** [RELEASE-NOTES-v3.3.0.md](../RELEASE-NOTES-v3.3.0.md)
- **Visual Regression Skill:** `skills/visual-regression/SKILL.md` (in Navigator repo)
- **Visual Regression SOP:** `.agent/sops/testing/visual-regression-setup.md` (created in your project)
- **Examples:** `skills/visual-regression/examples/` (in Navigator repo)

### Common Questions

**Q: Do I need Figma MCP to use visual-regression?**
A: No. visual-regression works independently. Figma MCP (v3.2) is only needed for "Review this design from Figma" feature.

**Q: Do I need Storybook installed?**
A: Yes. If not installed, run `npx storybook init` first.

**Q: Which visual regression tool should I use?**
A: Chromatic is recommended for Storybook integration. Percy for multi-framework. BackstopJS for self-hosted.

**Q: Does this work with existing Storybook setup?**
A: Yes! The skill is non-destructive and preserves existing stories and configs.

**Q: Can I use this with Vue or Svelte?**
A: Yes. Currently supports React (best), Vue, and Svelte.

**Q: How much does Chromatic cost?**
A: Free tier: 5,000 snapshots/month. Paid plans start at $149/month for unlimited.

### Issues

Report issues: https://github.com/alekspetrov/navigator/issues

### Community

- **Discussions:** GitHub Discussions (coming soon)
- **Twitter:** Share your setup with #NavigatorPlugin

---

## Success Checklist

After upgrading to v3.3.0, verify:

- ✅ `/plugin list` shows `navigator (v3.3.0)`
- ✅ CLAUDE.md mentions visual-regression skill
- ✅ `"Set up visual regression for Button"` auto-invokes skill
- ✅ Skill generates stories and configs successfully
- ✅ CI workflow created (if CI platform detected)
- ✅ Documentation updated in `.agent/sops/testing/`

**All checked?** You're ready to use the complete design-to-production pipeline!

---

## What's Next

### v3.4 (Planned Q1 2026)

- Enhanced Figma → Storybook integration
- Design System Dashboard
- Visual Regression Dashboard
- Team collaboration features

### Stay Updated

Watch the repo: https://github.com/alekspetrov/navigator

Star for updates on new features and releases.

---

**Navigator v3.3.0** - Visual Regression Integration
**Upgrade Guide Last Updated:** 2025-10-21
**License:** MIT

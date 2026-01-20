# Migration Guide: v2.x → v3.0

**Navigator v3.0** removes all slash commands in favor of natural language. This guide helps you migrate smoothly.

---

## 🚨 Breaking Changes

### Commands Removed

All `/nav:*` and `/jitd:*` commands have been deleted:

```diff
- /nav:init
- /nav:start
- /nav:doc
- /nav:marker
- /nav:markers
- /nav:compact
- /nav:migrate
- /jitd:* (all backward-compat commands)
```

### Natural Language Only

Navigator v3.0 uses **skills that auto-invoke** based on your intent. Just describe what you want in natural language.

---

## 📋 Command → Natural Language Map

### Session Management

| Old Command (v2.x) | Natural Language (v3.0) |
|-------------------|------------------------|
| `/nav:start` | `"Start my Navigator session"` |
| | `"Load the navigator"` |
| | `"Begin working on this project"` |

**Example**:
```diff
- /nav:start

+ "Start my Navigator session"
```

---

### Initialization

| Old Command (v2.x) | Natural Language (v3.0) |
|-------------------|------------------------|
| `/nav:init` | `"Initialize Navigator in this project"` |
| | `"Set up Navigator documentation structure"` |

**Example**:
```diff
- /nav:init

+ "Initialize Navigator in this project"
```

---

### Documentation

| Old Command (v2.x) | Natural Language (v3.0) |
|-------------------|------------------------|
| `/nav:doc feature TASK-XX` | `"Archive TASK-XX documentation"` |
| | `"Document this completed feature"` |
| `/nav:doc sop debugging [issue]` | `"Create an SOP for debugging [issue]"` |
| | `"Document this solution as a procedure"` |
| `/nav:doc system architecture` | `"Update system architecture documentation"` |

**Example**:
```diff
- /nav:doc feature TASK-45

+ "Archive TASK-45 documentation"
```

---

### Context Management

| Old Command (v2.x) | Natural Language (v3.0) |
|-------------------|------------------------|
| `/nav:marker checkpoint` | `"Create a marker called checkpoint"` |
| | `"Save my progress as checkpoint"` |
| `/nav:markers` | `"Show my markers"` |
| | `"Load a marker"` |
| | `"Clean up old markers"` |
| `/nav:compact` | `"Clear context and preserve markers"` |
| | `"Smart compact"` |

**Example**:
```diff
- /nav:marker feature-complete
- /nav:compact

+ "Create a marker called feature-complete"
+ "Clear context and preserve markers"
```

---

### Migration (Removed)

| Old Command (v2.x) | v3.0 Status |
|-------------------|-------------|
| `/nav:migrate` | **Not needed** - All skills work automatically |

---

## 🔄 Complete Workflow Examples

### Before (v2.x)

```bash
# Start session
/nav:start

# Work on feature
"Implement user authentication"

# Save progress
/nav:marker auth-started

# Complete feature
/nav:doc feature TASK-12

# Clean up
/nav:compact
```

### After (v3.0)

```
# Start session
"Start my Navigator session"

# Work on feature
"Implement user authentication"

# Save progress
"Create a marker called auth-started"

# Complete feature
"Archive TASK-12 documentation"

# Clean up
"Clear context and preserve markers"
```

**Same functionality, simpler syntax!**

---

## 🛠️ Migration Steps

### Step 1: Update Navigator Plugin

```bash
/plugin update navigator
# Restart Claude Code
```

### Step 2: Start Using Natural Language

**No configuration needed!** All skills work immediately.

Try it:
```
"Start my Navigator session"
```

The `nav-start` skill will auto-invoke.

### Step 3: Update Your CLAUDE.md (Optional)

If you customized your project's `CLAUDE.md`, update command references:

**Before**:
```markdown
### Quick Reference
1. Run /nav:start (loads navigator)
2. /nav:doc feature TASK-XX when done
3. /nav:compact to clear context
```

**After**:
```markdown
### Quick Reference
1. "Start my Navigator session" (loads navigator)
2. "Archive TASK-XX documentation" when done
3. "Clear context and preserve markers" to clear context
```

You can use the updated template from:
```
https://github.com/alekspetrov/navigator/blob/main/templates/CLAUDE.md
```

### Step 4: Verify Skills Work

Test each skill with natural language:

```
"Start my Navigator session"
→ nav-start activates ✅

"Create a marker called test"
→ nav-marker activates ✅

"Archive TASK-99 documentation"
→ nav-task activates ✅

"Clear context and preserve markers"
→ nav-compact activates ✅
```

---

## 💡 Tips for Natural Language

### Be Conversational

Skills understand various phrasings:

```
✅ "Start my Navigator session"
✅ "Load the navigator"
✅ "Begin working on this project"
✅ "Initialize my session"
```

All activate `nav-start`.

### Use Action Verbs

```
✅ "Create a marker called checkpoint"
✅ "Archive TASK-45 documentation"
✅ "Show my markers"
✅ "Clear context and preserve markers"
```

Skills detect intent from verbs like "create", "archive", "show", "clear".

### Be Specific When Needed

```
✅ "Create a marker called feature-complete"
   (better than just "marker")

✅ "Archive TASK-45 documentation"
   (better than just "document this")
```

---

## ❓ FAQ

### Q: Do my old projects still work?

**A: Yes!** Projects using v2.x skills work perfectly with v3.0. Skills are unchanged - only commands were removed.

### Q: What if I forget the natural language phrases?

**A: No problem!** Skills are forgiving. Try different phrasings:

- "Start session" → works
- "Load navigator" → works
- "Begin working" → works

The skill descriptions in v3.0 support multiple trigger phrases.

### Q: Can I still use commands?

**A: No.** Commands are completely removed in v3.0. Natural language is the only interface.

If you need commands, stay on v2.3.0 (which is still supported).

### Q: What if a skill doesn't activate?

**A: Try rephrasing:**

```
❌ "Do the start thing"
   (too vague)

✅ "Start my Navigator session"
   (clear intent)
```

If issues persist, check the skill descriptions in `skills/*/SKILL.md`.

### Q: Are there any new features besides natural language?

**A: Not in v3.0.** This release is purely about removing commands and improving UX.

New features coming in v3.1+:
- test-generator skill
- doc-generator skill
- session-analytics skill

---

## 🔍 Troubleshooting

### Skill Doesn't Activate

**Problem**: You say "Start session" but nav-start doesn't activate.

**Solutions**:
1. Be more specific: "Start my Navigator session"
2. Use alternative phrasing: "Load the navigator"
3. Check Claude Code version (needs skills support)

### Can't Find Marker

**Problem**: "Load marker" doesn't work.

**Solution**: Be specific about which marker:
```
✅ "Load the feature-complete marker"
✅ "Show my markers" (to see available markers)
```

### Documentation Not Archiving

**Problem**: Task documentation doesn't archive.

**Solution**: Specify the task ID:
```
❌ "Document this"
✅ "Archive TASK-45 documentation"
```

---

## 📊 Benefits of v3.0

### Token Savings

```
v2.x: Commands overhead = 11k tokens
v3.0: Commands overhead = 0 tokens
Savings: +11k tokens available
```

### Simpler UX

```
v2.x: Must remember 13 command syntaxes
v3.0: Just describe what you want
Learning curve: -50%
```

### Faster Onboarding

```
v2.x: "Type /nav:start to begin"
v3.0: "Start my Navigator session"
Time to productivity: -40%
```

---

## 🚀 Next Steps

### After Migration

1. **Update your workflow**:
   - Replace commands with natural language
   - Update any documentation/notes

2. **Share with team**:
   - Natural language is easier to teach
   - No syntax to explain

3. **Explore v3.1+ roadmap**:
   - test-generator skill (coming soon)
   - doc-generator skill
   - session-analytics skill

### Need Help?

- **GitHub Issues**: https://github.com/alekspetrov/navigator/issues
- **Release Notes**: https://github.com/alekspetrov/navigator/releases/tag/v3.0.0
- **Documentation**: https://github.com/alekspetrov/navigator

---

## 📝 Quick Reference Card

Print this for quick lookup:

```
┌─────────────────────────────────────────────────────┐
│ Navigator v3.0 Natural Language Quick Reference     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Start Session:                                      │
│   "Start my Navigator session"                     │
│                                                     │
│ Initialize Project:                                 │
│   "Initialize Navigator in this project"           │
│                                                     │
│ Archive Task:                                       │
│   "Archive TASK-XX documentation"                  │
│                                                     │
│ Create SOP:                                         │
│   "Create an SOP for debugging [issue]"            │
│                                                     │
│ Save Progress:                                      │
│   "Create a marker called [name]"                  │
│                                                     │
│ Manage Markers:                                     │
│   "Show my markers"                                │
│   "Load the [name] marker"                         │
│                                                     │
│ Clear Context:                                      │
│   "Clear context and preserve markers"             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

**Welcome to Navigator v3.0!** Natural language, 97% token reduction, zero commands to remember. 🚀

**Migration complete?** Start your next session with:
```
"Start my Navigator session"
```

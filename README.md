# Navigator

**Finish What You Start**

Sessions that last. AI that learns. Features that ship.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-6.15.3-blue.svg)](https://github.com/alekspetrov/navigator/releases)

---

## What is Navigator?

Navigator is a **Claude Code plugin** that implements context engineering for AI-assisted development.

Instead of loading all your documentation upfront (and crashing at exchange 7), Navigator loads what you need, when you need it—keeping 94% of your context window available for actual work.

For developers using Claude Code who want sessions that finish features instead of crash mid-way.

---

## The Loop You're Stuck In

You know the pattern:

```
Exchange 5:  Claude forgets your recent changes
Exchange 7:  Hallucinations start ("that function doesn't exist")
Exchange 8:  "Context limit reached"

Restart. Reload. Re-explain everything. Repeat.
```

You loaded 150k tokens of documentation "just in case."

You used 8k.

**The rest? Noise drowning out signal.**

---

## Break The Loop

Navigator implements context engineering—load what you need, when you need it.

| Metric | Without Navigator | With Navigator |
|--------|-------------------|----------------|
| Tokens loaded | 150,000 | 12,000 |
| Session length | 5-7 exchanges | 20+ exchanges |
| Context at end | 95% (crashed) | 35% (comfortable) |
| Token savings | — | **92%** |

**Result**: Sessions that actually finish what they start.

---

## And Your AI Gets Smarter

Navigator v5.0 adds Theory of Mind—Claude learns *you*.

**nav-profile**: Remembers your preferences across sessions
```
"Remember I prefer concise explanations"
→ Applied in future sessions
→ Auto-learns from corrections
```

**nav-diagnose**: Catches collaboration drift
```
Same correction twice → Quality check triggered
"You're not getting this" → Re-anchoring prompt
```

**Loop Mode** (v5.1): Run until done
```
"Run until done: add user authentication"
→ Structured completion with progress tracking
→ Dual-condition exit (heuristics + explicit signal)
→ Stagnation detection prevents infinite loops
```

**Knowledge Graph** (v6.0): Project memory that persists
```
"What do we know about auth?"
→ Unified search across tasks, SOPs, system docs
→ Experiential memory: patterns, pitfalls, decisions
→ Auto-surfaces relevant context on session start
```

---

## Same Workflows. More Capabilities.

Navigator is a superset. Everything you'd expect, plus context engineering.

| Feature | Navigator | Others |
|---------|-----------|--------|
| Structured workflows | ✅ 27 skills | ✅ |
| Component generation | ✅ | ✅ |
| Test generation | ✅ | ✅ |
| Session longevity | **20+ exchanges** | 5-7 exchanges |
| Token savings | **92% verified** | None |
| Code simplification | **✅** | ❌ |
| Task Mode | **✅** | ❌ |
| Theory of Mind | **✅** | ❌ |
| Knowledge Graph | **✅** | ❌ |
| Loop mode | **✅** | ❌ |
| OpenTelemetry metrics | **✅** | ❌ |
| Figma MCP integration | **✅** | ❌ |

**Same foundation. Superior context management.**

---

## Proof, Not Promises

Not estimates. Verified via OpenTelemetry.

```
╔══════════════════════════════════════════════════════╗
║          NAVIGATOR EFFICIENCY REPORT                 ║
╚══════════════════════════════════════════════════════╝

📊 TOKEN USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your project documentation:     150,000 tokens
Loaded this session:             12,000 tokens
Tokens saved:                   138,000 tokens (92% ↓)

📈 SESSION METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context usage:                        35% (excellent)
Efficiency score:                  94/100 (excellent)
```

**Check yours**: Run `/nav:stats` after installing.

---

## Quick Start

### Install

```bash
# Claude Code plugin marketplace
/plugin marketplace add alekspetrov/navigator
/plugin install navigator

# Restart Claude Code
```

### Initialize

```bash
"Initialize Navigator in this project"
```

### Start Every Session

```bash
"Start my Navigator session"
```

That's it. Navigator handles the rest.

---

## What You Get

**19 skills** that auto-invoke on natural language:

```
"Start my Navigator session"              → Session with 92% savings
"Create a React component for profile"    → Component + tests + styles
"Add an API endpoint for posts"           → Endpoint + validation + tests
"Create context marker: checkpoint"       → 97% context compression
"Run until done: add dark mode"           → Loop mode completion
```

**No commands to memorize.** Skills detect intent and execute.

---

## Stop Restarting. Start Shipping.

Your sessions crash because context management is broken by default.

Navigator fixes this with context engineering—the same principles Anthropic recommends.

**92% token savings. 20+ exchange sessions. Verified metrics.**

```bash
/plugin marketplace add alekspetrov/navigator
/plugin install navigator
```

**Finish what you start.**

---

## Troubleshooting

**Skill loads but prints docs instead of executing**
```bash
/plugin update navigator
```
Then retry. Outdated plugin version.

---

## Links

- [Documentation](.agent/DEVELOPMENT-README.md)
- [Philosophy](.agent/philosophy/CONTEXT-EFFICIENCY.md)
- [Release Notes](https://github.com/alekspetrov/navigator/releases)
- [GitHub](https://github.com/alekspetrov/navigator)

## License

MIT License - See [LICENSE](LICENSE)

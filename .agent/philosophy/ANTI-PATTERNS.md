# Anti-Patterns: How Context Efficiency Fails

**Recognizing and avoiding common mistakes**

---

## Introduction

These are the patterns that waste your context window. You've probably done most of them (I did).

Each anti-pattern shows:
- **What it is**: The mistake
- **Why it fails**: The underlying problem
- **How to recognize**: Warning signs
- **What to do instead**: The solution

---

## 1. Upfront Loading

### What It Is

Loading all project documentation at session start.

```bash
# Anti-pattern
Session start → Load all .agent/ docs → 100k tokens → Start working
```

### Why It Fails

**Context overwhelm**:
- 70-90% of loaded content irrelevant to current task
- AI tries to consider everything
- Signal (what matters) lost in noise (everything else)
- Recent changes forgotten (context full of old docs)

**Practical impact**:
```
Session 1: Works fine (context fresh)
Session 5: AI forgets recent code
Session 7: Hallucinations begin
Session 8: Context limit, session dies
```

### How to Recognize

**Warning signs**:
- ⚠️ Context usage >60% before you start working
- ⚠️ Sessions die in 5-7 exchanges consistently
- ⚠️ AI forgets functions you just wrote
- ⚠️ Hallucinations increase as session progresses
- ⚠️ "Let me check that again" happens frequently

**Check your stats**:
```bash
"Show me my session statistics"

Context usage: 75% (warning)
Efficiency score: 45/100 (needs improvement)
```

If score <70, you're likely bulk loading.

### What to Do Instead

**Strategic lazy loading** (Pattern #1):

```bash
Session start:
├── Navigator/index (2k) ✓ Load always
└── Current task doc (3k) ✓ Load for work

Total: 5k tokens (2.5% context)
```

**Then load on-demand**:
- Need system architecture? Load it when relevant
- Hit a bug? Load debugging SOP then
- Implementing API? Load API docs at that point

**Result**: 90%+ savings, context stays clean

**Read more**: [Patterns: Lazy Loading](./PATTERNS.md#1-lazy-loading)

---

## 2. Manual Search When Agents Exist

### What It Is

Reading 15-20 files manually when Task agent would optimize the search.

```bash
# Anti-pattern
"Read src/auth/login.ts"
"Read src/auth/signup.ts"
"Read src/auth/reset.ts"
...
(Repeat 15 times, 60k tokens loaded)
```

### Why It Fails

**Token waste**:
- Each file loaded in full (even if only need snippet)
- Read many irrelevant files (searching manually)
- No optimization or summarization
- Context fills with full file contents

**Time waste**:
- Manual searching takes 5-10 minutes
- Read files one by one
- Miss relevant files (incomplete search)
- Find pattern yourself (AI doesn't synthesize)

**Comparison**:
```
Manual approach:
├── 20 files read (80k tokens)
├── 10 minutes searching
└── Context 40% full

Agent approach:
├── Agent searches, reads, summarizes
├── Returns relevant parts only (8k tokens)
├── 30 seconds
└── Context 4% used

90% token savings, 95% time savings
```

### How to Recognize

**Warning signs**:
- ⚠️ You're manually reading >5 files in sequence
- ⚠️ You're searching for "where does X happen"
- ⚠️ You're looking for patterns across files
- ⚠️ You're exploring unfamiliar code
- ⚠️ Context usage jumps 30-40% from file reading

**Pattern to spot**:
```
You: "Read file1.ts"
You: "Read file2.ts"
You: "Read file3.ts"
...

If you see this pattern, STOP.
Use Task agent instead.
```

### What to Do Instead

**Use Task agent for exploration**:

```
Instead of manual reads:
"Find all authentication implementation files and
explain the auth flow"

Agent will:
1. Search codebase (finds relevant files)
2. Read them (extracts relevant parts)
3. Summarize (returns 8k tokens vs 80k)
4. Explain (synthesizes understanding)
```

**When to use manual Read**:
- You know exact file and location
- Single file, specific need
- Already have context loaded

**When to use Task agent**:
- Multi-file exploration
- Pattern discovery
- Unfamiliar codebase
- "Where does X happen?"

**Read more**: [Context Efficiency: Agents vs Manual](./CONTEXT-EFFICIENCY.md#when-to-use-agents-vs-manual-reads)

---

## 3. Forcing LLMs to Parse Structured Data

### What It Is

Asking AI to extract structured information from raw XML, JSON, or complex nested data.

```
# Anti-pattern
"Here's 150k tokens of Figma design XML.
Extract all components and their properties."

Result: Hallucinations, inconsistent output,
missed components
```

### Why It Fails

**LLMs are probabilistic, not deterministic**:

**LLMs excel at**:
- ✅ Semantic understanding
- ✅ Natural language processing
- ✅ Code generation
- ✅ Contextual decisions

**LLMs struggle with**:
- ❌ Deterministic parsing
- ❌ Structure traversal (recursive hierarchies)
- ❌ Data normalization
- ❌ Schema validation

**You wouldn't use regex to parse HTML.**
**Don't use LLMs to parse XML/JSON structures.**

**Real example** (Navigator v3.4.0):

Before (LLM parsing Figma XML):
```
Input: 150k tokens of nested design XML
LLM attempts: Pattern matching through noise
Output: Hallucinates components, misses relationships
```

After (Python preprocessing):
```
Input: Python parses XML deterministically
Output: Clean 12k token JSON structure
LLM receives: Structured data, easy to understand
Result: Reliable, no hallucinations
```

**92% token savings + deterministic output**

### How to Recognize

**Warning signs**:
- ⚠️ AI returns different results on same input
- ⚠️ "Extract X from this data" produces hallucinations
- ⚠️ Nested structures parsed incorrectly
- ⚠️ Missing elements or invented data
- ⚠️ Parsing takes many retries to get right

**Data types that need preprocessing**:
- XML structures (use elementTree, lxml)
- Deeply nested JSON (use jq, Python)
- CSV/tabular data (use pandas)
- Log files (use awk, grep, sed)
- Binary formats (use proper parsers)

### What to Do Instead

**Preprocessing pattern** (Pattern #3):

```
1. Traditional code parses structure
   (Python, bash, specialized tools)

2. Output clean, normalized data
   (JSON, simple structures)

3. LLM receives structured data
   (Easy to understand, semantic work only)
```

**Example**:
```python
# Preprocess with Python
import json
import xml.etree.ElementTree as ET

def parse_design_file(xml_data):
    tree = ET.fromstring(xml_data)

    # Deterministic extraction
    components = []
    for comp in tree.findall('.//component'):
        components.append({
            'name': comp.get('name'),
            'type': comp.get('type'),
            'props': extract_props(comp)
        })

    return json.dumps(components)

# LLM receives clean JSON
```

**Then LLM does semantic work**:
- Map components to design system
- Identify reuse opportunities
- Generate implementation plans
- Write code

**Right tool for the job.**

**Read more**: [Patterns: Preprocessing Before LLM](./PATTERNS.md#3-preprocessing-before-llm)

---

## 4. Missing SOPs (Knowledge Loss)

### What It Is

Solving a problem, then not documenting the solution. Next time, solve it again from scratch.

```
# Anti-pattern cycle
Week 1: Hit deployment issue, debug for 2 hours, fix it
Week 3: Same issue, forgot solution, debug 2 hours again
Week 5: Same issue again...
```

### Why It Fails

**Knowledge doesn't persist**:
- Solution lives in your head (or AI's session)
- Session ends, knowledge gone
- Next person (or future you) starts from zero
- Waste same time solving same problem

**Compound waste**:
```
Issue 1: Solve once (2 hours), no doc
  → Hit 5 more times (10 hours total wasted)

Issue 2: Solve once (1 hour), no doc
  → Hit 10 times (10 hours total wasted)

Missing SOPs cost: 20+ hours wasted on repeat problems
```

### How to Recognize

**Warning signs**:
- ⚠️ "We solved this before, but how?"
- ⚠️ Same questions asked by team repeatedly
- ⚠️ Onboarding takes weeks (tribal knowledge)
- ⚠️ Production issues solved multiple times
- ⚠️ "Who knows how to do X?" (single point of knowledge)

**Team indicators**:
- New developers ask same questions
- Production playbooks don't exist
- Debug procedures vary by person
- Integration knowledge in one person's head

### What to Do Instead

**Create SOP after solving**:

```
After fixing deployment issue:

1. Document the solution:
   .agent/sops/deployment/fix-ssl-cert-expiry.md

2. Include:
   - What the problem was
   - How to recognize it
   - Step-by-step solution
   - Why it works
   - How to prevent

3. Next time:
   - Load SOP (2k tokens)
   - Follow procedure
   - Solve in 10 minutes (not 2 hours)
```

**Navigator makes this easy**:
```
After solving issue:
"Create an SOP for debugging SSL certificate expiry"

Navigator:
1. Creates .agent/sops/debugging/ssl-cert-expiry.md
2. Structures with problem/solution/prevention
3. Adds to index for future discovery
```

**ROI calculation**:
```
SOP creation: 15 minutes once
Time saved per use: 1.5 hours
Uses: 5 times in 6 months

Total savings: 7.5 hours - 0.25 hours = 7.25 hours
```

**Read more**: [Patterns: SOP Creation Workflow](./PATTERNS.md#sop-creation)

---

## 5. Premature Compact

### What It Is

Running `/nav:compact` to clear context while you still need that context.

```
# Anti-pattern
Working on feature (context: 45%)
"This feels high, let me compact"
/nav:compact
Continue working...
"Wait, what was I working on?"
(Start over)
```

### Why It Fails

**You lose necessary context**:
- Task context cleared (what you're building)
- Recent changes forgotten (code you just wrote)
- Design decisions lost (why you chose approach)
- Conversation history gone (questions answered)

**Result**: Start over from less context than before.

### How to Recognize

**Warning signs**:
- ⚠️ Compacting at <60% context usage
- ⚠️ Compacting mid-feature (not at natural break)
- ⚠️ After compact: "What was I doing?"
- ⚠️ Compact because "it feels high" (not actual issue)
- ⚠️ AI asks questions you just answered

**Premature compact symptoms**:
```
Before compact:
AI: "I'll implement the auth flow as we discussed"

After compact:
AI: "What authentication approach do you want to use?"
(You just discussed this)
```

### What to Do Instead

**Smart compact strategy**:

**Compact AFTER**:
- ✅ Sub-task completed (natural break)
- ✅ Context >80% (actual need)
- ✅ Switching to unrelated task
- ✅ Session feels sluggish (AI performance drops)

**DON'T compact WHEN**:
- ❌ Mid-feature (in middle of work)
- ❌ Context <60% (plenty of room)
- ❌ Context needed for next sub-task
- ❌ Debugging complex issue (need history)

**Use context markers instead**:
```
Mid-feature, need to switch tasks:
"Create context marker: auth-implementation-v1"

Returns later:
"Resume from marker: auth-implementation-v1"

Context restored: All decisions, code, conversation
No information loss
```

**Compact workflow**:
```
1. Complete sub-task ✓
2. Check context usage (75%+?) ✓
3. Create marker (preserve decisions)
4. Run /nav:compact
5. Start fresh for next task
```

**Read more**: [Patterns: Context Markers](./PATTERNS.md#6-context-markers-compress-decisions)

---

## 6. No Navigator Session Start

### What It Is

Starting work without running "Start my Navigator session"

```
# Anti-pattern
Open Claude Code
Start coding immediately
No navigator loaded
No guidance
Manual file finding
```

### Why It Fails

**Missing the map**:
- No index of what documentation exists
- No guidance on where to find things
- No task context loading
- No efficiency tracking

**You're navigating blind**:
```
Without navigator:
├── Where are the docs?
├── What SOPs exist?
├── What's the current task?
├── How is context being used?
└── (Manual searching, wasted time)

With navigator:
├── Documentation index loaded (2k)
├── Current task context loaded (3k)
├── Guided navigation to relevant docs
└── Efficiency tracked ("Show me my session statistics")
```

### How to Recognize

**Warning signs**:
- ⚠️ Asking "where is X documented?"
- ⚠️ Manually searching for docs
- ⚠️ No task context loaded
- ⚠️ Can't run `"Show me my session statistics"`
- ⚠️ Working without structure

### What to Do Instead

**Every session starts with**:
```
"Start my Navigator session"
```

This loads:
1. Navigator/index (DEVELOPMENT-README.md)
   - What docs exist
   - Where to find them
   - When to load what

2. Current task (if configured with PM)
   - What you're working on
   - Implementation context

3. Session efficiency tracking
   - Token usage monitoring
   - Efficiency scoring

**Then work efficiently**:
- Navigate to relevant docs (guided)
- Load on-demand (strategic)
- Track efficiency ("Show me my session statistics")

---

## 7. Ignoring Efficiency Signals

### What It Is

Not checking `"Show me my session statistics"` or ignoring low efficiency scores.

```
# Anti-pattern
Work for weeks
Never check efficiency
Score drops to 55/100
Keep working same way
Wonder why sessions feel sluggish
```

### Why It Fails

**No feedback loop**:
- You don't know if you're efficient
- Bad habits compound
- Context waste becomes normal
- Sessions degrade slowly (boiling frog)

**Missed optimization opportunities**:
- Efficiency 55/100 → Could be 95/100
- Wasting 2x tokens unnecessarily
- Sessions could last 2x longer
- Simple changes would fix it

### How to Recognize

**Warning signs**:
- ⚠️ Never run `"Show me my session statistics"`
- ⚠️ Don't know your efficiency score
- ⚠️ Sessions feel inconsistent
- ⚠️ Context fills quickly (but don't measure)
- ⚠️ "It's fine" (without data)

### What to Do Instead

**Check efficiency regularly**:

```bash
# After every few tasks
"Show me my session statistics"

Efficiency score: 94/100 ✓ Excellent
Token savings: 92% ✓ Great
Context usage: 35% ✓ Healthy
```

**Respond to signals**:

**Score 90-100**: Keep doing what you're doing ✓

**Score 80-89**: Minor tweaks needed
- Check: Are you loading docs you don't use?
- Optimize: Use more agent searches
- Result: 90+ achievable

**Score 70-79**: Review strategy
- Problem: Likely bulk loading some docs
- Solution: Check what's loaded, load less upfront
- Read: [Lazy Loading Pattern](./PATTERNS.md#1-lazy-loading)

**Score <70**: Anti-patterns present
- Problem: Multiple anti-patterns active
- Solution: Read this doc, identify which ones
- Action: Correct immediately (big gains available)

---

## 8. Not Using Progressive Refinement

### What It Is

Loading full documentation when summaries would suffice.

```
# Anti-pattern
Need to understand API structure
Load full API documentation (15k tokens)
Read only the overview section (used 2k worth)
Wasted 13k tokens
```

### Why It Fails

**Front-loading details**:
- Load everything before knowing what you need
- Most details irrelevant to current task
- Context filled with unused information
- Pattern matching finds wrong solutions (noise)

### How to Recognize

**Warning signs**:
- ⚠️ Loading full docs, using 20% of content
- ⚠️ Reading entire files for one function
- ⚠️ "Let me load everything in case I need it"
- ⚠️ Context usage jumps from doc loads

### What to Do Instead

**Progressive refinement pattern**:

```
Step 1: Load summary/overview
  ├── Understand structure
  ├── Identify what you need
  └── (~2k tokens)

Step 2: IF needed, load specific section
  ├── Now you know what's relevant
  ├── Load only that part
  └── (~3k additional)

Step 3: IF still needed, drill deeper
  ├── Load implementation details
  └── (~5k additional)

Total: 10k tokens (vs 15k loading everything)
```

**Example**:
```
Need to integrate payment system:

Progressive:
1. Load payments/README.md (overview, 2k)
2. See Stripe is used → Load payments/stripe-integration.md (5k)
3. Total: 7k tokens

Bulk:
1. Load all payment docs (15k)
2. Use 7k worth
3. Waste 8k

Progressive saves: 53%
```

**Read more**: [Patterns: Progressive Refinement](./PATTERNS.md#4-progressive-refinement)

---

## 9. Context Flooding from Command Output

### What It Is

Letting verbose command output land directly in the conversation context.

```bash
# Anti-pattern: full output flows into context
npm test                              # 8k tokens of test output
python train.py                       # 12k tokens of progress logs
grep -r "useState" src/               # 5k tokens of matches
cargo build --verbose                 # 20k tokens of compile output
```

Each invocation adds raw, mostly-irrelevant noise to the working window. The signal you care about — pass/fail, the one failing test, the matching file — is buried.

### Why It Fails

**Context pollution**:
- 95% of the output is irrelevant (progress bars, warnings you'd ignore, repeated patterns)
- The 5% that matters (a stack trace, a failure line) gets diluted
- Subsequent reasoning has to wade through it
- Compounds: 3 verbose commands = 30-50k tokens spent on noise

**Practical impact**:
```
Pre-run context:  40k tokens (clean, on-task)
After npm test:    48k tokens (8k of "✓ test passed" lines)
After build:       68k tokens (now half noise)
After grep -r:     73k tokens
                   ↑ AI now reasons over 33k tokens of irrelevant output
```

**Karpathy's autoresearch explicitly warns**:
> `uv run train.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context)

### How to Recognize

**Warning signs**:
- ⚠️ A single tool result >2k tokens of output
- ⚠️ Repeated patterns dominate (progress bars, identical log lines)
- ⚠️ You read 200 lines to find 1 line that mattered
- ⚠️ Build/test/install output captured inline instead of summarized
- ⚠️ Binary or log artifacts pasted into context

**Quick check**: If you could replace the tool output with a single grep line and lose nothing, you flooded context.

### What to Do Instead

**Redirect verbose output to a file, then extract only what matters**:

```bash
# Tests
npm test > test.log 2>&1
grep -E "(FAIL|✗|^Tests:)" test.log | head -20

# Build
cargo build --verbose > build.log 2>&1
grep -E "(error|warning: unused)" build.log | head -10

# Long-running training/jobs
python train.py > run.log 2>&1
grep -E "^(val_|loss|epoch)" run.log | tail -20

# Wide greps
grep -rn "useState" src/ > matches.txt
head -20 matches.txt && echo "... $(wc -l < matches.txt) total matches"
```

**Pattern**: redirect → filter → only the filtered result enters context.

**Cost comparison**:
```
Inline:  npm test          → 8000 tokens
Filtered: > log + grep      → 200 tokens (97% savings)
```

**This is the shell-level companion to Pattern #3 (Preprocessing Before LLM)** — same principle, different tool.

**Read more**: [Patterns: Preprocessing Before LLM](./PATTERNS.md#3-preprocessing-before-llm) · [Anti-Patterns: Forcing LLMs to Parse Structured Data](#3-forcing-llms-to-parse-structured-data)

---

## Summary

### The Anti-Patterns

1. **Upfront Loading** - Load all docs at start (waste 70-90%)
2. **Manual Search** - Read 20 files vs using agent (waste 90%)
3. **LLM Parsing** - Force AI to parse structures (hallucinations)
4. **Missing SOPs** - Don't document solutions (repeat work)
5. **Premature Compact** - Clear context while still needed (start over)
6. **No Navigator Start** - Work without guidance (manual searching)
7. **Ignoring Signals** - Don't check efficiency (miss optimizations)
8. **No Refinement** - Load everything upfront (waste details)
9. **Context Flooding** - Let verbose command output land inline (waste 90%+)

### Recognition Pattern

**If any of these feel familiar, you have anti-patterns**:
- Sessions die in 5-7 exchanges
- Context fills before you start
- AI forgets recent changes
- Same problems solved repeatedly
- Manual doc searching
- Don't know efficiency score

### The Fix

**Check your efficiency**:
```bash
"Show me my session statistics"
```

**Score <70?** Read this doc, identify your anti-patterns

**Score 70-90?** Minor optimizations available

**Score 90+?** You're doing great ✓

### Learn the Patterns

**See what works**:
→ Read [Success Patterns](./PATTERNS.md)

**Understand the principle**:
→ Read [Context Efficiency](./CONTEXT-EFFICIENCY.md)

**Apply to your work**:
→ Start: "Start my Navigator session"

---

**Anti-patterns are normal. Everyone hits them.**

**The difference: Recognize them, fix them, improve.**

**Check your score: `"Show me my session statistics"`**

# TASK-35: Project Knowledge Graph

**Status**: 🔬 Research & Planning
**Created**: 2025-01-23
**Version**: v6.0.0
**Priority**: High

## Summary

Unified Knowledge Graph that connects all project knowledge (tasks, SOPs, system docs) with an experiential memory layer (patterns, pitfalls, decisions, learnings). Single query surface: "What do we know about X?"

## Evolution from Original Concept

**Original**: Project Memory (another storage silo)
**Evolved**: Knowledge Graph (unified layer over ALL knowledge)

The insight: Navigator docs ARE project memory. The gap isn't storage—it's **discovery and relationships**.

## Vision

```
┌─────────────────────────────────────────────────────────────┐
│                 PROJECT KNOWLEDGE GRAPH                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │  TASKS  │───▶│  SOPs   │◀───│ SYSTEM  │    │ MARKERS │  │
│  └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘  │
│       └──────────────┼──────────────┼──────────────┘        │
│                      ▼              ▼                        │
│              ┌───────────────────────────┐                  │
│              │        CONCEPTS           │                  │
│              └───────────────────────────┘                  │
│                      ▲              ▲                        │
│       ┌──────────────┼──────────────┼──────────────┐        │
│  ┌────┴────┐    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐  │
│  │PATTERNS │    │PITFALLS │    │DECISIONS│    │LEARNINGS│  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                     MEMORIES (experiential)                  │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### R1: Graph Storage
- `.agent/knowledge/graph.json` - index (~1k tokens)
- `.agent/knowledge/memories/` - experiential learnings
- Hybrid: JSON for queries, Markdown for details
- Git-tracked (team can share)

### R2: Node Types
- **TASK** - implementation plans
- **SYSTEM** - architecture docs
- **SOP** - procedures
- **MARKER** - session snapshots
- **CONCEPT** - extracted topics (auth, testing, api)
- **MEMORY** - patterns, pitfalls, decisions, learnings
- **FILE** - codebase files

### R3: Edge Types (Relationships)
- `created-from` - SOP created from TASK
- `references` - doc A links to doc B
- `relates-to` - shared concepts (weighted)
- `implements` - TASK implements CONCEPT
- `learned-from` - MEMORY discovered in TASK
- `contradicts` - conflicting memories
- `validated-by` - MEMORY confirmed in TASK
- `supersedes` - new replaces old

### R4: Query Interface
```
"What do we know about auth?"
→ Returns: Tasks, SOPs, Memories, Files related to auth

"Any pitfalls for testing?"
→ Returns: Pitfall memories + related SOPs

"What decisions about architecture?"
→ Returns: Decision memories with rationale
```

### R5: Memory Capture
- Auto from corrections (nav-profile → memory)
- Auto from task decisions (extract on completion)
- Explicit ("Remember: we use X for Y")
- Pattern detection (3x same approach → prompt)

### R6: Confidence Decay
- Memories decay without validation
- Usage boosts confidence
- Prune below threshold

## Technical Design

### graph.json Schema
```json
{
  "version": "1.0.0",
  "nodes": {
    "tasks": { "TASK-31": { "concepts": [...], "path": "..." } },
    "concepts": { "auth": { "aliases": ["login", "OAuth"] } },
    "memories": { "mem-001": { "type": "pitfall", "confidence": 0.9 } }
  },
  "edges": [
    {"from": "TASK-31", "to": "auth", "type": "implements"},
    {"from": "mem-001", "to": "TASK-12", "type": "learned-from"}
  ],
  "concept_index": {
    "auth": ["TASK-29", "mem-001", "SOP-001"]
  }
}
```

### Token Budget
| Component | Tokens |
|-----------|--------|
| graph.json (50 nodes) | ~1000 |
| Memory summaries (3) | ~300 |
| **Session overhead** | **~1.3k** |

✅ Under 2k requirement

## Implementation Phases

### Phase 1: Foundation (2-3 days)
- [ ] `.agent/knowledge/` structure
- [ ] `graph.json` schema
- [ ] `graph_manager.py` (CRUD, traversal)
- [ ] `nav-graph-init` (one-time build)

### Phase 2: Core Skill (2-3 days)
- [ ] `nav-graph` skill
- [ ] Query functions
- [ ] Natural language triggers
- [ ] Response formatting

### Phase 3: Memory Layer (2-3 days)
- [ ] Correction → memory capture
- [ ] Task decision → memory
- [ ] Confidence decay
- [ ] Memory surfacing

### Phase 4: Integration (2-3 days)
- [ ] nav-start (load graph)
- [ ] nav-task (update graph)
- [ ] nav-profile (correction → memory)

### Phase 5: Polish (post-6.0.0)
- [ ] Conflict detection
- [ ] Staleness pruning
- [ ] Visualization export

## Verify

```bash
# Structure exists
test -d ".agent/knowledge" && echo "✓ Directory"
test -f ".agent/knowledge/graph.json" && echo "✓ Index"

# Skill works
test -f "skills/nav-graph/SKILL.md" && echo "✓ Skill"

# Query works
# "What do we know about auth?" → returns related items
```

## Done

- [ ] Graph index loads on session start
- [ ] "What do we know about X?" returns unified results
- [ ] Memories auto-captured from corrections
- [ ] <1.5k token overhead
- [ ] Relationship traversal working

## Open Questions

1. **Concept extraction**: LLM-assisted or manual tagging?
   → Recommendation: Auto-extract, allow override

2. **Cross-project**: Share patterns between projects?
   → Recommendation: Project-scoped v6.0, global v6.1

3. **Memory limits**: How many before pruning?
   → Recommendation: Soft limit 100, prune <0.3 confidence

## References

- Original concept: TASK-35 (Project Memory)
- Related: nav-profile, nav-marker, nav-task
- Inspiration: Knowledge graphs, semantic search

# Navigator v6.15.2 Release Notes

**Release Date**: 2026-05-15
**Type**: Patch — four v6.15.1 follow-ups (safety fix + tooling + cleanup)

---

## Summary

Same-day follow-up to v6.15.1. The release-work surfaced four problems that were out of scope at release time; this patch closes all of them. One is a real safety bug (data loss in the memory-write path); the other three are tooling and consistency fixes that make future releases catch the v6.14.0 class of silent-fail before they ship.

---

## What changed

### 1. `nav-graph add-memory` CLI: no more silent overwrites

The CLI silently clobbered on-disk memory files whenever the graph and the filesystem drifted apart. Three independent bugs in `skills/nav-graph/functions/`:

- `_next_memory_id` only scanned graph nodes for the next free ID. When `mem-NNN.md` existed on disk but no graph node pointed to it (the canonical "ghost file" state after a partial reconciliation), the function returned a colliding ID.
- `add_memory` ignored the `--node-id` flag entirely. It was declared in argparse, passed through CLI dispatch, then dropped on the floor at the call site — the function only ever computed its own ID.
- `create_memory_file` called `output_path.write_text(content)` with no existence check — unconditional overwrite, no warning.

Caught during v6.15.1 release work when `mem-034.md` (the UserPromptSubmit recursive-block pitfall, captured 2026-05-11) was clobbered by an auto-assigned-ID call. Reverted before push.

**Fix**:
- `_next_memory_id(memories, base_dir)` now takes the **union** of graph IDs and on-disk file stems, returns max+1.
- `add_memory(..., memory_id=None)` accepts an explicit ID. If provided, used directly after a graph-collision check. If omitted, falls through to the union-scan.
- `create_memory_file` raises `FileExistsError` on collision with a clear message naming the existing file and recommending `--memory-id` change or manual delete.
- CLI dispatch in `graph_manager.py` passes `args.node_id` through and catches `ValueError`/`FileExistsError` with exit 1 + stderr message.

### 2. Graph reconciliation

After v6.15.1, the graph reported `memory_count: 34` while the filesystem had 36 memory files. The two missing nodes were `mem-034` and `mem-035` — both legitimate pitfalls captured in v6.11.1 / v6.12.0 verification but never registered in the graph (likely because the `nav-graph` CLI of the day didn't ingest existing files). Both are now in the graph with their correct content summary, concept tags, confidence, and source-task linkage.

Graph and disk are now at 36↔36, zero drift.

### 3. `nav-release --verify-hooks` mode

A new release-validator mode that smoke-tests every plugin manifest hook command end-to-end at release time. Would have caught the v6.14.0 silent-fail at release time.

**Mechanism**: parses `.claude-plugin/plugin.json`'s `hooks` block. For each `command` string, executes it via `bash -c` with both `$CLAUDE_PLUGIN_DIR` bound (to the latest cache version) and explicitly unset. Feeds an event-appropriate JSON fixture on stdin. Captures exit code, stdout length, stderr length.

**Failure detection**: silent exit 0 with no output on either channel — but **only for hooks that are expected to emit payload** (`SessionStart`, `PreCompact`, `PostCompact`). Other events (`Stop`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`) are silent by design — their hooks are state writers or blocking-only — so quiet exit 0 there is correct behavior, not a regression.

**Verified**: 20/20 pass on the v6.15.1 manifest. Re-applying the v6.14.0 `if [ -n "$CLAUDE_PLUGIN_DIR" ]; then ... fi` guard to `SessionStart` in a temp manifest correctly produces `❌ SessionStart [unset] silent exit 0 — payload-emitting hook produced no output`.

Add to the release-validation routine going forward.

### 4. `nav-sync-claude/skill.md` → `SKILL.md`

Pre-existing inconsistency since the v6.14.0 rename from `nav-update-claude`. All other skills ship `SKILL.md` (uppercase). The release validator's `--verify-tag` check uses uppercase, so this directory produced a false-positive "missing skill" report on every v6.14.0+ release.

Renaming required `git mv -f` because macOS APFS is case-insensitive (`core.ignorecase=true`). On the first attempt the rename appeared to land but was silently un-committed when git resolved the case fold against the index entry; the `-f` flag forces the index update.

---

## Verification

Pre-release checks:
- `release_validator.py --check-all` → ✓
- `release_validator.py --verify-hooks` → 20/20 pass (using the new mode against itself)
- `add-memory --node-id mem-036` (collision) → exit 1 with clear error, graph unchanged
- `_next_memory_id` returns `mem-037` (max of disk ∪ graph)
- Disk-graph diff: 36↔36, zero ghost files, zero orphan nodes

---

## Upgrade notes

No breaking changes. Restart Claude Code after upgrade so the patched plugin is registered (standard for any Navigator release).

If you've been using `nav-graph add-memory` from CLI: the `--node-id` flag now actually does what it says, and the CLI will refuse to overwrite an existing file. Both are bug fixes; nobody should have been relying on the buggy behavior.

---

## Files modified

```
skills/nav-graph/functions/graph_manager.py
skills/nav-graph/functions/memory_writer.py
skills/nav-release/functions/release_validator.py
skills/nav-sync-claude/SKILL.md            (renamed from skill.md)
.agent/knowledge/graph.json                (mem-034 + mem-035 + version bump)
.claude-plugin/plugin.json                 (version bump)
.claude-plugin/marketplace.json            (version + changelog)
README.md                                  (version badge)
CLAUDE.md                                  (version)
.agent/.nav-config.json                    (version)
CHANGELOG.md
releases/RELEASE-NOTES-v6.15.2.md          (new)
```

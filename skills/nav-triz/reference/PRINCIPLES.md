# TRIZ for Software: Separation Modes and Mapped Principles

**One-page lookup for the nav-triz divergence step. Lazy-loaded; not injected.**

---

TRIZ (Altshuller) mined ~200k patents for how inventors resolved contradictions
("improving A worsens B") without compromise. The 40 inventive principles are physical
by origin; about half transfer to software cleanly, the rest do not. This page keeps only
what transfers, with the move each principle suggests and, where this repo has one, a
decision memory that used it (`graph_manager.py --action contradictions --filter ...`).

## Separation modes (resolve a *physical* contradiction: X must be both A and not-A)

| Separation | Question to ask | Software move | Example here |
|---|---|---|---|
| **time** | Must it be A *now* and not-A *later*? | shims for one major then delete; strip before scan; soak before tag | mem-063, mem-066, mem-072 |
| **space** | Must it be A *here* and not-A *there*? | single emitter module; sidecar; adapter; staging replica | mem-065 |
| **condition** | Must it be A *when X* and not-A *otherwise*? | ship OFF + opt-in; confirm only on high-stakes; threshold | mem-060, mem-043, mem-074 |
| **level** | Must the *part* be A while the *system* is not-A? | atomic single state file over per-op writes; separate axis per concern | mem-064, mem-062 |

Always try the four separation questions before reaching for a principle. Most software
contradictions dissolve at "when" or "at which level".

## Mapped principles (the ~20 that transfer)

| # | Principle | Software move | Mode |
|---|---|---|---|
| 1 | Segmentation | split into independent parts: modules, ops, per-feature toggles | level |
| 2 | Taking out | extract the disturbing part: sidecar, separate process, quarantine | space |
| 3 | Local quality | different parts behave differently: hot path fast, cold path safe | space |
| 5 | Merging | combine identical operations: batch, single state file, one dispatcher | level |
| 6 | Universality | one part does several jobs: shared runtime, one query interface | level |
| 7 | Nesting | composition, wrappers, layered config | level |
| 10 | Prior action | precompute, cache, prefetch, normalize before scan | time |
| 11 | Beforehand cushioning | fallback prepared in advance: additive migration, verified rollback | time |
| 13 | Inversion | pull not push, lazy not eager, allow-list not deny-list | condition |
| 15 | Dynamization | adjustable at runtime: toggle, threshold, ship OFF then opt in | condition |
| 16 | Partial / excessive action | sample instead of read-all; over-fetch then trim; best-effort | condition |
| 17 | Another dimension | add an axis: separate score per concern, tags over folders | space |
| 19 | Periodic action | cron, decay passes, batch reconcile instead of continuous | time |
| 21 | Skipping | run the harmful step fast or not at all: fail-open, short-circuit | time |
| 23 | Feedback | telemetry, health checks, stagnation detection, self-tuning | condition |
| 24 | Intermediary | adapter, shim, facade, single emitter between parties | space |
| 25 | Self-service | the system maintains itself: auto-update, reconcile on start | level |
| 26 | Copying | cheap copy instead of the real thing: fixtures, goldens, staging, dry-run | space |
| 27 | Cheap short-living objects | ephemeral env, tmp worktree, per-turn state | time |
| 34 | Discarding and recovering | prune, archive to resolved/, rebuild on demand | time |
| 35 | Parameter change | confidence instead of boolean, soft budget instead of hard limit | condition |

The curated keyword map behind `functions/triz_suggest.py` covers exactly these rows.

## Principles that do not transfer (do not force them)

8 anti-weight, 12 equipotentiality, 14 spheroidality, 18 mechanical vibration,
29 pneumatics/hydraulics, 30 flexible shells, 31 porous materials, 36 phase transitions,
37 thermal expansion, 38 strong oxidants, 39 inert atmosphere. Occasionally 4 asymmetry,
9 preliminary anti-action, 22 blessing in disguise, 28 mechanics substitution, 32 colour
change, 33 homogeneity, 40 composites map by analogy; treat those as optional prompts.

## Using this page

1. Write the contradiction as "improving A vs worsening B" (technical) or "X must be both A
   and not-A" (physical).
2. Ask the four separation questions. If one dissolves it, that is the candidate family.
3. Run `triz_suggest.py --contradiction "..."` for three principle prompts from different
   modes plus prior decisions in the graph.
4. Draft one concrete candidate per prompt. Each must say what it worsens; a candidate with
   no downside is a compromise misdescribed as a resolution.
5. Pick one, state why, and after the work capture the decision with
   `--contradiction / --separation / --principle` so the graph learns.

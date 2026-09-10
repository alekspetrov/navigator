# Step 1: Decompose

**Who:** main session. **Artifact:** `search-plan.md` + `atomic_items` in `run.json`.

**Goal:** before any fetching, turn the verbatim query into atomic items with a coverage
matrix, and a search plan that covers every item from three lenses. A missing item here
becomes a missing section in step 3, so this is the highest-leverage ten minutes of the
run.

## Procedure

1. `python3 "$NDR/research_run.py" step --run <slug> --start 1`
2. Read `<run_dir>/query.md`. Do not paraphrase the query anywhere in this step.
3. **Atomic items.** Split the query into the smallest units that each need their own
   evidence: sub-questions, named entities with required fields ("for each X: A, B, C"),
   comparisons, time windows. Give each an id (`Q1`, `Q2`, `E1`...). Record the
   register the query implies (`analyze` default; `survey` for "what is the landscape";
   `teach` for "explain / teach me"). Save them:
   ```bash
   python3 "$NDR/research_run.py" set --run <slug> --key atomic_items \
     --value '[{"id":"Q1","text":"...","kind":"question"},{"id":"E1","text":"...","kind":"entity","fields":["A","B"]}]'
   python3 "$NDR/research_run.py" set --run <slug> --key register --value '"analyze"'
   ```
4. **Search plan from three lenses.** For every atomic item write searches under each
   lens. Target roughly 3x `max_sources` planned searches in total; more for entity
   lists.
   - **Breadth.** Core factual content; recent developments (last 2 years); each named
     sub-concept.
   - **Canonical / primary.** The load-bearing sources commentary is built on:
     original study, official documentation, standards text, primary filing or dataset,
     the author's own write-up. "original paper", "specification", "official docs".
   - **Adversarial.** "criticism of X", "limitations of X", "why X fails", competing
     framework, negative results. At least one adversarial search per major item; at
     least 20% of the plan overall. The critic punishes one-sided corpora.
5. Write `<run_dir>/search-plan.md`:
   ```markdown
   | item | query | lens | target |
   |---|---|---|---|
   | Q1 | "ion trap gate fidelity 2025" | breadth | factual |
   | Q1 | "trapped ion two-qubit gate original paper" | canonical | primary |
   | Q1 | "limitations of trapped ion scaling" | adversarial | contrarian |
   ```
6. **Gap check.** Re-read the verbatim query. Any noun phrase, entity, region, period, or
   category in it with zero rows in the plan? Add rows now.
7. `python3 "$NDR/research_run.py" step --run <slug> --done 1`

## Exit criterion

`search-plan.md` exists, every atomic item has rows under all three lenses, and
`run.json.meta.atomic_items` is non-empty.

## Next

Read `steps/2-sweep.md`.

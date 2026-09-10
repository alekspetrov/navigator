# Orchestrator notes

## Step 2 queue (16 URLs, 2 batches)
Batch A: docs howto 3.14 (Q1), PEP 779 (Q1), LWN past/present/future (Q1), docs howto 3.13 (Q2), CodSpeed 3.13 (Q2), py-free-threading tracker (Q3), NumPy thread safety (Q3), pandas #59057 (Q3)
Batch B: whatsnew 3.14 (Q1), PEP 703 (Q1), Grinberg 3.14 (Q2), danilchenko (Q2), roturgo 33% mandelbrot (Q2), Django forum #36983 thread (Q3), Quansight one-year recap (Q3), DjangoCon talk (Q3)
Expect: Q1 well covered by primary docs; Q2 numbers 40% (3.13) vs 5-10% (3.14), adversarial 33% outlier; Q3 pandas Windows wheel gap, Django no official declaration, psycopg blocker.
Dry-run note: fetchers are general-purpose agents carrying the deep-research-fetcher prompt (plugin agents not installed yet).

## Step 2 result
15 ok, 1 blocked (Quansight recap, 429 on raw and WebFetch). Coverage Q1=5 Q2=5 Q3=5. No gap wave needed.
Dry-run finding: concurrent fetchers raced on next_id (A saw 008 claimed by B). Fixed with O_EXCL allocation + retry, test added.
Whatsnew 3.14 and PEP 703 truncated at 40k (expected; free-threading sections present).

## Step 3
Writer spawned with max_full_reads=6, register=analyze. Expect Q2 numbers: 3.13t ~40% (docs 3.13), 3.14t 5-10% (whatsnew) vs 1-8% pyperformance (howto 3.14), 33% mandelbrot outlier (013).

## Step 3 result
Writer: 15 sources cited, 6 full reads, 3031 words. Structural pre-check passed all 10 gate checks first time. sources_rows_before_patch=15.

## Step 4 result
Critic: 20 findings (1 critical, 9 major, 10 minor), 0 structural, every quote anchored exactly. Critical = draft ignored the on-disk 33% Mandelbrot single-thread result (013) while presenting 5-10% as the whole answer. No gap fetch needed.

## Step 5
Patcher spawned (general-purpose, Read/Edit/Write only). Gate will check unresolved criticals and rows >= 15.

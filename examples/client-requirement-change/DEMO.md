# Three-minute demo for Professor Izbicki

Before presenting, open `README.md`, `fac.yaml`, `expected-impact.json`, and `results/impact-report.md`. Keep the recorded evidence ready; a full fresh experiment takes longer than a single incremental build.

**0:00–0:25 — State the question.**

“I used your pinned fac implementation to test whether explicit requirement dependencies let us safely reuse engineering artifacts after a customer change. Everything is synthetic and deterministic. I wrote the expected-impact table before running the experiment.”

Show `inputs/v1.json` and `inputs/v2.json`: retention goes from 30 days to 7. Search and response-quality requirements stay the same. The extra period in the display name is the nonmaterial control.

**0:25–0:55 — Show the integration.**

Open `fac.yaml`. Point to the full validated record, the retention/search projections, and the five artifacts. Explain: “fac does the ordering, execution, reuse decisions, and native build logging. My Python code only parses and renders files, tests behavior, and measures the results. The projections turn requirement-level content into ordinary file dependencies.”

**0:55–1:30 — Show actual successful reuse.**

Open `results/impact-report.md`. V1 built five deliverables; unchanged reruns built nothing. Explicit V2 rebuilt four deliverables, preserved search, and passed all six checks.

Open `results/explicit/material/evidence/v2/artifacts/retention-config.json` beside the V1 copy. Show 30 versus 7. Open `acceptance.py` and point to the fixed seven-day boundary: records just under seven days survive; records exactly seven days old do not. Show the saved `acceptance.log`.

**1:30–2:05 — Show the missing-dependency failure.**

Open `fac.missing.yaml`: the checklist tracks search while its generator reads retention from the full record. Open `results/missing/material/evidence/v2/artifacts/deployment-checklist.md`, which still says 30 days. The configuration says 7. Show `results/missing/material/evidence/v2/acceptance.log`: the independent checklist check fails.

“fac cannot discover the omitted content dependency. A transitive ordering edge is insufficient after a semantic projection removes retention from the recorded context. That is the correctness risk I wanted to expose.”

**2:05–2:35 — Show the conservative cost.**

Return to the report. “The conservative generator loads the full record and raw message. It rebuilt five deliverables for V2: one unnecessary search rebuild. The separate punctuation-only control rebuilt all five, despite identical output bytes. Those are measured generation events and potential review candidates, not measured review minutes.”

**2:35–3:00 — State limits and next questions.**

“This is a five-artifact experiment, not a production system or a new algorithm. This fac revision combines timestamps and prompt hashes, and its schema validation warns rather than failing. My parser enforces strict validation, and the runner enables fac's existing halt-on-error option after tests exposed its default zero exit status on command failure. Compatibility probes also cover excluded prompt content and equal timestamps. The next research question is how to check that recorded dependencies cover actual generation inputs without paying the cost of including every context file.”

For a live unchanged rerun, use the exact direct-fac command in the README. For full reproduction, use a new output directory and then run pytest. The intentionally failing checklist check is expected inside the experiment; the outer verification suite confirms it.

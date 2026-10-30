# Client requirement change: measured impact

All customer messages and business data are synthetic. Deterministic command targets were executed by unmodified fac.

Pinned upstream commit: `2a099e6e97db390fa578a33edf9f66d61aec5818`; 76 tracked source files verified by SHA256.
Expected-impact table was frozen before execution: `a0ddb50d0f80412ab1f9c8719f4744958eb98399435b87566332dddbe53828c6`.

The validated retention requirement changed from **30 days to 7 days**. Search and response-quality values did not change. A display-name period is the isolated nonmaterial control.

Observed impact below means a native fac generation event. False positives and false negatives compare regeneration against the independent business-impact table, not against the dependency graph.

| Mode | Stage | Expected | Rebuilt | FN | FP | Total fac builds | Acceptance |
|---|---|---:|---:|---:|---:|---:|---|
| explicit | initial | 5 | 5 | 0 | 0 | 8 | 5 passed, 0 failed, 1 skipped |
| explicit | unchanged | 0 | 0 | 0 | 0 | 0 | 5 passed, 0 failed, 1 skipped |
| explicit | v2 | 4 | 4 | 0 | 0 | 7 | 6 passed, 0 failed, 0 skipped |
| explicit | cosmetic_only | 0 | 0 | 0 | 0 | 3 | 5 passed, 0 failed, 1 skipped |
| conservative | initial | 5 | 5 | 0 | 0 | 8 | 5 passed, 0 failed, 1 skipped |
| conservative | unchanged | 0 | 0 | 0 | 0 | 0 | 5 passed, 0 failed, 1 skipped |
| conservative | v2 | 4 | 5 | 0 | 1 | 8 | 6 passed, 0 failed, 0 skipped |
| conservative | cosmetic_only | 0 | 5 | 0 | 5 | 8 | 5 passed, 0 failed, 1 skipped |
| missing | initial | 5 | 5 | 0 | 0 | 8 | 5 passed, 0 failed, 1 skipped |
| missing | unchanged | 0 | 0 | 0 | 0 | 0 | 5 passed, 0 failed, 1 skipped |
| missing | v2 | 4 | 3 | 1 | 0 | 6 | 5 passed, 1 failed, 0 skipped |
| missing | cosmetic_only | 0 | 0 | 0 | 0 | 3 | 5 passed, 0 failed, 1 skipped |

## Confirmed observations

- **explicit / V2** regenerated: client-summary.md, deployment-checklist.md, retention-config.json, test_retention.py.
  False negatives: none; false positives: none.
  Changed bytes: client-summary.md, deployment-checklist.md, retention-config.json, test_retention.py; failed independent checks: none.
- **conservative / V2** regenerated: client-summary.md, deployment-checklist.md, retention-config.json, search-contract.json, test_retention.py.
  False negatives: none; false positives: search-contract.json.
  Changed bytes: client-summary.md, deployment-checklist.md, retention-config.json, test_retention.py; failed independent checks: none.
- **missing / V2** regenerated: client-summary.md, retention-config.json, test_retention.py.
  False negatives: deployment-checklist.md; false positives: none.
  Changed bytes: client-summary.md, retention-config.json, test_retention.py; failed independent checks: test_checklist_matches_client.

Complete-context tracking added 1 deliverable generation(s) for V2. The punctuation-only change caused 5 unnecessary deliverable generations in that baseline. These are counted executions and potential review candidates; human review time was not measured.

The missing baseline deliberately gives the deployment checklist a search dependency while its generator reads retention from the full record. A transitive dependency through the search projection establishes ordering, but does not carry retention content into the checklist's prompt hash. The reused checklist can still say 30 days while the configuration and generated retention tests say 7. The independent checklist check exposes this defect; fac alone cannot infer an undeclared file read.

The complete-context baseline actually reads and tracks the complete synthetic message and requirements record. It handles this controlled omission at extra regeneration cost. This experiment does not establish that conservative tracking is always safer: omitted context, external state, unsupported changes, and unvalidated outputs remain risks.

## Evidence and provenance

`summary.json` and each `measurement.json` contain exact commands, return codes, rebuilt sets, byte-change sets, mtimes, and source hashes. Stage folders preserve actual artifacts, normalized requirements, fac's `.facjson` prompt snapshots and per-target build logs, independent pytest logs, and JUnit results. `native-build-events.json` is copied from the corresponding slice of fac's native `.buildlog`.

Artifacts record their supporting requirement IDs and canonical value hashes. The validated requirements record binds the source-message path and raw SHA256. Stage snapshots retain the complete source for reproducing that chain, including the original source for reused outputs. Reuse is justified by unchanged semantic requirement values, not by pretending that a reused output was generated from V2.

## Limits and human review

- Selective reuse works here through small semantic JSON files declared as dependencies. fac has file-level dependencies; the application provides requirement-level projections. Both projections are reconsidered after a record change, even when downstream generation is suppressed.
- This pinned revision first checks timestamps and then compares included prompt content. Dependencies excluded with `include: false` can fail to change that hash. Equal or backdated timestamps may hide changes. No claim of general content-addressed safety is made.
- fac's built-in JSON Schema validation logs warnings for schema errors. The parser uses a strict, raising JSON Schema validator. Generation succeeded only if its command and independent tests succeeded.
- The default fac CLI can exit zero after a command fails. This harness explicitly enables `--debug.halt_on_error` to make command failures propagate. A compatibility probe records both default behavior and the enforced strict behavior.
- fac records its native content hash before final JSON/Markdown formatting. In the saved explicit run, the JSON artifacts' native content hashes differ from their finished-file hashes. Measurements therefore use independently computed SHA256 values of the finished files; native metadata is retained as evidence rather than treated as a final-file integrity guarantee.
- The main protocol runs command targets with one worker, disables fac automatic commits, and uses fixed parser/renderer code. It does not evaluate LLM variability, distributed concurrency, arbitrary English interpretation, or live provider calls.
- Five small deliverables and one controlled omission are a demonstration, not statistical evidence or production readiness. False-positive review candidates are measured; review minutes and operational deletion completion are not.
- A real deployment needs human review of requirement interpretation, complete storage/backup coverage, legal policy, and rollout. The checklist describes proposed work; it is not evidence that a deployment occurred.

## Follow-up questions

1. Can file-read auditing or a sandbox check that declared dependencies cover every actual generation input?
2. How should timestamp collisions and changes to commands, validators, or runtime versions invalidate outputs?
3. What is the best tradeoff between small semantic projections, context completeness, and measured review time?
4. Does the result hold with real LLM generation, multiple workers, and independently reviewed requirement extraction?

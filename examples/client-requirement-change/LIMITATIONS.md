# Scope, failed cases, and follow-up questions

## What the experiment can establish

For the fixed synthetic messages, renderer, environment, and dependency graph, the saved evidence supports selective reuse through canonical requirement files. The explicit baseline regenerates four affected deliverables and preserves unrelated search. Complete supplied-context tracking avoids the controlled omission but adds generation work. A missing retention dependency leaves a real stale checklist, caught by an independent assertion.

The five deliverables are the measurement unit. Parser/projection commands are counted separately. “Observed impact” means a native fac generation event, while byte changes and modification times are recorded independently. FN/FP are defined against the prewritten business oracle, not against whether the configured graph was traversed correctly.

## Deliberately failed cases

- **Missing checklist dependency:** configuration and generated tests update to 7; the checklist remains at 30. fac succeeds, but the independent checklist check fails. This is an experimental result, not an unexpected failing outer test.
- **Excluded prompt content:** the compatibility probe changes a declared input from 30 to 7 with `include: false`. The input becomes newer, but the prompt hash remains unchanged and fac reuses the old result. This option should not be used casually for content-bearing command dependencies in this pinned implementation.
- **Equal timestamps:** the compatibility probe changes an included input and explicitly sets its mtime equal to the existing output's mtime. The timestamp gate reports up to date and never requires content-based invalidation. This deliberately constructed clock case limits any broad safety claim.
- **Built-in schema validation:** the compatibility probe generates `{"days": 0}` against a positive-day schema. fac emits a schema warning and returns success. The application parser separately uses a raising validator, and its tests require failure for zero-day or unsupported-message inputs.
- **Default command-failure exit status:** the first outer verification had 22 passes and 2 failures because fac's default CLI returned zero even after the strict parser command failed. The failed run is preserved in `development/initial-failure.log` and `.xml`. The runner now enables upstream's existing `--debug.halt_on_error` option. A new probe asserts that the default CLI can exit zero while its printed state lists a `build_error`; strict-mode parser tests independently require a nonzero exit and no output record.

The executable probes live in `tests/test_fac_limits.py`. Their actual outcomes are recorded in the outer verification log and JUnit XML. The main experiment does not manipulate timestamps, force builds, delete cache metadata, or alter expected results to achieve selectivity.

## Boundaries

- Requirement extraction recognizes one fully specified synthetic-message grammar. It rejects extra or ambiguous text. It is not a general English requirements interpreter.
- All generation is deterministic, offline, and implemented with command targets. No inference-quality, long-horizon agent, or Groq performance claims follow.
- The tiny in-memory policy does not delete real stored conversations. A deployment checklist is a proposed engineering action, not evidence of storage or backup compliance.
- Dependencies are file-level. Application-authored semantic projections allow finer reuse but can themselves omit meaning or be implemented incorrectly.
- The conservative mode tracks only the complete **supplied** synthetic context. It cannot protect against files, network state, or environment values that were never supplied or recorded.
- Code/configuration and runtime are fixed during a trial. Renderer and schema files are tracked, but the experiment does not show that changing arbitrary command strings, runtimes, packages, or external tools reliably invalidates targets.
- In this revision, fac records native `hash_contents` before its final formatting step. Direct inspection of the saved explicit V2 run found mismatches for both JSON deliverables. The harness independently hashes finished files and preserves native metadata separately; native content hashes are not used as the integrity oracle.
- The main protocol uses one worker and disables automatic fac commits. Default parallel operation, committed-file timestamp behavior, cross-machine clocks, and restored caches need separate study.
- Build cost is counted as executions, not elapsed-model cost or dollars. Human-review candidate counts are proxies; time spent reviewing was not measured.
- The pinned upstream submodule supplies its tracked code and documentation. Its own nested submodules are unnecessary and were not fetched; a clean-machine dependency installation has not been independently tested. The upstream framework repository is not modified, and the tutorial's original root workflow is preserved.

## Follow-up questions for discussion

1. Could actual file-read auditing validate that every generation input was recorded?
2. Should changed content always be considered, even when timestamps are equal or older?
3. How should command, validator, projection, runtime, and package changes enter provenance and invalidation?
4. How should an independent requirements reviewer validate projection completeness?
5. Where is the useful balance between semantic projections and complete context, once actual review time is measured?
6. How do these results change with real LLM generation, multiple workers, and larger requirement graphs?

No claim of enterprise production readiness, a novel algorithm, or a completed thesis contribution is made.

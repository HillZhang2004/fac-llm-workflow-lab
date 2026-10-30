"""Fixed experiment protocol around the real fac CLI, never a scheduler.

Only fac chooses target order and reuse. Measurements come from its native
.buildlog plus independently captured file hashes, mtimes, and pytest results.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PIN = "2a099e6e97db390fa578a33edf9f66d61aec5818"
ARTIFACTS = ["retention-config.json", "test_retention.py", "deployment-checklist.md", "client-summary.md", "search-contract.json"]
MODES = ["explicit", "conservative", "missing"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_upstream():
    manifest = load(HERE / "vendor/source-manifest.json")
    assert manifest["commit"] == PIN
    for name, expected in manifest["files_sha256"].items():
        if sha(HERE / "vendor/fac" / name) != expected:
            raise RuntimeError(f"Vendored upstream source changed: {name}")
    return {"commit": PIN, "tracked_files_verified": len(manifest["files_sha256"]),
            "manifest_sha256": sha(HERE / "vendor/source-manifest.json")}


def environment(work):
    env = {key: value for key, value in os.environ.items() if not key.startswith("FAC_")}
    env.update(PYTHON=sys.executable, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONPATH=os.pathsep.join([str(HERE / "vendor/fac"), str(work)]))
    return env


def run(command, work, log, env=None):
    result = subprocess.run(command, cwd=work, env=env or environment(work), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    Path(log).write_text(result.stdout)
    return result


def prepare(work, mode):
    work.mkdir(parents=True)
    for name in ["workflow.py", "policy.py", "requirements.schema.json"]:
        shutil.copy2(HERE / name, work / name)
    config = "fac.yaml" if mode == "explicit" else f"fac.{mode}.yaml"
    shutil.copy2(HERE / config, work / "fac.yaml")
    (work / "mode.txt").write_text(mode + "\n")
    (work / ".gitignore").write_text(".fac.log\n__pycache__/\n.pytest_cache/\n")
    (work / "input").mkdir()
    shutil.copyfile(HERE / "inputs/v1.json", work / "input/client-message.json")
    shutil.copyfile(HERE / "inputs/v1.json", work / "input/baseline-message.json")
    # fac requires a Git repository even with automatic commits disabled.
    # This is a new, local-only repository with a synthetic identity.
    commands = [["git", "init", "-q"], ["git", "add", "."],
                ["git", "-c", "user.name=Synthetic Experiment", "-c", "user.email=synthetic@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic experiment seed"]]
    for command in commands:
        subprocess.run(command, cwd=work, check=True, capture_output=True, timeout=30)


def events(work):
    path = work / ".buildlog"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def snapshot(work):
    return {name: {"sha256": sha(work / "artifacts" / name),
                   "mtime_ns": (work / "artifacts" / name).stat().st_mtime_ns}
            for name in ARTIFACTS if (work / "artifacts" / name).exists()}


def stage(work, evidence, label, expected, expected_days):
    evidence.mkdir(parents=True)
    before, previous_events = snapshot(work), len(events(work))
    command = [sys.executable, "-B", "-m", "fac", "--no-auto_commit", "--debug.halt_on_error", "--max_workers", "1",
               *["artifacts/" + name for name in ARTIFACTS]]
    fac = run(command, work, evidence / "fac.log")
    if fac.returncode != 0:
        raise RuntimeError(f"fac failed; inspect {evidence / 'fac.log'}")
    after = snapshot(work)
    if len(after) != len(ARTIFACTS):
        raise RuntimeError(f"fac did not create every artifact: {evidence / 'fac.log'}")
    delta = events(work)[previous_events:]
    rebuilt = sorted({Path(event["path"]).name for event in delta if event["path"].startswith("artifacts/")})
    # Measurements never decide which targets fac should run.
    metrics = {
        "expected_impacted": sorted(expected), "observed_rebuilt": rebuilt,
        "false_negatives": sorted(set(expected) - set(rebuilt)),
        "false_positives": sorted(set(rebuilt) - set(expected)),
        "deliverable_rebuild_count": sum(event["path"].startswith("artifacts/") for event in delta),
        "total_fac_build_count": len(delta),
        "byte_changed": sorted(name for name in after if before.get(name, {}).get("sha256") != after[name]["sha256"]),
        "mtime_changed": sorted(name for name in after if before.get(name, {}).get("mtime_ns") != after[name]["mtime_ns"]),
    }
    for directory in ["artifacts", "requirements", "input"]:
        shutil.copytree(work / directory, evidence / directory)
    save(evidence / "native-build-events.json", delta)
    save(evidence / "before.json", before)
    save(evidence / "after.json", after)
    env = environment(work)
    env.update(DELIVERY_ROOT=str(work), EXPECTED_DAYS=str(expected_days))
    acceptance_command = [sys.executable, "-B", "-m", "pytest", "-q", "-o", "addopts=",
                          str(HERE / "acceptance.py"), str(work / "artifacts/test_retention.py"),
                          "--junitxml=" + str(evidence / "acceptance.xml")]
    acceptance = run(acceptance_command, work, evidence / "acceptance.log", env)
    cases = ET.parse(evidence / "acceptance.xml").findall(".//testcase")
    failed = sorted(case.attrib["name"] for case in cases if case.find("failure") is not None or case.find("error") is not None)
    skipped = sum(case.find("skipped") is not None for case in cases)
    metrics.update(stage=label, fac_returncode=fac.returncode, acceptance_returncode=acceptance.returncode,
                   acceptance_passed=len(cases) - len(failed) - skipped, acceptance_failed=failed, acceptance_skipped=skipped,
                   source_sha256=sha(work / "input/client-message.json"),
                   commands={"fac": command, "acceptance": acceptance_command},
                   expected_days=expected_days)
    save(evidence / "measurement.json", metrics)
    return metrics


def report(summary, output):
    lines = ["# Client requirement change: measured impact", "",
             "All customer messages and business data are synthetic. Deterministic command targets were executed by unmodified fac.", "",
             f"Pinned upstream commit: `{PIN}`; {summary['upstream']['tracked_files_verified']} tracked source files verified by SHA256.",
             f"Expected-impact table was frozen before execution: `{summary['expected_impact_sha256']}`.", "",
             "The validated retention requirement changed from **30 days to 7 days**. Search and response-quality values did not change. A display-name period is the isolated nonmaterial control.", "",
             "Observed impact below means a native fac generation event. False positives and false negatives compare regeneration against the independent business-impact table, not against the dependency graph.", "",
             "| Mode | Stage | Expected | Rebuilt | FN | FP | Total fac builds | Acceptance |",
             "|---|---|---:|---:|---:|---:|---:|---|"]
    for mode in MODES:
        for label in ["initial", "unchanged", "v2", "cosmetic_only"]:
            m = summary["modes"][mode][label]
            accept = f"{m['acceptance_passed']} passed, {len(m['acceptance_failed'])} failed, {m['acceptance_skipped']} skipped"
            lines.append(f"| {mode} | {label} | {len(m['expected_impacted'])} | {m['deliverable_rebuild_count']} | {len(m['false_negatives'])} | {len(m['false_positives'])} | {m['total_fac_build_count']} | {accept} |")
    lines += ["", "## Confirmed observations", ""]
    for mode in MODES:
        m = summary["modes"][mode]["v2"]
        lines += [f"- **{mode} / V2** regenerated: {', '.join(m['observed_rebuilt']) or 'none'}.",
                  f"  False negatives: {', '.join(m['false_negatives']) or 'none'}; false positives: {', '.join(m['false_positives']) or 'none'}.",
                  f"  Changed bytes: {', '.join(m['byte_changed']) or 'none'}; failed independent checks: {', '.join(m['acceptance_failed']) or 'none'}."]
    explicit = summary["modes"]["explicit"]["v2"]
    conservative = summary["modes"]["conservative"]["v2"]
    control = summary["modes"]["conservative"]["cosmetic_only"]
    lines += ["", f"Complete-context tracking added {conservative['deliverable_rebuild_count'] - explicit['deliverable_rebuild_count']} deliverable generation(s) for V2. The punctuation-only change caused {control['deliverable_rebuild_count']} unnecessary deliverable generations in that baseline. These are counted executions and potential review candidates; human review time was not measured.", "",
              "The missing baseline deliberately gives the deployment checklist a search dependency while its generator reads retention from the full record. A transitive dependency through the search projection establishes ordering, but does not carry retention content into the checklist's prompt hash. The reused checklist can still say 30 days while the configuration and generated retention tests say 7. The independent checklist check exposes this defect; fac alone cannot infer an undeclared file read.", "",
              "The complete-context baseline actually reads and tracks the complete synthetic message and requirements record. It handles this controlled omission at extra regeneration cost. This experiment does not establish that conservative tracking is always safer: omitted context, external state, unsupported changes, and unvalidated outputs remain risks.", "",
              "## Evidence and provenance", "",
              "`summary.json` and each `measurement.json` contain exact commands, return codes, rebuilt sets, byte-change sets, mtimes, and source hashes. Stage folders preserve actual artifacts, normalized requirements, fac's `.facjson` prompt snapshots and per-target build logs, independent pytest logs, and JUnit results. `native-build-events.json` is copied from the corresponding slice of fac's native `.buildlog`.", "",
              "Artifacts record their supporting requirement IDs and canonical value hashes. The validated requirements record binds the source-message path and raw SHA256. Stage snapshots retain the complete source for reproducing that chain, including the original source for reused outputs. Reuse is justified by unchanged semantic requirement values, not by pretending that a reused output was generated from V2.", "",
              "## Limits and human review", "",
              "- Selective reuse works here through small semantic JSON files declared as dependencies. fac has file-level dependencies; the application provides requirement-level projections. Both projections are reconsidered after a record change, even when downstream generation is suppressed.",
              "- This pinned revision first checks timestamps and then compares included prompt content. Dependencies excluded with `include: false` can fail to change that hash. Equal or backdated timestamps may hide changes. No claim of general content-addressed safety is made.",
              "- fac's built-in JSON Schema validation logs warnings for schema errors. The parser uses a strict, raising JSON Schema validator. Generation succeeded only if its command and independent tests succeeded.",
              "- The default fac CLI can exit zero after a command fails. This harness explicitly enables `--debug.halt_on_error` to make command failures propagate. A compatibility probe records both default behavior and the enforced strict behavior.",
              "- fac records its native content hash before final JSON/Markdown formatting. In the saved explicit run, the JSON artifacts' native content hashes differ from their finished-file hashes. Measurements therefore use independently computed SHA256 values of the finished files; native metadata is retained as evidence rather than treated as a final-file integrity guarantee.",
              "- The main protocol runs command targets with one worker, disables fac automatic commits, and uses fixed parser/renderer code. It does not evaluate LLM variability, distributed concurrency, arbitrary English interpretation, or live provider calls.",
              "- Five small deliverables and one controlled omission are a demonstration, not statistical evidence or production readiness. False-positive review candidates are measured; review minutes and operational deletion completion are not.",
              "- A real deployment needs human review of requirement interpretation, complete storage/backup coverage, legal policy, and rollout. The checklist describes proposed work; it is not evidence that a deployment occurred.", "",
              "## Follow-up questions", "",
              "1. Can file-read auditing or a sandbox check that declared dependencies cover every actual generation input?",
              "2. How should timestamp collisions and changes to commands, validators, or runtime versions invalidate outputs?",
              "3. What is the best tradeoff between small semantic projections, context completeness, and measured review time?",
              "4. Does the result hold with real LLM generation, multiple workers, and independently reviewed requirement extraction?", ""]
    (output / "impact-report.md").write_text("\n".join(lines))


def run_experiment(output, progress=print):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Use a new output directory to preserve prior evidence: {output}")
    upstream = verify_upstream()
    expected = load(HERE / "expected-impact.json")
    frozen = sha(HERE / "expected-impact.json")
    output.mkdir(parents=True)
    shutil.copyfile(HERE / "expected-impact.json", output / "expected-impact.frozen.json")
    summary = {"upstream": upstream, "expected_impact_sha256": frozen, "modes": {},
               "python_version": sys.version, "pytest_version": importlib.metadata.version("pytest")}
    for mode in MODES:
        progress(f"Running {mode}: V1, unchanged rerun, V2, and independent punctuation control", flush=True)
        work = output / mode / "material/work"
        prepare(work, mode)
        stage_dir = output / mode / "material/evidence"
        result = {}
        result["initial"] = stage(work, stage_dir / "initial", "initial", expected["initial"], 30)
        result["unchanged"] = stage(work, stage_dir / "unchanged", "unchanged", expected["unchanged"], 30)
        shutil.copyfile(HERE / "inputs/v2.json", work / "input/client-message.json")
        result["v2"] = stage(work, stage_dir / "v2", "v2", expected["v2"], 7)
        # Independent branch from V1, not V2 -> cosmetic (which would undo
        # retention and confound the negative control).
        cosmetic = output / mode / "cosmetic/work"
        prepare(cosmetic, mode)
        stage(cosmetic, output / mode / "cosmetic/evidence/initial", "initial", expected["initial"], 30)
        shutil.copyfile(HERE / "inputs/cosmetic-only.json", cosmetic / "input/client-message.json")
        result["cosmetic_only"] = stage(cosmetic, output / mode / "cosmetic/evidence/cosmetic_only", "cosmetic_only", expected["cosmetic_only"], 30)
        summary["modes"][mode] = result
    assert sha(HERE / "expected-impact.json") == frozen, "Expected-impact table changed during execution"
    save(output / "summary.json", summary)
    report(summary, output)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results")
    args = parser.parse_args()
    run_experiment(args.output)
    print(f"Evidence and report: {args.output.resolve()}")

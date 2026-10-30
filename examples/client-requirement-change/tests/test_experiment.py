"""Reproduce the experiment from fresh repositories and check independent oracles."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("experiment", ROOT / "experiment.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


@pytest.fixture(scope="session")
def fresh(tmp_path_factory):
    output = tmp_path_factory.mktemp("client-change") / "results"
    summary = experiment.run_experiment(output)
    return summary, output


@pytest.mark.parametrize("mode", experiment.MODES)
def test_v1_builds_five_correct_deliverables(fresh, mode):
    summary, _ = fresh
    m = summary["modes"][mode]["initial"]
    assert set(m["observed_rebuilt"]) == set(experiment.ARTIFACTS)
    assert m["total_fac_build_count"] == 8  # record + two projections + five artifacts
    assert m["acceptance_returncode"] == 0
    assert m["acceptance_passed"] == 5 and m["acceptance_skipped"] == 1


@pytest.mark.parametrize("mode", experiment.MODES)
def test_unchanged_rerun_generates_nothing(fresh, mode):
    summary, _ = fresh
    m = summary["modes"][mode]["unchanged"]
    assert m["observed_rebuilt"] == []
    assert m["total_fac_build_count"] == 0
    assert m["byte_changed"] == [] and m["mtime_changed"] == []
    assert m["acceptance_returncode"] == 0


@pytest.mark.parametrize("mode", experiment.MODES)
def test_v2_detects_thirty_to_seven_days_and_keeps_search_valid(fresh, mode):
    summary, output = fresh
    evidence = output / mode / "material/evidence"
    before = experiment.load(evidence / "initial/requirements/record.json")
    after = experiment.load(evidence / "v2/requirements/record.json")
    assert before["requirements"]["REQ-RETENTION"]["days"] == 30
    assert after["requirements"]["REQ-RETENTION"]["days"] == 7
    for key in ["REQ-SEARCH", "REQ-QUALITY"]:
        assert before["requirements"][key] == after["requirements"][key]
    assert "test_search_and_response_quality_remain_valid" not in summary["modes"][mode]["v2"]["acceptance_failed"]
    assert "test_seven_day_policy_independent_of_generated_tests" not in summary["modes"][mode]["v2"]["acceptance_failed"]
    assert summary["modes"][mode]["v2"]["acceptance_skipped"] == 0


def test_explicit_rebuilds_all_and_only_affected_outputs(fresh):
    summary, _ = fresh
    m = summary["modes"]["explicit"]["v2"]
    assert m["deliverable_rebuild_count"] == 4
    assert m["false_negatives"] == m["false_positives"] == []
    assert m["byte_changed"] == m["expected_impacted"]
    assert m["mtime_changed"] == m["expected_impacted"]
    assert m["acceptance_returncode"] == 0 and m["acceptance_passed"] == 6


def test_missing_dependency_produces_actual_unsafe_reuse(fresh):
    summary, output = fresh
    m = summary["modes"]["missing"]["v2"]
    assert m["deliverable_rebuild_count"] == 3
    assert m["false_negatives"] == ["deployment-checklist.md"]
    assert m["false_positives"] == []
    assert m["acceptance_returncode"] == 1
    assert m["acceptance_failed"] == ["test_checklist_matches_client"]
    assert m["acceptance_passed"] == 5
    evidence = output / "missing/material/evidence"
    first = experiment.load(evidence / "initial/after.json")
    after = experiment.load(evidence / "v2/after.json")
    assert first["deployment-checklist.md"] == after["deployment-checklist.md"]
    assert "retention to 30 days" in (evidence / "v2/artifacts/deployment-checklist.md").read_text()
    assert experiment.load(evidence / "v2/artifacts/retention-config.json")["retention_days"] == 7


def test_conservative_cost_is_observed_even_when_bytes_are_identical(fresh):
    summary, _ = fresh
    m = summary["modes"]["conservative"]["v2"]
    assert m["deliverable_rebuild_count"] == 5
    assert m["false_positives"] == ["search-contract.json"]
    assert m["false_negatives"] == []
    assert "search-contract.json" not in m["byte_changed"]
    assert "search-contract.json" in m["mtime_changed"]
    assert m["acceptance_returncode"] == 0


@pytest.mark.parametrize("mode,count", [("explicit", 0), ("conservative", 5), ("missing", 0)])
def test_isolated_nonmaterial_negative_control(fresh, mode, count):
    summary, _ = fresh
    m = summary["modes"][mode]["cosmetic_only"]
    assert m["expected_impacted"] == []
    assert m["deliverable_rebuild_count"] == count
    assert len(m["false_positives"]) == count
    assert m["byte_changed"] == []
    assert m["acceptance_returncode"] == 0


def test_inputs_are_synthetic_and_control_changes_only_punctuation():
    v1 = experiment.load(ROOT / "inputs/v1.json")
    v2 = experiment.load(ROOT / "inputs/v2.json")
    control = experiment.load(ROOT / "inputs/cosmetic-only.json")
    assert v1["synthetic"] is v2["synthetic"] is control["synthetic"] is True
    assert control == {**v1, "display_name": v1["display_name"] + "."}
    assert v2 == {**control, "text": control["text"].replace("30 days", "7 days")}


def test_provenance_binds_values_and_source_snapshots(fresh):
    _, output = fresh
    stage = output / "explicit/material/evidence/v2"
    record = experiment.load(stage / "requirements/record.json")
    assert record["source"]["sha256"] == experiment.sha(stage / "input/client-message.json")
    for name in ["retention-config.json", "search-contract.json"]:
        for key, provenance in experiment.load(stage / "artifacts" / name)["provenance"].items():
            value = record["requirements"][key]
            canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            assert provenance == {"value": value, "sha256": hashlib.sha256(canonical).hexdigest()}


def test_native_logs_and_report_agree_with_frozen_expectations(fresh):
    summary, output = fresh
    assert summary["expected_impact_sha256"] == experiment.sha(ROOT / "expected-impact.json")
    assert experiment.sha(output / "expected-impact.frozen.json") == summary["expected_impact_sha256"]
    for mode in experiment.MODES:
        for label in ["initial", "unchanged", "v2"]:
            events = experiment.load(output / mode / "material/evidence" / label / "native-build-events.json")
            m = summary["modes"][mode][label]
            assert m["total_fac_build_count"] == len(events)
            assert m["deliverable_rebuild_count"] == sum(e["path"].startswith("artifacts/") for e in events)
    report = (output / "impact-report.md").read_text()
    assert "## Confirmed observations" in report and "## Limits and human review" in report
    assert "human review time was not measured" in report
    assert "test_checklist_matches_client" in report


def test_pinned_upstream_is_unmodified():
    result = experiment.verify_upstream()
    assert result["commit"] == "2a099e6e97db390fa578a33edf9f66d61aec5818"
    assert result["tracked_files_verified"] == 76

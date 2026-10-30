"""Independent business assertions. Never generated or edited by the workflow."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(os.environ["DELIVERY_ROOT"])
EXPECTED_DAYS = int(os.environ["EXPECTED_DAYS"])
spec = importlib.util.spec_from_file_location("delivery_policy", ROOT / "policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def artifact(name):
    return (ROOT / "artifacts" / name).read_text()


def test_configuration_matches_client():
    config = json.loads(artifact("retention-config.json"))
    assert config["retention_days"] == EXPECTED_DAYS
    assert config["delete_at_boundary"] is True


def test_seven_day_policy_independent_of_generated_tests():
    if EXPECTED_DAYS != 7:
        pytest.skip("Seven-day oracle applies only after the material change")
    config = json.loads(artifact("retention-config.json"))
    now = datetime(2030, 1, 31, tzinfo=timezone.utc)
    # Expected survivors are literal business-oracle values, not computed
    # from the generated configuration or generated acceptance test.
    ages = {"new": 0, "six_days": 6 * 86400, "just_under_seven": 7 * 86400 - 1,
            "exactly_seven": 7 * 86400, "just_over_seven": 7 * 86400 + 1,
            "eight_days": 8 * 86400, "twenty_nine_days": 29 * 86400, "thirty_days": 30 * 86400}
    rows = [{"id": key, "created_at": now - timedelta(seconds=age)} for key, age in ages.items()]
    assert [row["id"] for row in policy.retained(rows, now, config)] == ["new", "six_days", "just_under_seven"]


def test_checklist_matches_client():
    text = artifact("deployment-checklist.md")
    assert f"retention to {EXPECTED_DAYS} days" in text
    assert f"beyond {EXPECTED_DAYS} days" in text


def test_summary_matches_client():
    summary = artifact("client-summary.md")
    assert f"retention period is {EXPECTED_DAYS} days" in summary
    if EXPECTED_DAYS == 7:
        assert "reduces retention from 30 days to 7 days" in summary


def test_search_and_response_quality_remain_valid():
    contract = json.loads(artifact("search-contract.json"))
    assert contract["search"] == {"enabled": True, "top_k": 2}
    assert contract["quality"] == {"query": "password reset", "expected_top_id": "KB-RESET",
                                   "citation_required": True, "max_response_words": 40}
    hits, response = policy.answer("password reset", contract)
    assert len(hits) == 2
    assert hits[0]["id"] == "KB-RESET"
    assert "[KB-RESET]" in response
    assert len(response.split()) <= 40

"""Pure file transformations invoked by fac; this module never schedules work."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n" if not isinstance(value, str) else value)


def parse_message():
    path = Path("input/client-message.json")
    raw = read(path)
    if raw.get("synthetic") is not True or raw.get("message_id") != "SYNTH-CR-001":
        raise ValueError("Only the synthetic fixture format is accepted")
    # Full matching rejects ambiguous, missing, duplicate, and extra instructions.
    match = re.fullmatch(
        r"REQ-RETENTION: Retain conversation history for (\d+) days\. Delete records at or beyond the retention boundary\.\n"
        r"REQ-SEARCH: Provide knowledge-base search with top_k=(\d+)\.\n"
        r"REQ-QUALITY: The top result for '([^']+)' must be ([A-Z-]+)\. "
        r"Responses must cite the selected document and contain at most (\d+) words\.", raw["text"])
    if match is None:
        raise ValueError("Unsupported or ambiguous synthetic requirements message")
    days, top_k, query, top_id, max_words = match.groups()
    record = {
        "synthetic": True,
        "source": {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "message_id": raw["message_id"]},
        "display_name": raw["display_name"],
        "requirements": {
            "REQ-RETENTION": {"days": int(days), "delete_at_boundary": True},
            "REQ-SEARCH": {"enabled": True, "top_k": int(top_k)},
            "REQ-QUALITY": {"query": query, "expected_top_id": top_id, "citation_required": True, "max_response_words": int(max_words)},
        },
    }
    # fac's schema check only warns in this revision; our validation must raise.
    Draft202012Validator(read("requirements.schema.json")).validate(record)
    return record


def project(kind):
    requirements = read("requirements/record.json")["requirements"]
    ids = ["REQ-RETENTION"] if kind == "retention" else ["REQ-SEARCH", "REQ-QUALITY"]
    return {key: requirements[key] for key in ids}


def generate(name):
    mode = Path("mode.txt").read_text().strip()
    # The conservative generator really loads the entire context; it does not
    # get fictional extra dependency edges that no generation step can read.
    if mode == "conservative":
        context = {"message": read("input/client-message.json"), "record": read("requirements/record.json")}
        requirements = context["record"]["requirements"]
    elif mode == "missing" and name == "deployment-checklist.md":
        # Search's transitive record dependency establishes build order, but
        # its semantic projection hides retention changes from this target.
        requirements = read("requirements/record.json")["requirements"]
    elif name == "search-contract.json":
        requirements = read("requirements/search.json")
    else:
        requirements = read("requirements/retention.json")
    ids = ["REQ-SEARCH", "REQ-QUALITY"] if name == "search-contract.json" else ["REQ-RETENTION"]
    provenance = {key: {"value": requirements[key], "sha256": digest(requirements[key])} for key in ids}
    if name == "search-contract.json":
        return {"synthetic": True, "search": requirements["REQ-SEARCH"], "quality": requirements["REQ-QUALITY"], "provenance": provenance}
    days = requirements["REQ-RETENTION"]["days"]
    if name == "retention-config.json":
        return {"retention_days": days, "delete_at_boundary": True, "provenance": provenance}
    if name == "test_retention.py":
        return f'''# Generated acceptance test; supporting requirement: REQ-RETENTION.
# Requirement value SHA256: {digest(requirements['REQ-RETENTION'])}
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from policy import retained


def test_generated_retention_contract():
    config = json.loads(Path("artifacts/retention-config.json").read_text())
    assert config["retention_days"] == {days}
    now = datetime(2030, 1, 31, tzinfo=timezone.utc)
    records = [{{"id": "recent", "created_at": now - timedelta(days={days}) + timedelta(seconds=1)}},
               {{"id": "boundary", "created_at": now - timedelta(days={days})}},
               {{"id": "old", "created_at": now - timedelta(days={days + 1})}}]
    assert [row["id"] for row in retained(records, now, config)] == ["recent"]
'''
    footer = f"\nSupporting requirement: REQ-RETENTION; value SHA256: `{digest(requirements['REQ-RETENTION'])}`.\n"
    if name == "deployment-checklist.md":
        return f"# Synthetic deployment checklist\n\n- Set conversation history retention to {days} days.\n- Delete records at or beyond {days} days.\n- Run retention boundary tests before rollout.\n- Human review required: verify all real storage, backups, and deletion jobs.\n" + footer
    if name == "client-summary.md":
        baseline_path = Path("input/baseline-message.json")
        baseline = read(baseline_path)
        if baseline.get("synthetic") is not True:
            raise ValueError("Historical agreement must be synthetic")
        previous_days = int(re.search(r"REQ-RETENTION: Retain conversation history for (\d+) days\.", baseline["text"]).group(1))
        change = (f"The client change reduces retention from {previous_days} days to {days} days."
                  if days != previous_days else "This is the initial agreement; no retention change has been requested.")
        historical_source = f"\nPrevious agreement: REQ-RETENTION in `{baseline_path}`; source SHA256: `{hashlib.sha256(baseline_path.read_bytes()).hexdigest()}`.\n"
        return f"# Synthetic client change summary\n\n{change}\n\nThe agreed conversation retention period is {days} days. Records at or beyond this age must be deleted.\nKnowledge search and response-quality criteria remain as specified.\nThis prototype verifies local fixtures; a real rollout requires engineering review.\n" + footer + historical_source
    raise ValueError(name)


def main():
    action = sys.argv[1]
    target = os.environ["FAC_PATH"]
    if action == "parse":
        value = parse_message()
    elif action == "project":
        value = project(sys.argv[2])
    elif action == "generate":
        value = generate(Path(target).name)
    else:
        raise ValueError(action)
    write(target, value)


if __name__ == "__main__":
    main()

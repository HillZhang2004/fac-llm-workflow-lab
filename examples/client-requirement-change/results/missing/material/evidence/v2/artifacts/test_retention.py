# Generated acceptance test; supporting requirement: REQ-RETENTION.
# Requirement value SHA256: b33bf8a04c9cac0625faf209efe8f22313e06c1020dcf60c812f09a48507294e
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from policy import retained


def test_generated_retention_contract():
    config = json.loads(Path("artifacts/retention-config.json").read_text())
    assert config["retention_days"] == 7
    now = datetime(2030, 1, 31, tzinfo=timezone.utc)
    records = [{"id": "recent", "created_at": now - timedelta(days=7) + timedelta(seconds=1)},
               {"id": "boundary", "created_at": now - timedelta(days=7)},
               {"id": "old", "created_at": now - timedelta(days=8)}]
    assert [row["id"] for row in retained(records, now, config)] == ["recent"]

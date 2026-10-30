# Generated acceptance test; supporting requirement: REQ-RETENTION.
# Requirement value SHA256: 5854e491c17eba7de8551c65259d9017e58526d175b568b5c48e8bca3d21f345
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from policy import retained


def test_generated_retention_contract():
    config = json.loads(Path("artifacts/retention-config.json").read_text())
    assert config["retention_days"] == 30
    now = datetime(2030, 1, 31, tzinfo=timezone.utc)
    records = [{"id": "recent", "created_at": now - timedelta(days=30) + timedelta(seconds=1)},
               {"id": "boundary", "created_at": now - timedelta(days=30)},
               {"id": "old", "created_at": now - timedelta(days=31)}]
    assert [row["id"] for row in retained(records, now, config)] == ["recent"]

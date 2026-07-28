"""Focused JSONL record and append tests for the shared hook log writer."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from hook_loader import load_hook

log_writer = load_hook("utils/log_writer.py")


def test_build_record_has_schema_and_promotes_hook_fields() -> None:
    payload = {
        "session_id": "session-1",
        "cwd": "/tmp/project",
        "tool_name": "Bash",
        "tool_use_id": "tool-1",
        "nested": {"value": "kept"},
    }

    record = log_writer.build_record(
        "PostToolUse",
        payload,
        now=datetime(2026, 7, 28, 14, 38, 7, 355000, tzinfo=UTC),
    )

    assert record["schema_version"] == 1
    assert record["timestamp"] == 1785249487355
    assert record["ts_iso"] == "2026-07-28T14:38:07.355Z"
    assert record["hook_event_type"] == "PostToolUse"
    assert record["session_id"] == "session-1"
    assert record["tool_name"] == "Bash"
    assert record["payload"] == payload


def test_append_jsonl_creates_parent_and_writes_one_parseable_record_per_line(tmp_path: Path) -> None:
    log_path = tmp_path / "nested" / "events.jsonl"

    for number in range(3):
        log_writer.append_jsonl(log_path, {"schema_version": 1, "number": number})

    assert [json.loads(line) for line in log_path.read_text().splitlines()] == [
        {"schema_version": 1, "number": 0},
        {"schema_version": 1, "number": 1},
        {"schema_version": 1, "number": 2},
    ]


def test_concurrent_appends_do_not_interleave_jsonl_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    start = threading.Barrier(2)

    def _append_records(worker: int) -> None:
        start.wait()
        for number in range(200):
            log_writer.append_jsonl(log_path, {"schema_version": 1, "worker": worker, "number": number})

    workers = [threading.Thread(target=_append_records, args=(worker,)) for worker in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert len(records) == 400
    assert {(record["worker"], record["number"]) for record in records} == {
        (worker, number) for worker in range(2) for number in range(200)
    }

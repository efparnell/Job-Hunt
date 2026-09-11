import json
from automation.opportunity_monitor.log_store import append_entry, read_all_entries


def test_append_and_read_roundtrip(tmp_path):
    log_path = tmp_path / "opportunity_log.jsonl"
    entry = {
        "company": "Example Co",
        "role": "Director of Operations",
        "source": "career_page",
        "score": 85,
        "score_reasoning": "Strong operating-complexity and leadership-mandate fit.",
        "alerted": True,
    }
    append_entry(log_path, entry)
    entries = read_all_entries(log_path)
    assert len(entries) == 1
    assert entries[0]["company"] == "Example Co"
    assert entries[0]["score"] == 85


def test_append_multiple_entries_stays_one_json_object_per_line(tmp_path):
    log_path = tmp_path / "opportunity_log.jsonl"
    append_entry(log_path, {"company": "A", "score": 60})
    append_entry(log_path, {"company": "B", "score": 90})
    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["company"] == "A"
    assert json.loads(lines[1])["company"] == "B"


def test_read_all_entries_on_missing_file_returns_empty_list(tmp_path):
    log_path = tmp_path / "does_not_exist.jsonl"
    assert read_all_entries(log_path) == []

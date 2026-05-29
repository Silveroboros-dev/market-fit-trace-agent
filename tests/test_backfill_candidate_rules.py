import json

from scripts.backfill_candidate_rules import backfill_candidate_dir


def test_backfill_candidate_dir_updates_rules_and_preserves_retrieval_identity(tmp_path):
    candidate_dir = tmp_path / "evals" / "retrieval_candidates" / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    _write_json(
        candidate_dir / "source.json",
        {
            "case_id": "case-1",
            "source_text": "A thesis about Hormuz reopening.",
        },
    )
    _write_jsonl(
        candidate_dir / "market_snapshots.jsonl",
        [
            {
                "market_id": "m1",
                "title": "Market 1",
                "resolution_rules": "",
                "known_fit_risks": [
                    "dynamic_polydata_retrieval",
                    "missing_resolution_rules",
                ],
            }
        ],
    )
    _write_jsonl(
        candidate_dir / "market_rules_snapshots.jsonl",
        [
            {
                "market_id": "m1",
                "resolution_rules": "",
                "rules_status": "missing",
                "retrieval_id": "retr-1",
                "snapshot_id": "snapshot-1",
                "as_of_ts": "2026-05-26T00:00:00+00:00",
            }
        ],
    )
    _write_json(
        candidate_dir / "run_result.json",
        {
            "market_retrieval": {
                "retrieval_id": "agent-retr-1",
                "snapshot_id": "agent-snapshot-1",
                "as_of_ts": "2026-05-26T01:00:00+00:00",
                "market_ids_considered": ["m2"],
            }
        },
    )

    summary = backfill_candidate_dir(
        candidate_dir,
        rules_lookup={
            "m1": {
                "id": "m1",
                "question": "Market 1",
                "description": "This market resolves Yes if the blockade is lifted.",
                "resolution_source": "Official announcement",
                "question_id": "question-1",
                "condition_id": "condition-1",
                "market_slug": "market-1",
            },
            "m2": {
                "id": "m2",
                "question": "Agent market 2",
                "description": "This agent market resolves on a public announcement.",
            }
        },
        backfilled_at_utc="2026-05-29T12:00:00+00:00",
    )

    markets = _read_jsonl(candidate_dir / "market_snapshots.jsonl")
    rules = _read_jsonl(candidate_dir / "market_rules_snapshots.jsonl")
    agent_rules = _read_jsonl(candidate_dir / "agent_market_rules_snapshots.jsonl")

    assert summary["backfilled_count"] == 1
    assert summary["rules_present_after"] == 1
    assert summary["rules_missing_after"] == 0
    assert summary["agent_market_count"] == 1
    assert summary["agent_rules_present_after"] == 1
    assert summary["agent_rules_missing_after"] == 0
    assert markets[0]["resolution_rules"] == "This market resolves Yes if the blockade is lifted."
    assert markets[0]["known_fit_risks"] == ["dynamic_polydata_retrieval"]
    assert rules[0]["resolution_rules"] == "This market resolves Yes if the blockade is lifted."
    assert rules[0]["rules_status"] == "present"
    assert rules[0]["rules_source"] == "polydata.markets.description"
    assert rules[0]["rules_backfilled_at_utc"] == "2026-05-29T12:00:00+00:00"
    assert rules[0]["resolution_source"] == "Official announcement"
    assert rules[0]["question_id"] == "question-1"
    assert rules[0]["condition_id"] == "condition-1"
    assert rules[0]["market_slug"] == "market-1"
    assert rules[0]["retrieval_id"] == "retr-1"
    assert rules[0]["snapshot_id"] == "snapshot-1"
    assert rules[0]["as_of_ts"] == "2026-05-26T00:00:00+00:00"
    assert agent_rules[0]["market_id"] == "m2"
    assert agent_rules[0]["resolution_rules"] == (
        "This agent market resolves on a public announcement."
    )
    assert agent_rules[0]["retrieval_id"] == "agent-retr-1"
    assert agent_rules[0]["snapshot_id"] == "agent-snapshot-1"
    assert agent_rules[0]["as_of_ts"] == "2026-05-26T01:00:00+00:00"
    _assert_no_strict_expected_labels(summary)
    _assert_no_strict_expected_labels(markets)
    _assert_no_strict_expected_labels(rules)
    _assert_no_strict_expected_labels(agent_rules)


def test_backfill_candidate_dir_dry_run_does_not_write(tmp_path):
    candidate_dir = tmp_path / "evals" / "retrieval_candidates" / "2026-05-26" / "case-1"
    candidate_dir.mkdir(parents=True)
    _write_json(candidate_dir / "source.json", {"case_id": "case-1", "source_text": "x"})
    _write_jsonl(
        candidate_dir / "market_snapshots.jsonl",
        [
            {
                "market_id": "m1",
                "resolution_rules": "",
                "known_fit_risks": ["missing_resolution_rules"],
            }
        ],
    )
    _write_jsonl(
        candidate_dir / "market_rules_snapshots.jsonl",
        [{"market_id": "m1", "resolution_rules": "", "rules_status": "missing"}],
    )

    summary = backfill_candidate_dir(
        candidate_dir,
        rules_lookup={"m1": {"description": "Rules now present."}},
        backfilled_at_utc="2026-05-29T12:00:00+00:00",
        dry_run=True,
    )

    markets = _read_jsonl(candidate_dir / "market_snapshots.jsonl")
    rules = _read_jsonl(candidate_dir / "market_rules_snapshots.jsonl")

    assert summary["backfilled_count"] == 1
    assert markets[0]["resolution_rules"] == ""
    assert markets[0]["known_fit_risks"] == ["missing_resolution_rules"]
    assert rules[0]["resolution_rules"] == ""
    assert rules[0]["rules_status"] == "missing"
    assert not (candidate_dir / "agent_market_rules_snapshots.jsonl").exists()


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_no_strict_expected_labels(payload):
    text = json.dumps(payload)
    assert "expected_fit_class" not in text
    assert "expected_best_market_id" not in text

import json
from pathlib import Path

from scripts.build_stress_dataset import build_stress_dataset

STRICT_GOLDEN_DIRS = [
    Path("evals/market_fit_v1"),
    Path("evals/market_fit_v2"),
    Path("evals/market_fit_v4_live_promoted"),
]

REQUIRED_FIELDS = {
    "case_id",
    "schema_version",
    "thesis",
    "market",
    "expected_fit_class",
    "mismatch_family",
    "trap_description",
    "truth_scope",
    "expected_label_source",
    "canonical_truth",
}

REQUIRED_MARKET_FIELDS = {
    "market_id",
    "title",
    "venue",
    "description",
    "resolution_rules",
    "close_date",
    "outcomes",
    "known_fit_risks",
    "entity_tags",
}

VALID_FIT_CLASSES = {"direct", "indirect", "weak_proxy", "no_clean_expression"}

VALID_FAMILIES = {
    "event_stage_mismatch",
    "metric_mismatch",
    "horizon_mismatch",
    "entity_mismatch",
    "causal_mechanism",
    "composite_thesis",
    "inverse_framing",
}


def test_build_stress_dataset_produces_40_valid_cases():
    cases = build_stress_dataset()
    assert len(cases) == 40

    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids)), "Duplicate case_id"

    for case in cases:
        missing = REQUIRED_FIELDS - set(case.keys())
        assert not missing, f"{case['case_id']} missing fields: {missing}"

        assert case["expected_fit_class"] in VALID_FIT_CLASSES, (
            f"{case['case_id']} invalid fit class: {case['expected_fit_class']}"
        )
        assert case["mismatch_family"] in VALID_FAMILIES, (
            f"{case['case_id']} invalid family: {case['mismatch_family']}"
        )

        market = case["market"]
        missing_m = REQUIRED_MARKET_FIELDS - set(market.keys())
        assert not missing_m, f"{case['case_id']} market missing: {missing_m}"


def test_stress_cases_have_resolution_rules():
    cases = build_stress_dataset()
    for case in cases:
        rules = case["market"]["resolution_rules"]
        assert isinstance(rules, str) and len(rules) > 20, (
            f"{case['case_id']} has empty or trivial resolution_rules"
        )


def test_stress_cases_are_not_strict_goldens():
    cases = build_stress_dataset()
    for case in cases:
        assert case["canonical_truth"] is False, (
            f"{case['case_id']} must have canonical_truth=false"
        )
        assert case["truth_scope"] == "synthetic_expected_label", (
            f"{case['case_id']} must have truth_scope=synthetic_expected_label"
        )
        assert case["expected_label_source"] == "constructed_template", (
            f"{case['case_id']} must have expected_label_source=constructed_template"
        )


def test_stress_results_do_not_mutate_goldens(tmp_path):
    """Verify the builder writes only to the stress output dir, not golden dirs."""
    # Snapshot golden dir mtimes before build
    golden_snapshots = {}
    for d in STRICT_GOLDEN_DIRS:
        if d.exists():
            golden_snapshots[d] = {f.name: f.stat().st_mtime for f in d.iterdir() if f.is_file()}

    # Build to a temp location
    output_file = tmp_path / "stress_cases.jsonl"
    cases = build_stress_dataset()
    with output_file.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")

    # Confirm golden dirs unchanged
    for d, before in golden_snapshots.items():
        after = {f.name: f.stat().st_mtime for f in d.iterdir() if f.is_file()}
        assert before == after, f"Golden dir {d} was modified during stress build"


def test_stress_dataset_distribution():
    cases = build_stress_dataset()
    by_family: dict[str, int] = {}
    for case in cases:
        family = case["mismatch_family"]
        by_family[family] = by_family.get(family, 0) + 1

    assert len(by_family) == 7, f"Expected 7 families, got {len(by_family)}"
    assert by_family["event_stage_mismatch"] == 8
    assert by_family["causal_mechanism"] == 6
    assert by_family["metric_mismatch"] == 6

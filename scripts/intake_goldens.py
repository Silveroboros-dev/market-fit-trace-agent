from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ALLOWED_FIT_CLASSES = {"direct", "indirect", "weak_proxy", "no_clean_expression"}
DEFAULT_REPORT_PATH = Path("evals/golden_intake_report.md")


@dataclass(frozen=True)
class ExampleRecord:
    pack: str
    path: Path
    line_no: int
    example_id: str
    schema_version: str
    source_text: str
    source_url: str
    status_id: str | None
    content_hash: str
    fetch_status: str
    expected: dict[str, Any] | None
    market_ids: set[str]


@dataclass
class Finding:
    severity: str
    code: str
    example_id: str
    pack: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate golden/candidate eval intake for provenance, dedupe, market refs, "
            "and promotion risks."
        )
    )
    parser.add_argument(
        "--examples",
        action="append",
        type=Path,
        help=(
            "Path to an examples.jsonl file. May be passed multiple times. "
            "Defaults to every evals/market_fit_*/examples.jsonl file."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Markdown report path. Default: {DEFAULT_REPORT_PATH}",
    )
    parser.add_argument(
        "--near-duplicate-threshold",
        type=float,
        default=0.92,
        help="SequenceMatcher ratio for near-duplicate source text warnings.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings as well as errors.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    example_paths = args.examples or sorted(Path("evals").glob("market_fit_*/examples.jsonl"))
    records: list[ExampleRecord] = []
    findings: list[Finding] = []

    for path in example_paths:
        if not path.exists():
            findings.append(
                Finding("error", "missing_examples_file", "-", path.parent.name, str(path))
            )
            continue
        pack_records, pack_findings = load_pack(path)
        records.extend(pack_records)
        findings.extend(pack_findings)

    findings.extend(find_cross_pack_duplicates(records))
    findings.extend(find_near_duplicates(records, args.near_duplicate_threshold))

    report = render_report(records, findings)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)

    has_errors = any(finding.severity == "error" for finding in findings)
    has_warnings = any(finding.severity == "warning" for finding in findings)
    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


def load_pack(examples_path: Path) -> tuple[list[ExampleRecord], list[Finding]]:
    pack = examples_path.parent.name
    expected_by_id, expected_findings = load_expected(examples_path.parent)
    market_ids = load_market_ids(examples_path.parent)
    records: list[ExampleRecord] = []
    findings: list[Finding] = list(expected_findings)

    for line_no, row in iter_jsonl(examples_path):
        example_id = str(row.get("example_id") or "")
        source_text = str(row.get("source_text") or "")
        source_provenance = row.get("source_provenance") or {}
        source_url = str(source_provenance.get("source_url") or "")
        fetch_status = str(source_provenance.get("fetch_status") or "")
        expected = expected_by_id.get(example_id)
        record = ExampleRecord(
            pack=pack,
            path=examples_path,
            line_no=line_no,
            example_id=example_id,
            schema_version=str(row.get("schema_version") or ""),
            source_text=source_text,
            source_url=source_url,
            status_id=extract_status_id(source_url),
            content_hash=stable_text_hash(source_text),
            fetch_status=fetch_status,
            expected=expected,
            market_ids=market_ids,
        )
        records.append(record)
        findings.extend(validate_example(row, record))
        findings.extend(validate_expected(record))
        findings.extend(validate_market_references(record))

    return records, findings


def load_expected(pack_dir: Path) -> tuple[dict[str, dict[str, Any]], list[Finding]]:
    path = pack_dir / "expected_outputs.jsonl"
    findings: list[Finding] = []
    if not path.exists():
        return {}, [
            Finding(
                "error",
                "missing_expected_outputs",
                "-",
                pack_dir.name,
                f"{path} is required for promotion-ready intake.",
            )
        ]

    expected: dict[str, dict[str, Any]] = {}
    for line_no, row in iter_jsonl(path):
        example_id = str(row.get("example_id") or "")
        if not example_id:
            findings.append(
                Finding(
                    "error",
                    "missing_expected_example_id",
                    "-",
                    pack_dir.name,
                    f"{path}:{line_no}",
                )
            )
            continue
        expected[example_id] = row
    return expected, findings


def load_market_ids(pack_dir: Path) -> set[str]:
    path = pack_dir / "market_snapshots.jsonl"
    if not path.exists():
        return set()
    ids: set[str] = set()
    for _, row in iter_jsonl(path):
        market_id = row.get("market_id")
        if isinstance(market_id, str):
            ids.add(market_id)
    return ids


def validate_example(row: dict[str, Any], record: ExampleRecord) -> list[Finding]:
    findings: list[Finding] = []
    required = [
        ("example_id", row.get("example_id")),
        ("schema_version", row.get("schema_version")),
        ("as_of_ts", row.get("as_of_ts")),
        ("source_type", row.get("source_type")),
        ("source_text", row.get("source_text")),
    ]
    for field, value in required:
        if not value:
            findings.append(
                Finding("error", "missing_required_field", record.example_id, record.pack, field)
            )

    if len(record.source_text.strip()) < 20:
        findings.append(
            Finding(
                "error",
                "source_text_too_short",
                record.example_id,
                record.pack,
                "source_text must be long enough to adjudicate.",
            )
        )

    provenance = row.get("source_provenance") or {}
    for field in ("source_name", "source_url", "fetch_status"):
        if not provenance.get(field):
            findings.append(
                Finding(
                    "error",
                    "missing_source_provenance",
                    record.example_id,
                    record.pack,
                    field,
                )
            )

    labels = row.get("labels") or {}
    if not labels.get("topic"):
        findings.append(
            Finding("error", "missing_topic_label", record.example_id, record.pack, "labels.topic")
        )

    market_ref = row.get("market_snapshot_ref") or {}
    rules_ref = row.get("market_rules_snapshot_ref") or {}
    refs = (("market_snapshot_ref", market_ref), ("market_rules_snapshot_ref", rules_ref))
    for name, ref in refs:
        if not ref.get("build_id"):
            findings.append(
                Finding("error", "missing_snapshot_build_id", record.example_id, record.pack, name)
            )

    if "grok" in f"{record.fetch_status} {provenance.get('notes', '')}".lower():
        findings.append(
            Finding(
                "warning",
                "grok_candidate_requires_review",
                record.example_id,
                record.pack,
                (
                    "Treat as candidate-only until source text and market rules are "
                    "independently checked."
                ),
            )
        )

    if "candidate" in record.schema_version:
        findings.append(
            Finding(
                "warning",
                "candidate_pack_not_promoted",
                record.example_id,
                record.pack,
                (
                    "Candidate schema version must be explicitly promoted before becoming "
                    "strict goldens."
                ),
            )
        )

    return findings


def validate_expected(record: ExampleRecord) -> list[Finding]:
    expected = record.expected
    if expected is None:
        return [
            Finding(
                "error",
                "missing_expected_row",
                record.example_id,
                record.pack,
                "No matching expected_outputs.jsonl row.",
            )
        ]

    findings: list[Finding] = []
    fit = expected.get("expected_fit") or {}
    fit_class = fit.get("semantic_fit_class")
    if fit_class not in ALLOWED_FIT_CLASSES:
        findings.append(
            Finding(
                "error",
                "invalid_fit_class",
                record.example_id,
                record.pack,
                f"semantic_fit_class={fit_class!r}",
            )
        )

    thesis = expected.get("expected_thesis") or {}
    if not thesis.get("summary"):
        findings.append(
            Finding("error", "missing_expected_summary", record.example_id, record.pack, "")
        )

    explanation = expected.get("expected_explanation") or {}
    for field in ("must_mention", "must_not_claim"):
        if not isinstance(explanation.get(field), list) or not explanation.get(field):
            findings.append(
                Finding(
                    "warning",
                    "weak_explanation_constraints",
                    record.example_id,
                    record.pack,
                    f"expected_explanation.{field} should be a non-empty list.",
                )
            )

    safety = expected.get("safety_expectations") or {}
    if safety.get("contains_execution_recommendation") is not False:
        findings.append(
            Finding(
                "error",
                "unsafe_execution_expectation",
                record.example_id,
                record.pack,
                "Expected output must forbid execution recommendations.",
            )
        )
    if safety.get("contains_investment_advice_language") is not False:
        findings.append(
            Finding(
                "error",
                "unsafe_investment_expectation",
                record.example_id,
                record.pack,
                "Expected output must forbid investment-advice language.",
            )
        )

    return findings


def validate_market_references(record: ExampleRecord) -> list[Finding]:
    expected = record.expected or {}
    fit = expected.get("expected_fit") or {}
    refs: list[str] = []
    best = fit.get("best_market_id")
    if best:
        refs.append(str(best))
    for field in ("acceptable_market_ids", "adjacent_market_ids", "rejected_market_ids"):
        refs.extend(str(item) for item in fit.get(field) or [] if item)

    findings: list[Finding] = []
    for market_id in sorted(set(refs)):
        if market_id not in record.market_ids:
            findings.append(
                Finding(
                    "error",
                    "market_ref_missing_snapshot",
                    record.example_id,
                    record.pack,
                    (
                        f"{market_id} is referenced in expected output but absent from "
                        "market_snapshots.jsonl."
                    ),
                )
            )
    return findings


def find_cross_pack_duplicates(records: list[ExampleRecord]) -> list[Finding]:
    findings: list[Finding] = []
    groupings = {
        "duplicate_example_id": group_by(records, lambda record: record.example_id),
        "duplicate_source_url": group_by(records, lambda record: normalize_url(record.source_url)),
        "duplicate_x_status": group_by(records, lambda record: record.status_id or ""),
        "duplicate_source_text": group_by(records, lambda record: record.content_hash),
    }
    for code, groups in groupings.items():
        for key, items in groups.items():
            if not key or len(items) < 2:
                continue
            detail = ", ".join(f"{item.pack}/{item.example_id}" for item in items)
            for item in items:
                findings.append(
                    Finding(
                        "warning",
                        code,
                        item.example_id,
                        item.pack,
                        f"Duplicate key {key}: {detail}",
                    )
                )
    return findings


def find_near_duplicates(records: list[ExampleRecord], threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    normalized = [(record, normalize_text(record.source_text)) for record in records]
    for index, (left, left_text) in enumerate(normalized):
        for right, right_text in normalized[index + 1 :]:
            if left.content_hash == right.content_hash:
                continue
            if not left_text or not right_text:
                continue
            ratio = SequenceMatcher(None, left_text[:3000], right_text[:3000]).ratio()
            if ratio >= threshold:
                detail = (
                    f"{left.pack}/{left.example_id} ~= "
                    f"{right.pack}/{right.example_id}; ratio={ratio:.3f}"
                )
                findings.append(
                    Finding(
                        "warning",
                        "near_duplicate_source_text",
                        left.example_id,
                        left.pack,
                        detail,
                    )
                )
                findings.append(
                    Finding(
                        "warning",
                        "near_duplicate_source_text",
                        right.example_id,
                        right.pack,
                        detail,
                    )
                )
    return findings


def render_report(records: list[ExampleRecord], findings: list[Finding]) -> str:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    by_pack: dict[str, int] = defaultdict(int)
    for record in records:
        by_pack[record.pack] += 1

    lines = [
        "# Golden Intake Report",
        "",
        (
            "This report validates eval fixture intake before candidate rows are promoted "
            "to strict goldens."
        ),
        "",
        "## Summary",
        "",
        f"- examples scanned: {len(records)}",
        f"- packs scanned: {len(by_pack)}",
        f"- structural errors: {len(errors)}",
        f"- review warnings: {len(warnings)}",
        "",
        "| Pack | Examples |",
        "| --- | ---: |",
    ]
    for pack, count in sorted(by_pack.items()):
        lines.append(f"| `{pack}` | {count} |")

    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No findings.")
    else:
        lines.extend(
            [
                "| Severity | Code | Pack | Example | Detail |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for finding in sorted(
            findings,
            key=lambda item: (item.severity != "error", item.pack, item.example_id, item.code),
        ):
            lines.append(
                "| "
                + " | ".join(
                    [
                        finding.severity,
                        f"`{finding.code}`",
                        f"`{finding.pack}`",
                        f"`{finding.example_id}`",
                        escape_markdown_table(finding.detail),
                    ]
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Promotion Rule",
            "",
            "- Structural errors block promotion.",
            (
                "- Grok-sourced rows remain candidates until the source text and market "
                "rules are independently checked."
            ),
            (
                "- Duplicate or near-duplicate rows should be merged, dropped, or justified "
                "before promotion."
            ),
            (
                "- Strict goldens must pass their pack-specific eval command, such as "
                "`make evals`, `make evals-v2`, or `make evals-v4-live-promoted`, "
                "without `--allow-failures`."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def iter_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append((line_no, value))
    return rows


def group_by(records: list[ExampleRecord], key_fn: Any) -> dict[str, list[ExampleRecord]]:
    groups: dict[str, list[ExampleRecord]] = defaultdict(list)
    for record in records:
        groups[key_fn(record)].append(record)
    return groups


def extract_status_id(url: str) -> str | None:
    match = re.search(r"https?://(?:www\.)?(?:x|twitter)\.com/[^/]+/status/(\d+)", url)
    if not match:
        return None
    return f"x_status:{match.group(1)}"


def normalize_url(url: str) -> str:
    return url.strip().split("?")[0].rstrip("/")


def normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"https?://\S+", " ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def stable_text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def escape_markdown_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    sys.exit(main())

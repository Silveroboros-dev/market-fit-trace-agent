from __future__ import annotations

import asyncio
import json

from app.agent import MarketFitTraceAgent
from app.golden_replay import (
    STRICT_GOLDEN_PACKS,
    list_strict_golden_options,
    resolve_strict_golden_provider,
)
from app.ledger import LedgerStore


class OfflineADKRuntime:
    runtime_name = "offline-golden-ui-test"

    async def generate_json(self, **_kwargs):
        return None


def test_strict_golden_resolver_covers_all_canonical_goldens():
    cases = _strict_golden_cases()

    assert len(cases) == 19
    for case in cases:
        provider = resolve_strict_golden_provider(case["source_text"])
        assert provider is not None
        assert provider.case.pack == case["pack"]
        assert provider.case.example_id == case["example_id"]


def test_strict_golden_provider_returns_only_expected_market_context():
    for case in _representative_golden_cases():
        provider = resolve_strict_golden_provider(case["source_text"])
        assert provider is not None

        market_ids = {market.market_id for market in provider.get_markets()}
        expected_ids = set(provider.case.expected_market_ids)

        assert market_ids <= expected_ids


def test_strict_golden_options_are_ui_safe_and_complete():
    options = list_strict_golden_options()

    assert len(options) == 19
    assert options[0]["pack"] == "market_fit_v1"
    for option in options:
        assert option["label"]
        assert option["source_text"]
        assert option["expected_fit_class"] in {
            "direct",
            "indirect",
            "weak_proxy",
            "no_clean_expression",
        }
        assert option["fixture_market_count"] == len(option["fixture_market_ids"])
        assert resolve_strict_golden_provider(option["source_text"]) is not None


def test_strict_goldens_endpoint_payload():
    from app.main import strict_goldens

    payload = strict_goldens()

    assert payload["golden_count"] == 19
    assert len(payload["goldens"]) == 19
    assert payload["goldens"][0]["source_text"]


def test_agent_replays_strict_golden_market_context_before_and_after_trace(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.workflow.log_eval_annotations", _skip_annotations)
    monkeypatch.setattr("app.workflow.TraceContext", FakeTraceContext)
    asyncio.run(_agent_replays_strict_golden_market_context_before_and_after_trace(tmp_path))


async def _agent_replays_strict_golden_market_context_before_and_after_trace(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    agent = MarketFitTraceAgent(
        store=store,
        adk_runtime=OfflineADKRuntime(),
        market_provider_resolver=resolve_strict_golden_provider,
    )

    for case in _strict_golden_cases():
        provider = resolve_strict_golden_provider(case["source_text"])
        assert provider is not None
        expected_ids = {market.market_id for market in provider.get_markets()}

        first = await agent.run(thesis=case["source_text"], prompt_version="v1_lenient")
        first_ids = {market.market_id for market in first.market_context}
        assert first.market_retrieval is not None
        assert first.market_retrieval.mode == "golden_fixture"
        assert first.market_retrieval.query_summary["example_id"] == case["example_id"]
        assert first_ids == expected_ids

        improved = await agent.improve_from_trace(
            first.run_id, allow_local_fallback=True
        )
        second_ids = {market.market_id for market in improved.after.market_context}
        assert improved.after.market_retrieval is not None
        assert improved.after.market_retrieval.mode == "golden_fixture"
        assert second_ids == expected_ids


def _strict_golden_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for pack_dir in STRICT_GOLDEN_PACKS:
        examples_path = pack_dir / "examples.jsonl"
        for row in _read_jsonl(examples_path):
            cases.append(
                {
                    "pack": pack_dir.name,
                    "example_id": row["example_id"],
                    "source_text": row["source_text"],
                }
            )
    return cases


def _representative_golden_cases() -> list[dict[str, str]]:
    wanted = {"eval_001", "eval_007", "eval_v2_013", "demo-hormuz-candidate"}
    return [case for case in _strict_golden_cases() if case["example_id"] in wanted]


def _read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _skip_annotations(**_kwargs):
    return False


class FakeTraceContext:
    def span(self, *_args, **_kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def set_current_span_attributes(self, *_args, **_kwargs):
        return None

    def trace_id(self):
        return "local-test-trace"

    def span_id(self, *_args, **_kwargs):
        return None

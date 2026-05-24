from __future__ import annotations

from app.ledger import LedgerStore
from app.models import HumanVerdict


def test_ledger_records_human_verdict(tmp_path):
    store = LedgerStore(tmp_path / "ledger.json")
    source = store.create_source("The Fed will cut in July.")
    run = store.create_run("The Fed will cut in July.", "gemini-test", "v1")
    claim = store.propose_claim(
        run_id=run["id"],
        source_id=source["id"],
        claim_text="The Fed will cut in July.",
        entities=["Federal Reserve"],
        horizon="July",
        stance="expects cut",
        confidence=0.8,
        reasoning_summary="Direct policy event.",
    )
    verdict = store.record_human_verdict(
        claim_id=claim["claim_id"],
        verdict=HumanVerdict.VERIFY,
        corrected_claim_text=None,
        corrected_fit_class=None,
        reviewer_note="Looks correct.",
    )
    trace = store.query_claim_trace(claim["claim_id"])

    assert verdict["claim_status"] == "verified"
    assert trace.status == "verified"
    assert any(event.event_type == "human_verdict_recorded" for event in trace.events)


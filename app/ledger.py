from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from app.config import settings
from app.models import ClaimTrace, FitClass, HumanVerdict, LedgerEvent, utc_now


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _empty_store() -> dict[str, list[dict[str, Any]]]:
    return {
        "sources": [],
        "agent_runs": [],
        "claims": [],
        "market_fit_records": [],
        "human_verdicts": [],
        "eval_results": [],
        "ledger_events": [],
    }


class LedgerStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.ledger_store_path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(_empty_store())

    def create_source(self, raw_text: str, title: str | None = None) -> dict[str, Any]:
        source = {
            "id": _new_id("src"),
            "title": title or "Pasted thesis",
            "source_type": "pasted_text",
            "uri": None,
            "raw_text": raw_text,
            "content_hash": uuid.uuid5(uuid.NAMESPACE_URL, raw_text).hex,
            "created_at": utc_now(),
        }
        with self._locked_store() as data:
            data["sources"].append(source)
        return source

    def create_run(self, user_goal: str, model: str, prompt_version: str) -> dict[str, Any]:
        run = {
            "id": _new_id("run"),
            "user_goal": user_goal,
            "model": model,
            "prompt_version": prompt_version,
            "phoenix_trace_id": None,
            "status": "running",
            "eval_summary_json": None,
            "created_at": utc_now(),
        }
        with self._locked_store() as data:
            data["agent_runs"].append(run)
        return run

    def update_run(self, run_id: str, **updates: Any) -> dict[str, Any]:
        with self._locked_store() as data:
            run = self._find(data, "agent_runs", run_id)
            run.update(updates)
            return dict(run)

    def get_run(self, run_id: str) -> dict[str, Any]:
        data = self._read()
        return dict(self._find(data, "agent_runs", run_id))

    def get_source(self, source_id: str) -> dict[str, Any]:
        data = self._read()
        return dict(self._find(data, "sources", source_id))

    def get_latest_fit(self, claim_id: str) -> dict[str, Any] | None:
        data = self._read()
        fits = [fit for fit in data["market_fit_records"] if fit["claim_id"] == claim_id]
        return dict(fits[-1]) if fits else None

    def get_latest_eval_for_run(self, run_id: str) -> dict[str, Any] | None:
        data = self._read()
        evals = [item for item in data["eval_results"] if item["run_id"] == run_id]
        return dict(evals[-1]) if evals else None

    def propose_claim(
        self,
        *,
        run_id: str,
        source_id: str,
        claim_text: str,
        entities: list[str],
        horizon: str,
        stance: str,
        confidence: float,
        reasoning_summary: str,
    ) -> dict[str, str]:
        claim = {
            "id": _new_id("claim"),
            "run_id": run_id,
            "source_id": source_id,
            "claim_text": claim_text,
            "entities_json": json.dumps(entities),
            "horizon": horizon,
            "stance": stance,
            "status": "proposed",
            "confidence": confidence,
            "reasoning_summary": reasoning_summary,
            "created_at": utc_now(),
        }
        with self._locked_store() as data:
            data["claims"].append(claim)
            self._append_event(
                data,
                run_id=run_id,
                claim_id=claim["id"],
                event_type="ledger_claim_proposed",
                summary=f"Claim proposed: {claim_text}",
                payload=claim,
            )
        return {"claim_id": claim["id"], "status": "proposed"}

    def attach_market_fit(
        self,
        *,
        claim_id: str,
        recommended_market_id: str | None,
        semantic_fit_class: FitClass | str,
        fit_reason: str,
        captures: list[str],
        misses: list[str],
        rejected_markets: list[dict[str, Any]],
    ) -> dict[str, str]:
        with self._locked_store() as data:
            claim = self._find(data, "claims", claim_id)
            record = {
                "id": _new_id("fit"),
                "claim_id": claim_id,
                "recommended_market_id": recommended_market_id,
                "semantic_fit_class": str(semantic_fit_class),
                "fit_reason": fit_reason,
                "captures_json": json.dumps(captures),
                "misses_json": json.dumps(misses),
                "rejected_markets_json": json.dumps(rejected_markets),
                "created_at": utc_now(),
            }
            data["market_fit_records"].append(record)
            self._append_event(
                data,
                run_id=claim["run_id"],
                claim_id=claim_id,
                event_type="market_fit_classified",
                summary=f"Fit classified as {record['semantic_fit_class']}",
                payload=record,
            )
        return {"fit_record_id": record["id"], "status": "recorded"}

    def record_eval_result(
        self,
        *,
        run_id: str,
        claim_id: str | None,
        phoenix_trace_id: str,
        metrics: dict[str, Any],
        failure_summary: str | None,
    ) -> dict[str, str]:
        record = {
            "id": _new_id("eval"),
            "run_id": run_id,
            "claim_id": claim_id,
            "phoenix_trace_id": phoenix_trace_id,
            "metrics_json": json.dumps(metrics),
            "failure_summary": failure_summary,
            "created_at": utc_now(),
        }
        with self._locked_store() as data:
            data["eval_results"].append(record)
            self._append_event(
                data,
                run_id=run_id,
                claim_id=claim_id,
                event_type="fit_eval_run",
                summary=failure_summary or "Fit eval passed",
                payload=record,
            )
        return {"eval_record_id": record["id"], "status": "recorded"}

    def record_market_retrieval(
        self,
        *,
        run_id: str,
        claim_id: str | None,
        retrieval: dict[str, Any],
    ) -> None:
        with self._locked_store() as data:
            self._append_event(
                data,
                run_id=run_id,
                claim_id=claim_id,
                event_type="market_retrieval_run",
                summary=(
                    f"Retrieved {len(retrieval.get('market_ids_considered', []))} "
                    f"markets via {retrieval.get('mode', 'unknown')}"
                ),
                payload=retrieval,
            )

    def record_human_verdict(
        self,
        *,
        claim_id: str,
        verdict: HumanVerdict | str,
        corrected_claim_text: str | None,
        corrected_fit_class: FitClass | str | None,
        reviewer_note: str,
    ) -> dict[str, str]:
        status_map = {
            HumanVerdict.VERIFY.value: "verified",
            HumanVerdict.REJECT.value: "rejected",
            HumanVerdict.NEEDS_REVIEW.value: "needs_review",
            HumanVerdict.CORRECTED.value: "revised",
        }
        verdict_value = str(verdict)
        claim_status = status_map[verdict_value]
        with self._locked_store() as data:
            claim = self._find(data, "claims", claim_id)
            record = {
                "id": _new_id("verdict"),
                "claim_id": claim_id,
                "verdict": verdict_value,
                "corrected_claim_text": corrected_claim_text,
                "corrected_fit_class": str(corrected_fit_class) if corrected_fit_class else None,
                "reviewer_note": reviewer_note,
                "created_at": utc_now(),
            }
            claim["status"] = claim_status
            if corrected_claim_text:
                claim["claim_text"] = corrected_claim_text
            data["human_verdicts"].append(record)
            self._append_event(
                data,
                run_id=claim["run_id"],
                claim_id=claim_id,
                event_type="human_verdict_recorded",
                summary=f"Human verdict recorded: {verdict_value}",
                payload=record,
            )
        return {"verdict_id": record["id"], "claim_status": claim_status}

    def query_claim_trace(self, claim_id: str) -> ClaimTrace:
        data = self._read()
        claim = self._find(data, "claims", claim_id)
        events = [
            LedgerEvent(
                event_type=event["event_type"],
                created_at=event["created_at"],
                summary=event["summary"],
                payload=event.get("event_payload_json", {}),
            )
            for event in data["ledger_events"]
            if event.get("claim_id") == claim_id
        ]
        return ClaimTrace(claim_id=claim_id, status=claim["status"], events=events)

    def record_trace_inspection(
        self,
        *,
        run_id: str,
        claim_id: str | None,
        phoenix_trace_id: str,
        summary: str,
        source: str,
    ) -> None:
        with self._locked_store() as data:
            self._append_event(
                data,
                run_id=run_id,
                claim_id=claim_id,
                event_type="phoenix_trace_inspected",
                summary=summary,
                payload={
                    "phoenix_trace_id": phoenix_trace_id,
                    "source": source,
                },
            )

    def reset(self) -> None:
        with self._lock:
            self._write(_empty_store())

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return _empty_store()
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, sort_keys=True)

    def _locked_store(self) -> LockedStore:
        return LockedStore(self)

    @staticmethod
    def _find(
        data: dict[str, list[dict[str, Any]]],
        collection: str,
        item_id: str,
    ) -> dict[str, Any]:
        for item in data[collection]:
            if item["id"] == item_id:
                return item
        raise KeyError(f"{collection} item not found: {item_id}")

    @staticmethod
    def _append_event(
        data: dict[str, list[dict[str, Any]]],
        *,
        run_id: str,
        claim_id: str | None,
        event_type: str,
        summary: str,
        payload: dict[str, Any],
    ) -> None:
        data["ledger_events"].append(
            {
                "id": _new_id("evt"),
                "run_id": run_id,
                "claim_id": claim_id,
                "event_type": event_type,
                "event_payload_json": payload,
                "summary": summary,
                "created_at": utc_now(),
            }
        )


class LockedStore:
    def __init__(self, store: LedgerStore) -> None:
        self.store = store
        self.data: dict[str, list[dict[str, Any]]] | None = None

    def __enter__(self) -> dict[str, list[dict[str, Any]]]:
        self.store._lock.acquire()
        self.data = self.store._read()
        return self.data

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is None and self.data is not None:
            self.store._write(self.data)
        self.store._lock.release()

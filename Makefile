.PHONY: dev test lint format evals evals-v2 evals-v4-live-promoted evals-live evals-candidates evals-candidates-v3 intake-goldens export-retrieval-candidate backfill-candidate-rules triage-candidates export-candidate-dataset review-candidate phoenix-export-candidates phoenix-sync-goldens phoenix-experiment-goldens api ui adk-run adk-web smoke-adk smoke-adk-live smoke-polydata phoenix-ensure phoenix-check phoenix-experiment deploy-adk

api:
	uv run --python 3.11 uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

ui:
	uv run --python 3.11 streamlit run app/ui.py

dev: api

test:
	uv run --python 3.11 --extra dev pytest

lint:
	uv run --python 3.11 --extra dev ruff check .

format:
	uv run --python 3.11 --extra dev ruff format .

evals:
	uv run --python 3.11 python scripts/run_evals.py

evals-v2:
	uv run --python 3.11 python scripts/run_evals.py \
		--cases evals/market_fit_v2/examples.jsonl \
		--expected evals/market_fit_v2/expected_outputs.jsonl \
		--markets evals/market_fit_v2/market_snapshots.jsonl

evals-v4-live-promoted:
	uv run --python 3.11 python scripts/run_evals.py \
		--cases evals/market_fit_v4_live_promoted/examples.jsonl \
		--expected evals/market_fit_v4_live_promoted/expected_outputs.jsonl \
		--markets evals/market_fit_v4_live_promoted/market_snapshots.jsonl

evals-live:
	uv run --python 3.11 python scripts/run_evals.py --live

evals-candidates:
	uv run --python 3.11 python scripts/run_evals.py --allow-failures \
		--cases evals/market_fit_v2_candidates/examples.jsonl \
		--expected evals/market_fit_v2_candidates/expected_outputs.jsonl \
		--markets evals/market_fit_v2_candidates/market_snapshots.jsonl

evals-candidates-v3:
	uv run --python 3.11 python scripts/run_evals.py --allow-failures \
		--cases evals/market_fit_v3_candidates/examples.jsonl \
		--expected evals/market_fit_v3_candidates/expected_outputs.jsonl \
		--markets evals/market_fit_v3_candidates/market_snapshots.jsonl

intake-goldens:
	uv run --python 3.11 python scripts/intake_goldens.py

export-retrieval-candidate:
	uv run --python 3.11 python scripts/export_retrieval_candidate.py

backfill-candidate-rules:
	uv run --python 3.11 python scripts/backfill_candidate_rules.py

triage-candidates:
	uv run --python 3.11 python scripts/triage_candidates.py
	uv run --python 3.11 python scripts/export_candidate_review_dataset.py

export-candidate-dataset:
	uv run --python 3.11 python scripts/export_candidate_review_dataset.py

review-candidate:
	uv run --python 3.11 python scripts/review_candidate.py --case-id "$(CASE)" --status "$(STATUS)" --note "$(NOTE)" --reviewer "$(or $(REVIEWER),local_reviewer)"

phoenix-export-candidates:
	uv run --python 3.11 python scripts/export_candidate_review_dataset.py

adk-run:
	uv run --python 3.11 adk run market_fit_adk

adk-web:
	uv run --python 3.11 adk web --port 8001 .

smoke-adk:
	uv run --python 3.11 python scripts/smoke_arize_adk.py --offline

smoke-adk-live:
	uv run --python 3.11 python scripts/smoke_arize_adk.py

smoke-polydata:
	uv run --python 3.11 python scripts/smoke_polydata.py

phoenix-ensure:
	uv run --python 3.11 python scripts/ensure_phoenix_annotation_configs.py

phoenix-check:
	uv run --python 3.11 python scripts/check_phoenix_trace.py

phoenix-sync-goldens:
	uv run --python 3.11 python scripts/run_phoenix_dataset_experiment.py --sync-only

phoenix-experiment-goldens:
	uv run --python 3.11 python scripts/run_phoenix_dataset_experiment.py

phoenix-experiment:
	uv run --python 3.11 python scripts/run_phoenix_dataset_experiment.py

deploy-adk:
	bash scripts/deploy_adk_cloud_run.sh

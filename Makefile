.PHONY: dev test lint format evals evals-v2 evals-v4-live-promoted evals-live trace-repair evals-candidates evals-candidates-v3 intake-goldens governance-50 export-retrieval-candidate export-failure-eval-candidate policy-review-batch policy-change-proposal repair-loop backfill-candidate-rules triage-candidates export-candidate-dataset review-candidate phoenix-export-candidates phoenix-export-governance phoenix-experiment-governance phoenix-sync-goldens phoenix-experiment-goldens build-stress-40 run-stress-40 stress-appendix api api-live ui adk-run adk-web smoke-adk smoke-adk-live smoke-polydata phoenix-ensure phoenix-check phoenix-experiment deploy-adk

api:
	PHOENIX_MCP_ENABLED=true uv run --python 3.11 uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

api-live:
	PHOENIX_MCP_ENABLED=true MARKET_PROVIDER=polydata uv run --python 3.11 uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

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

trace-repair:
	PHOENIX_MCP_ENABLED=true uv run --python 3.11 python scripts/run_trace_repair_eval.py

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

governance-50:
	uv run --python 3.11 python scripts/build_governance_50_manifest.py

export-retrieval-candidate:
	uv run --python 3.11 python scripts/export_retrieval_candidate.py

export-failure-eval-candidate:
	uv run --python 3.11 python scripts/export_failure_eval_candidate.py --run-id "$(RUN_ID)"

policy-review-batch:
	uv run --python 3.11 python scripts/build_policy_review_batch.py

policy-change-proposal:
	uv run --python 3.11 python scripts/build_policy_change_proposal.py

repair-loop:
	uv run --python 3.11 python scripts/run_repair_loop.py

build-stress-40:
	uv run --python 3.11 python scripts/build_stress_dataset.py

run-stress-40:
	uv run --python 3.11 python scripts/run_stress_gemini_eval.py

stress-appendix:
	uv run --python 3.11 python scripts/build_stress_appendix.py

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

phoenix-export-governance:
	uv run --python 3.11 python scripts/export_governance_dataset.py

phoenix-experiment-governance:
	uv run --python 3.11 python scripts/run_governance_experiment.py

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

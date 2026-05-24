#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before deploying.}"
: "${GOOGLE_CLOUD_LOCATION:=global}"
: "${CLOUD_RUN_REGION:=us-central1}"
: "${SERVICE_NAME:=market-fit-trace-agent-adk}"
: "${PHOENIX_PROJECT_NAME:=market_fit_trace_agent}"
: "${GEMINI_MODEL:=gemini-3.5-flash}"

ADK_AGENT_PATH="${ADK_AGENT_PATH:-market_fit_adk}"
ENV_VARS="GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_GENAI_USE_VERTEXAI=true,GEMINI_MODEL=${GEMINI_MODEL},PHOENIX_PROJECT_NAME=${PHOENIX_PROJECT_NAME},PHOENIX_COLLECTOR_ENDPOINT=${PHOENIX_COLLECTOR_ENDPOINT:-},PHOENIX_BASE_URL=${PHOENIX_BASE_URL:-}"

GCLOUD_ARGS=(
  "--allow-unauthenticated"
)

if [[ -n "${PHOENIX_API_KEY_SECRET:-}" ]]; then
  GCLOUD_ARGS+=("--set-env-vars=${ENV_VARS}")
  GCLOUD_ARGS+=("--set-secrets=PHOENIX_API_KEY=${PHOENIX_API_KEY_SECRET}:latest")
elif [[ -n "${PHOENIX_API_KEY:-}" ]]; then
  GCLOUD_ARGS+=("--set-env-vars=${ENV_VARS},PHOENIX_API_KEY=${PHOENIX_API_KEY}")
else
  GCLOUD_ARGS+=("--set-env-vars=${ENV_VARS}")
  echo "Warning: PHOENIX_API_KEY or PHOENIX_API_KEY_SECRET is not set; Phoenix export will not authenticate." >&2
fi

adk deploy cloud_run \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --region="${CLOUD_RUN_REGION}" \
  --service_name="${SERVICE_NAME}" \
  --app_name="market_fit_trace_agent" \
  --port=8080 \
  "${ADK_AGENT_PATH}" \
  -- \
  "${GCLOUD_ARGS[@]}"

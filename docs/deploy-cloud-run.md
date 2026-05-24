# Cloud Run Deployment

This repo includes two deployment paths:

- ADK agent API server on Cloud Run.
- FastAPI demo UI/API on Cloud Run.

## ADK Agent API Server

The deployable ADK agent follows the Google ADK Cloud Run convention:

- agent code is in `market_fit_adk/agent.py`;
- the module exports `root_agent`;
- `market_fit_adk/__init__.py` imports the agent module;
- `market_fit_adk/requirements.txt` declares ADK and Phoenix instrumentation
  dependencies.

Configure environment variables:

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export GOOGLE_CLOUD_LOCATION=global
export CLOUD_RUN_REGION=us-central1
export GEMINI_MODEL=gemini-3.5-flash
export PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-space-name/v1/traces
export PHOENIX_BASE_URL=https://app.phoenix.arize.com/s/your-space-name
export PHOENIX_API_KEY_SECRET=phoenix-api-key
```

Use Secret Manager for `PHOENIX_API_KEY` before deployment:

```bash
printf '%s' "$PHOENIX_API_KEY" | gcloud secrets create phoenix-api-key --data-file=-
```

If the secret already exists, add a new version instead:

```bash
printf '%s' "$PHOENIX_API_KEY" | gcloud secrets versions add phoenix-api-key --data-file=-
```

Deploy:

```bash
make deploy-adk
```

## FastAPI Demo UI/API

Build and deploy the FastAPI demo UI/API:

```bash
gcloud run deploy market-fit-trace-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3.5-flash,PHOENIX_PROJECT_NAME=market_fit_trace_agent
```

Add secrets for `GOOGLE_CLOUD_PROJECT`, `PHOENIX_API_KEY`, and Phoenix URLs
through your normal Google Cloud secret workflow.

## Notes

- Use AI Studio API-key auth for local live runs when fastest.
- Use Vertex AI / Cloud Run auth for hosted deployment.
- Confirm Phoenix export after deployment with `make phoenix-check` against the
  configured Phoenix project.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY market_fit_adk ./market_fit_adk
COPY mcp ./mcp
COPY evals ./evals
COPY scripts ./scripts

RUN pip install --no-cache-dir .

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

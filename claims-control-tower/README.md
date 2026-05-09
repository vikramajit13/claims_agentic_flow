# Claims Control Tower

FastAPI backend for a phase-1 claims workflow covering submission, adjudication, human review, payment guardrails, payment instruction creation, and audit events.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run with Docker

```bash
docker compose up --build
```

## Test

```bash
pytest
```

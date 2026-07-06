# Claims Control Tower Monorepo

Fresh monorepo starter for rebuilding the project with:

- `apps/api`: FastAPI backend
- `apps/web`: React dashboard starter
- root workspace scripts for the frontend app

## Current Backend Scope

The API currently keeps the surface intentionally small:

Claims APIs:

- `POST /v1/claims`
- `GET /v1/claims`
- `GET /v1/claims/{claim_id}`
- `POST /v1/claims/{claim_id}/documents/presign`
- `POST /v1/claims/{claim_id}/documents/{document_id}/complete-upload`

Workflow API:

- `POST /v1/workflows/claims/{claim_id}/start`

## What Is Included

- PostgreSQL + pgvector support for persistent storage
- pre-signed S3 upload starter
- explicit upload confirmation before OCR
- mock OCR over S3-backed documents
- OCR queue handoff starter for a future worker service
- Lambda-ready S3 event -> SQS -> OCR processing flow
- mock vector embedding persistence for OCR text
- LangSmith observability wiring
- React/Vite dashboard placeholder

## S3 And OCR Flow

Current local fallback flow:

1. `POST /v1/claims/{claim_id}/documents/presign`
2. client uploads the file
3. `POST /v1/claims/{claim_id}/documents/{document_id}/complete-upload`
4. mock OCR runs immediately or mock queue state is created

Target AWS flow now scaffolded in code:

1. client uploads the file to S3
2. S3 object-created event triggers a Lambda
3. that Lambda reads S3 object metadata, updates the API through an internal callback, and pushes an OCR job to SQS
4. a second Lambda consumes SQS
5. the second Lambda calls the API OCR pipeline
6. OCR is executed and the document record is updated with extracted text and embeddings

The presign response now includes `upload_headers`. Your uploader must send those headers with the S3 PUT so the event Lambda can recover the `document_id`, `claim_id`, and `run_ocr` flags from S3 object metadata.

## Monorepo Layout

- [apps/api](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/apps/api)
- [apps/web](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/apps/web)
- [infra](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/infra)

## Docker

```bash
docker compose up --build
```

This starts:

- `postgres` with pgvector
- `api` on port `8000`

## API Tests

```bash
docker compose run --rm api pytest -q tests
```

## Frontend Starter

```bash
cd apps/web
npm install
npm run dev
```

Or from the repo root:

```bash
npm run web:dev
```

## Next Suggested Steps

1. Add the first graph module under `apps/api/app/graph`
2. Add HITL screens in `apps/web`
3. Add LangSmith eval datasets and runners
4. Add GitHub Actions for Fargate, Lambda, and static frontend deploys
5. Add SQS or Step Functions for deeper multi-agent orchestration

## GitHub Actions

Starter GitHub Actions are included for:

- CI: `.github/workflows/ci.yml`
- AWS deploy: `.github/workflows/deploy-aws.yml`

Setup notes are in:

- [docs/github-actions-aws.md](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/docs/github-actions-aws.md)

Terraform infrastructure notes are in:

- [infra/README.md](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/infra/README.md)

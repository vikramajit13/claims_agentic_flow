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

Workflow API:

- `POST /v1/workflows/claims/{claim_id}/start`

## What Is Included

- PostgreSQL + pgvector support for persistent storage
- pre-signed S3 upload starter
- mock OCR over S3-backed documents
- mock vector embedding persistence for OCR text
- LangSmith observability wiring
- React/Vite dashboard placeholder

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

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
- dedicated prompt package for LLM system and user prompts

## Prompt Structure

Prompt files now live under [apps/api/app/prompts](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/apps/api/app/prompts).

Recommended enterprise-ready prompt pattern:

1. Keep system prompts stable, policy-heavy, and low-churn.
2. Keep user prompts dynamic, data-heavy, and task-specific.
3. Keep output contracts in code with schema validation, not only in prompt text.
4. Version prompts by task domain, not by model provider.
5. Separate prompt text from orchestration logic and fallback logic.

For this repo, a good scaling structure is:

- `prompts/document_intelligence/system/v1.md`
- `prompts/document_intelligence/user/v1.md`
- `prompts/claim_routing/system/v1.md`
- `prompts/claim_routing/user/v1.md`
- `prompts/adjuster_briefing/system/v1.md`
- `prompts/adjuster_briefing/user/v1.md`

What to use for enterprise-ready prompts:

- System prompt:
  - role
  - scope boundaries
  - risk/compliance rules
  - allowed labels and enums
  - non-hallucination rules
  - output format constraints

- User prompt:
  - task request
  - input facts
  - extracted context
  - decision criteria
  - explicit schema example

- Code-level guardrails:
  - Pydantic schema validation
  - fallback path
  - confidence thresholds
  - audit logging
  - prompt version tagging later

Each prompt file should include metadata in YAML front matter, for example:

- `prompt_name`
- `prompt_version`
- `prompt_role`
- `domain`
- `task`
- `owner`
- `status`
- `output_contract`
- `change_reason`

## LangSmith Prompt Registry

LangSmith is a good fit here, but I would use it as the remote registry and collaboration layer, not as the only source of truth.

Recommended pattern:

1. Keep source prompts in versioned `.md` files in the repo.
2. Load them locally at runtime with metadata.
3. Optionally push approved prompt versions to LangSmith using the prompt registry client.
4. Trace prompt name and version in runtime outputs and evaluations.

The helper for this is in [prompt_registry.py](/Users/vikramsingh/claims_agentic_flow/claims-control-tower/apps/api/app/prompt_registry.py:1). It uses the existing `langsmith` client APIs like `push_prompt` so you can publish the exact versioned prompt artifact to LangSmith when you want governed sharing, review, and rollback.

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

## Local Ollama Option

You can test the LLM-first document-intelligence flow locally with Ollama running on your Mac.

1. Start Ollama on your host machine.
2. Pull a model, for example:

```bash
ollama pull llama3.1:8b
```

3. Start the API with Ollama enabled:

```bash
ENABLE_LLM_DOCUMENT_INTELLIGENCE=true \
OPENAI_BASE_URL=http://host.docker.internal:11434/v1 \
DOCUMENT_INTELLIGENCE_MODEL=llama3.1:8b \
docker compose up --build
```

Notes:

- `host.docker.internal` is already wired into `docker-compose.yml` so the container can reach Ollama running on your host.
- `OPENAI_API_KEY` is optional for local Ollama.
- `USE_MOCK_OCR=true` can stay enabled locally. That still exercises the full LLM document-intelligence step using mock Textract-style text.

## Local LLM Test Flow

1. Create a claim:

```bash
curl -s http://localhost:8000/v1/claims \
  -H 'Content-Type: application/json' \
  -d '{"claim_number":"OLLAMA-001","customer_id":1,"claim_type":"motor"}'
```

2. Presign a document:

```bash
curl -s http://localhost:8000/v1/claims/1/documents/presign \
  -H 'Content-Type: application/json' \
  -d '{"file_name":"repair-invoice.pdf","content_type":"application/pdf","run_ocr":true}'
```

3. Complete the upload using the returned `document_id`:

```bash
curl -s http://localhost:8000/v1/claims/1/documents/1/complete-upload \
  -H 'Content-Type: application/json' \
  -d '{}'
```

4. Fetch the claim and inspect the LLM-enriched document fields:

```bash
curl -s http://localhost:8000/v1/claims/1
```

When Ollama is being used successfully, the document response should show:

- `quality_assessment.processing_mode = "llm"`
- `quality_assessment.fallback_used = false`

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

from fastapi.testclient import TestClient


def test_create_and_list_claims(client: TestClient):
    create_response = client.post(
        "/v1/claims",
        json={
            "claim_number": "MONO-001",
            "customer_id": 1,
            "claim_type": "motor",
            "description": "Starter monorepo claim",
            "claim_amount": 900,
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["status"] == "draft"

    list_response = client.get("/v1/claims")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_presign_document_with_mock_s3_and_ocr(client: TestClient):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "MONO-002",
            "customer_id": 2,
            "claim_type": "travel",
        },
    ).json()

    presign_response = client.post(
        f"/v1/claims/{claim['id']}/documents/presign",
        json={
            "file_name": "invoice.pdf",
            "content_type": "application/pdf",
            "run_ocr": True,
        },
    )
    assert presign_response.status_code == 200
    payload = presign_response.json()
    assert payload["upload_method"] == "PUT"
    assert payload["upload_url"].startswith("https://mock-s3.local/")
    assert payload["upload_headers"]["x-amz-meta-document-id"]
    assert payload["upload_headers"]["x-amz-meta-claim-id"] == str(claim["id"])
    assert payload["upload_headers"]["x-amz-meta-run-ocr"] == "true"

    document_response = client.post(
        f"/v1/claims/{claim['id']}/documents/{payload['document_id']}/complete-upload",
        json={},
    )
    assert document_response.status_code == 200
    assert document_response.json()["upload_status"] == "ocr_completed"

    get_response = client.get(f"/v1/claims/{claim['id']}")
    claim_payload = get_response.json()
    assert claim_payload["documents"][0]["ocr_requested"] is True
    assert claim_payload["documents"][0]["ocr_status"] == "completed"
    assert "Mock OCR extracted text" in claim_payload["documents"][0]["ocr_text"]


def test_start_workflow_from_submitted_claim(client: TestClient):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "MONO-003",
            "customer_id": 3,
            "claim_type": "motor",
        },
    ).json()
    client.post(
        f"/v1/claims/{claim['id']}/documents/presign",
        json={"file_name": "photo.jpg", "run_ocr": False},
    )
    workflow_waiting_response = client.post(
        f"/v1/workflows/claims/{claim['id']}/start",
        json={"hitl_required": False},
    )
    assert workflow_waiting_response.status_code == 200
    assert workflow_waiting_response.json()["status"] == "waiting_for_documents"

    claim_state = client.get(f"/v1/claims/{claim['id']}").json()
    document_id = claim_state["documents"][0]["id"]
    complete_response = client.post(
        f"/v1/claims/{claim['id']}/documents/{document_id}/complete-upload",
        json={},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["upload_status"] == "uploaded"
    assert complete_response.json()["ocr_status"] == "not_requested"

    workflow_response = client.post(
        f"/v1/workflows/claims/{claim['id']}/start",
        json={"hitl_required": False, "notes": ["Ready for graph starter"]},
    )
    assert workflow_response.status_code == 200
    payload = workflow_response.json()
    assert payload["status"] == "waiting_for_human"
    assert payload["current_step"] == "human_review"


def test_internal_document_callbacks(client: TestClient):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "MONO-004",
            "customer_id": 4,
            "claim_type": "property",
        },
    ).json()

    presign = client.post(
        f"/v1/claims/{claim['id']}/documents/presign",
        json={"file_name": "damage-invoice.pdf", "run_ocr": True},
    ).json()

    mark_uploaded = client.post(
        "/internal/documents/s3-object-created",
        headers={"X-Internal-Token": "test-internal-token"},
        json={
            "document_id": presign["document_id"],
            "claim_id": claim["id"],
            "s3_bucket": presign["s3_bucket"],
            "s3_key": presign["s3_key"],
            "queued_for_ocr": True,
            "ocr_job_id": "msg-123",
        },
    )
    assert mark_uploaded.status_code == 200
    assert mark_uploaded.json()["upload_status"] == "ocr_queued"

    process_ocr = client.post(
        "/internal/documents/process-ocr",
        headers={"X-Internal-Token": "test-internal-token"},
        json={"document_id": presign["document_id"]},
    )
    assert process_ocr.status_code == 200
    assert process_ocr.json()["ocr_status"] == "completed"

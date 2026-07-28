from fastapi.testclient import TestClient

from app.document_pipeline_service import DocumentPipelineService


async def _process_document(document_id: int) -> dict:
    service = DocumentPipelineService()
    return await service.process_ocr_job(document_id=document_id)


def test_ocr_pipeline_generates_structured_document_intelligence(client: TestClient):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "DOC-INT-001",
            "customer_id": 50,
            "claim_type": "motor",
        },
    ).json()

    presign = client.post(
        f"/v1/claims/{claim['id']}/documents/presign",
        json={"file_name": "repair-invoice.pdf", "run_ocr": True},
    ).json()

    client.post(
        "/internal/documents/s3-object-created",
        headers={"X-Internal-Token": "test-internal-token"},
        json={
            "document_id": presign["document_id"],
            "claim_id": claim["id"],
            "s3_bucket": presign["s3_bucket"],
            "s3_key": presign["s3_key"],
            "queued_for_ocr": True,
            "ocr_job_id": "sqs-msg-001",
        },
    )

    process_response = client.post(
        "/internal/documents/process-ocr",
        headers={"X-Internal-Token": "test-internal-token"},
        json={"document_id": presign["document_id"]},
    )
    assert process_response.status_code == 200
    assert process_response.json()["document_classification"]["document_type"] == "invoice"
    assert process_response.json()["quality_assessment"]["quality_level"] == "high"

    claim_response = client.get(f"/v1/claims/{claim['id']}")
    document = claim_response.json()["documents"][0]

    assert document["ocr_status"] == "completed"
    assert document["normalized_text"]
    assert document["document_classification"]["document_type"] == "invoice"
    assert document["extracted_fields"]["fields"]["invoice_number"] == "INV-1001"
    assert document["extracted_fields"]["fields"]["invoice_amount"] == 4200.0
    assert document["quality_assessment"]["review_recommended"] is False
    assert document["validation_results"]["has_text"] is True

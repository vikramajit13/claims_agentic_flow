import json

from fastapi.testclient import TestClient

from app.lambda_handlers.ocr_queue_consumer_handler import handler as ocr_queue_handler
from app.lambda_handlers.s3_upload_event_handler import handler as s3_upload_handler


def test_s3_event_enqueues_ocr_job(client: TestClient):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "MONO-PIPE-001",
            "customer_id": 10,
            "claim_type": "property",
        },
    ).json()

    presign = client.post(
        f"/v1/claims/{claim['id']}/documents/presign",
        json={"file_name": "damage-photo.png", "run_ocr": True},
    ).json()

    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": presign["s3_bucket"]},
                    "object": {"key": presign["s3_key"]},
                },
            }
        ]
    }

    result = s3_upload_handler(event, None)
    assert result["processed_records"] == 1
    assert result["results"][0]["upload_status"] == "ocr_queued"
    assert result["results"][0]["ocr_status"] == "pending"
    assert result["results"][0]["ocr_job_id"].startswith("mock-ocr-job-")


def test_sqs_event_processes_ocr_job(client: TestClient):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "MONO-PIPE-002",
            "customer_id": 11,
            "claim_type": "travel",
        },
    ).json()

    presign = client.post(
        f"/v1/claims/{claim['id']}/documents/presign",
        json={"file_name": "invoice.pdf", "run_ocr": True},
    ).json()

    s3_upload_handler(
        {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {
                        "bucket": {"name": presign["s3_bucket"]},
                        "object": {"key": presign["s3_key"]},
                    },
                }
            ]
        },
        None,
    )

    sqs_event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "event_type": "document_ready_for_ocr",
                        "document_id": presign["document_id"],
                        "claim_id": claim["id"],
                        "s3_bucket": presign["s3_bucket"],
                        "s3_key": presign["s3_key"],
                        "s3_uri": presign["s3_uri"],
                    }
                )
            }
        ]
    }

    result = ocr_queue_handler(sqs_event, None)
    assert result["processed_records"] == 1
    assert result["results"][0]["upload_status"] == "ocr_completed"
    assert result["results"][0]["ocr_status"] == "completed"

    claim_state = client.get(f"/v1/claims/{claim['id']}").json()
    assert claim_state["documents"][0]["ocr_status"] == "completed"
    assert claim_state["documents"][0]["upload_status"] == "ocr_completed"
    assert "Mock OCR extracted text" in claim_state["documents"][0]["ocr_text"]

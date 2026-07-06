from __future__ import annotations

import json
import uuid

import boto3

from app.config import settings
from app.observability import traceable


class OcrQueueService:
    def __init__(self) -> None:
        self.client = None if settings.use_mock_sqs else boto3.client("sqs", region_name=settings.aws_region)

    @traceable(name="enqueue_ocr_job", run_type="tool")
    def enqueue_document(self, *, document_id: int, claim_id: int, s3_bucket: str, s3_key: str, s3_uri: str) -> str:
        if settings.use_mock_sqs or not settings.ocr_queue_url:
            return f"mock-ocr-job-{document_id}-{uuid.uuid4()}"

        if self.client is None:
            raise RuntimeError("SQS client is not configured for non-mock usage.")

        response = self.client.send_message(
            QueueUrl=settings.ocr_queue_url,
            MessageBody=json.dumps(
                {
                    "document_id": document_id,
                    "claim_id": claim_id,
                    "s3_bucket": s3_bucket,
                    "s3_key": s3_key,
                    "s3_uri": s3_uri,
                }
            ),
        )
        return response["MessageId"]

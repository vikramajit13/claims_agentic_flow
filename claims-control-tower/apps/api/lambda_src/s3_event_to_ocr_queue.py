from __future__ import annotations

import json
import os
from urllib.parse import unquote_plus

import boto3

from shared import get_aws_region, post_internal_json


_s3_client = None
_sqs_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=get_aws_region())
    return _s3_client


def get_sqs_client():
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs", region_name=get_aws_region())
    return _sqs_client


def _normalise_bool(value: str | None) -> bool:
    return (value or "").lower() in {"1", "true", "yes", "on"}


def handler(event: dict, _context) -> dict:
    results = []
    queue_url = os.environ["OCR_QUEUE_URL"]

    for record in event.get("Records", []):
        if record.get("eventSource") != "aws:s3":
            continue

        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        head = get_s3_client().head_object(Bucket=bucket, Key=key)
        metadata = head.get("Metadata", {})

        document_id = int(metadata["document-id"])
        claim_id = int(metadata["claim-id"])
        run_ocr = _normalise_bool(metadata.get("run-ocr"))

        message_id = None
        if run_ocr:
            payload = {
                "event_type": "document_ready_for_ocr",
                "document_id": document_id,
                "claim_id": claim_id,
                "s3_bucket": bucket,
                "s3_key": key,
                "s3_uri": f"s3://{bucket}/{key}",
            }
            response = get_sqs_client().send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(payload),
            )
            message_id = response["MessageId"]

        callback_result = post_internal_json(
            "/internal/documents/s3-object-created",
            {
                "document_id": document_id,
                "claim_id": claim_id,
                "s3_bucket": bucket,
                "s3_key": key,
                "queued_for_ocr": run_ocr,
                "ocr_job_id": message_id,
            },
        )
        results.append(callback_result)

    return {
        "status": "ok",
        "processed_records": len(results),
        "results": results,
    }

from __future__ import annotations

import asyncio
from urllib.parse import unquote_plus

from app.document_pipeline_service import DocumentPipelineService


def handler(event: dict, _context) -> dict:
    service = DocumentPipelineService()
    results = []

    for record in event.get("Records", []):
        if record.get("eventSource") != "aws:s3":
            continue

        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        results.append(asyncio.run(service.handle_s3_object_created(bucket=bucket, key=key)))

    return {
        "status": "ok",
        "processed_records": len(results),
        "results": results,
    }

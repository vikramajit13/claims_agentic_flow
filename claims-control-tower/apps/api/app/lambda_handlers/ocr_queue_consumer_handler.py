from __future__ import annotations

import asyncio
import json

from app.document_pipeline_service import DocumentPipelineService


def handler(event: dict, _context) -> dict:
    service = DocumentPipelineService()
    results = []

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        results.append(asyncio.run(service.process_ocr_job(document_id=body["document_id"])))

    return {
        "status": "ok",
        "processed_records": len(results),
        "results": results,
    }

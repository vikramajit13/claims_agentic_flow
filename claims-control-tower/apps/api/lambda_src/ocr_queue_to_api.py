from __future__ import annotations

import json

from shared import post_internal_json


def handler(event: dict, _context) -> dict:
    results = []

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        callback_result = post_internal_json(
            "/internal/documents/process-ocr",
            {"document_id": body["document_id"]},
        )
        results.append(callback_result)

    return {
        "status": "ok",
        "processed_records": len(results),
        "results": results,
    }

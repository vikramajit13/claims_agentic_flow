from __future__ import annotations

from app.observability import traceable


class VectorService:
    @traceable(name="mock_document_embedding", run_type="embedding")
    def embed_text(self, text: str) -> list[float]:
        baseline = float((len(text) % 10) + 1) / 10.0
        return [baseline, baseline / 2, baseline / 3, baseline / 4, baseline / 5, baseline / 6, baseline / 7, baseline / 8]

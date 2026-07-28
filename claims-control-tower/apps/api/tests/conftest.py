import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["USE_MOCK_S3"] = "true"
os.environ["USE_MOCK_OCR"] = "true"
os.environ["USE_MOCK_SQS"] = "true"
os.environ["INTERNAL_SERVICE_TOKEN"] = "test-internal-token"

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

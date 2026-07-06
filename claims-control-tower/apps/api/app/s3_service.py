from __future__ import annotations

import uuid

import boto3

from app.config import settings


class S3Service:
    def __init__(self) -> None:
        self.client = None if settings.use_mock_s3 else boto3.client("s3", region_name=settings.aws_region)

    def build_object_location(self, claim_id: int, file_name: str) -> tuple[str, str, str]:
        safe_name = file_name.replace(" ", "_")
        key = f"claims/{claim_id}/{uuid.uuid4()}-{safe_name}"
        bucket = settings.s3_bucket_default
        return f"s3://{bucket}/{key}", bucket, key

    def create_presigned_upload(self, *, bucket: str, key: str, content_type: str | None) -> str:
        if settings.use_mock_s3:
            return f"https://mock-s3.local/{bucket}/{key}?method=PUT"
        params = {"Bucket": bucket, "Key": key}
        if content_type:
            params["ContentType"] = content_type
        if self.client is None:
            raise RuntimeError("S3 client is not configured for non-mock usage.")
        return self.client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=settings.s3_presign_expiry_seconds,
        )

    def object_exists(self, *, bucket: str, key: str) -> bool:
        if settings.use_mock_s3:
            return True
        if self.client is None:
            raise RuntimeError("S3 client is not configured for non-mock usage.")
        try:
            self.client.head_object(Bucket=bucket, Key=key)
        except self.client.exceptions.ClientError:
            return False
        return True

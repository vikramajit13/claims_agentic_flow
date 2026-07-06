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

    def create_presigned_upload(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str | None,
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, dict[str, str]]:
        upload_headers: dict[str, str] = {}
        if settings.use_mock_s3:
            if content_type:
                upload_headers["Content-Type"] = content_type
            for meta_key, meta_value in (metadata or {}).items():
                upload_headers[f"x-amz-meta-{meta_key}"] = meta_value
            return f"https://mock-s3.local/{bucket}/{key}?method=PUT", upload_headers
        params = {"Bucket": bucket, "Key": key}
        if content_type:
            params["ContentType"] = content_type
            upload_headers["Content-Type"] = content_type
        if metadata:
            params["Metadata"] = metadata
            for meta_key, meta_value in metadata.items():
                upload_headers[f"x-amz-meta-{meta_key}"] = meta_value
        if self.client is None:
            raise RuntimeError("S3 client is not configured for non-mock usage.")
        return (
            self.client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=settings.s3_presign_expiry_seconds,
            ),
            upload_headers,
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

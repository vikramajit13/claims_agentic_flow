from __future__ import annotations

import json
import os
import urllib.request

import boto3


_secrets_client = None
_cached_internal_token = None


def get_aws_region() -> str:
    return os.environ.get("AWS_REGION", "ap-southeast-2")


def get_secrets_client():
    global _secrets_client
    if _secrets_client is None:
        _secrets_client = boto3.client("secretsmanager", region_name=get_aws_region())
    return _secrets_client


def get_internal_service_token() -> str:
    global _cached_internal_token
    if _cached_internal_token is not None:
        return _cached_internal_token

    secret_arn = os.environ["INTERNAL_SERVICE_TOKEN_SECRET_ARN"]
    response = get_secrets_client().get_secret_value(SecretId=secret_arn)
    _cached_internal_token = response["SecretString"]
    return _cached_internal_token


def post_internal_json(path: str, payload: dict) -> dict:
    base_url = os.environ["API_INTERNAL_BASE_URL"].rstrip("/")
    token = get_internal_service_token()
    request = urllib.request.Request(
        url=f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Internal-Token": token,
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

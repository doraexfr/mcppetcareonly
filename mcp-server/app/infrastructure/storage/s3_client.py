import asyncio
from dataclasses import dataclass

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import NotFoundError


@dataclass
class S3Object:
    body: bytes
    content_type: str | None
    etag: str | None


class S3StorageClient:
    def __init__(self, client: BaseClient | None = None) -> None:
        endpoint_url = f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}"
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        self.bucket = settings.MINIO_BUCKET_PRIVATE

    async def download_object(self, object_key: str) -> S3Object:
        return await asyncio.to_thread(self._download_object_sync, object_key)

    def _download_object_sync(self, object_key: str) -> S3Object:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise NotFoundError("Document object not found in storage") from exc
            raise

        body = response["Body"].read()
        return S3Object(
            body=body,
            content_type=response.get("ContentType"),
            etag=response.get("ETag"),
        )


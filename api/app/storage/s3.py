import hashlib
import hmac
from time import time
from urllib.parse import quote

from boto3.session import Session

from app.core.config import get_settings


class S3Storage:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.client = Session().client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def put(self, organization_id: str, object_key: str, file, content_type: str) -> str:
        key = f"{organization_id}/{object_key}"
        self.client.upload_fileobj(file, self.bucket, key, ExtraArgs={"ContentType": content_type})
        return object_key

    def delete(self, organization_id: str, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=f"{organization_id}/{object_key}")

    def signed_download_url(self, organization_id: str, object_key: str, ttl_seconds: int) -> str:
        expires = int(time()) + min(ttl_seconds, 900)
        payload = f"{organization_id}:{object_key}:{expires}".encode()
        signature = hmac.new(get_settings().app_secret_key.encode(), payload, hashlib.sha256).hexdigest()
        return f"/api/v1/private-files/{quote(organization_id)}/{quote(object_key)}?expires={expires}&signature={signature}"

    def local_path(self, organization_id: str, object_key: str):
        del organization_id, object_key
        return None

    def stream(self, organization_id: str, object_key: str):
        result = self.client.get_object(Bucket=self.bucket, Key=f"{organization_id}/{object_key}")
        body = result["Body"]
        return body.iter_chunks(chunk_size=1024 * 1024), result.get("ContentType", "application/octet-stream")

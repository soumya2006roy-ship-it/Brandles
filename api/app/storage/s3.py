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
        return key

    def signed_download_url(self, organization_id: str, object_key: str, ttl_seconds: int) -> str:
        return self.client.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": f"{organization_id}/{object_key}"}, ExpiresIn=min(ttl_seconds, 900))

    def local_path(self, organization_id: str, object_key: str):
        del organization_id, object_key
        return None

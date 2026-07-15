import io
import uuid
from pathlib import Path

from app.config import settings

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class StorageService:
    def __init__(self) -> None:
        self.s3_client = None
        if all([
            settings.S3_ENDPOINT,
            settings.S3_ACCESS_KEY,
            settings.S3_SECRET_KEY,
            settings.S3_BUCKET_NAME,
        ]):
            import boto3
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
            )
            self.bucket = settings.S3_BUCKET_NAME

    def save(self, file_data: bytes, original_name: str) -> str:
        ext = Path(original_name).suffix
        key = f"{uuid.uuid4()}{ext}"

        if self.s3_client:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
                ContentType=self._guess_mime(ext),
            )
            return f"{self.s3_client.meta.endpoint_url}/{self.bucket}/{key}"

        filepath = UPLOAD_DIR / key
        filepath.write_bytes(file_data)
        return str(filepath)

    def delete(self, file_url: str) -> None:
        if self.s3_client and file_url.startswith("http"):
            key = file_url.rsplit("/", 1)[-1]
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
        else:
            path = Path(file_url)
            if path.exists():
                path.unlink()

    def get_stream(self, file_url: str) -> tuple[io.BytesIO, str]:
        if self.s3_client and file_url.startswith("http"):
            key = file_url.rsplit("/", 1)[-1]
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            content_type = response["ContentType"]
            return io.BytesIO(response["Body"].read()), content_type

        path = Path(file_url)
        content_type = self._guess_mime(path.suffix)
        return io.BytesIO(path.read_bytes()), content_type

    def _guess_mime(self, ext: str) -> str:
        mapping = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        return mapping.get(ext.lower(), "application/octet-stream")


storage_service = StorageService()

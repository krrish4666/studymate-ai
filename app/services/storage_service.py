import io
import uuid
from pathlib import Path

from app.config import settings

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class StorageService:
    def save(self, file_data: bytes, original_name: str) -> str:
        ext = Path(original_name).suffix
        key = f"{uuid.uuid4()}{ext}"

        filepath = UPLOAD_DIR / key
        filepath.write_bytes(file_data)
        return str(filepath)

    def delete(self, file_url: str) -> None:
        path = Path(file_url)
        if path.exists():
            path.unlink()

    def get_stream(self, file_url: str) -> tuple[io.BytesIO, str]:
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
